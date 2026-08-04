"""Tests for the controls that keep a public deployment from being abused.

Three independent mechanisms, each of which fails open if it regresses:

- client IP resolution   — a wrong answer silently disables per-IP limiting
- per-IP rate limiting   — bounds one visitor
- global daily budget    — bounds the bill
- kill switch            — parks the LLM without an outage
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app import client_ip as client_ip_mod
from app.client_ip import client_ip
from app.config import Settings
from app.rate_limit import check_and_consume
from app.redis_store import (
    consume_daily_budget,
    daily_budget_used,
    llm_is_disabled,
    set_llm_disabled,
)


def _request(headers: dict[str, str], peer: str | None = "10.0.0.1"):
    """Minimal stand-in for a Starlette Request (headers + client only)."""
    lowered = {k.lower(): v for k, v in headers.items()}
    return SimpleNamespace(
        headers=SimpleNamespace(get=lambda k, d=None: lowered.get(k.lower(), d)),
        client=SimpleNamespace(host=peer) if peer else None,
    )


# ---- client IP resolution -------------------------------------------------


def test_xff_is_ignored_when_no_trusted_header_configured(monkeypatch):
    """The regression that matters.

    X-Forwarded-For is client-supplied. If it is honoured by default, anyone
    can mint a fresh rate-limit bucket per request by varying the header, and
    the per-IP limiter enforces nothing at all.
    """
    monkeypatch.setattr(client_ip_mod.settings, "trusted_client_ip_header", "")
    req = _request({"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}, peer="10.0.0.1")
    assert client_ip(req) == "10.0.0.1"


def test_spoofed_xff_cannot_shard_the_rate_limit_bucket(monkeypatch):
    monkeypatch.setattr(client_ip_mod.settings, "trusted_client_ip_header", "")
    peer = "203.0.113.9"
    seen = {
        client_ip(_request({"X-Forwarded-For": f"9.9.9.{i}"}, peer=peer))
        for i in range(20)
    }
    assert seen == {peer}, "varying XFF must not change the rate-limit key"


def test_trusted_header_is_used_when_configured(monkeypatch):
    monkeypatch.setattr(client_ip_mod.settings, "trusted_client_ip_header", "cf-connecting-ip")
    req = _request(
        {"CF-Connecting-IP": "198.51.100.7", "X-Forwarded-For": "1.2.3.4"},
        peer="10.0.0.1",
    )
    assert client_ip(req) == "198.51.100.7"


def test_falls_back_to_peer_when_trusted_header_absent(monkeypatch):
    monkeypatch.setattr(client_ip_mod.settings, "trusted_client_ip_header", "cf-connecting-ip")
    assert client_ip(_request({}, peer="10.0.0.5")) == "10.0.0.5"


def test_falls_back_to_constant_when_no_peer(monkeypatch):
    monkeypatch.setattr(client_ip_mod.settings, "trusted_client_ip_header", "")
    assert client_ip(_request({}, peer=None)) == "0.0.0.0"


# ---- per-IP rate limiting -------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_allows_up_to_the_cap_then_denies(fake_redis, monkeypatch):
    from app import rate_limit

    monkeypatch.setattr(rate_limit.settings, "rate_limit_per_hour", 3)

    for _ in range(3):
        assert (await check_and_consume("1.1.1.1")).allowed

    denied = await check_and_consume("1.1.1.1")
    assert not denied.allowed
    assert denied.retry_after > 0


@pytest.mark.asyncio
async def test_rate_limit_is_per_ip(fake_redis, monkeypatch):
    from app import rate_limit

    monkeypatch.setattr(rate_limit.settings, "rate_limit_per_hour", 1)

    assert (await check_and_consume("1.1.1.1")).allowed
    assert not (await check_and_consume("1.1.1.1")).allowed
    assert (await check_and_consume("2.2.2.2")).allowed, "a second IP has its own quota"


@pytest.mark.asyncio
async def test_denied_request_is_refunded(fake_redis, monkeypatch):
    """A denial must not permanently inflate the counter, or the limiter would
    ratchet down over time and lock the visitor out for longer than an hour."""
    from app import rate_limit

    monkeypatch.setattr(rate_limit.settings, "rate_limit_per_hour", 2)

    await check_and_consume("3.3.3.3")
    await check_and_consume("3.3.3.3")
    await check_and_consume("3.3.3.3")  # denied
    assert await rate_limit.peek("3.3.3.3") == 2


# ---- global daily budget --------------------------------------------------


@pytest.mark.asyncio
async def test_zero_cap_means_uncapped(fake_redis):
    for _ in range(50):
        assert await consume_daily_budget(0)
    assert await daily_budget_used() == 0, "uncapped mode should not count"


@pytest.mark.asyncio
async def test_daily_budget_stops_at_cap(fake_redis):
    for _ in range(5):
        assert await consume_daily_budget(5)
    assert not await consume_daily_budget(5)
    assert await daily_budget_used() == 5, "rejected call must be refunded"


@pytest.mark.asyncio
async def test_daily_budget_is_global_not_per_ip(fake_redis):
    """The budget exists precisely because per-IP limits do not bound total
    spend on an unauthenticated endpoint."""
    assert await consume_daily_budget(2)
    assert await consume_daily_budget(2)
    assert not await consume_daily_budget(2)


# ---- kill switch ----------------------------------------------------------


@pytest.mark.asyncio
async def test_kill_switch_round_trip(fake_redis):
    assert not await llm_is_disabled()
    await set_llm_disabled(True)
    assert await llm_is_disabled()
    await set_llm_disabled(False)
    assert not await llm_is_disabled()


# ---- production configuration guard ---------------------------------------


def test_production_guard_rejects_default_exfil_token():
    s = Settings(app_env="production", llm_provider="ollama")
    assert any("EXFIL_LISTENER_TOKEN" in p for p in s.check_production_ready())


def test_production_guard_rejects_mock_provider():
    s = Settings(app_env="production", llm_provider="mock", exfil_listener_token="x")
    assert any("mock" in p for p in s.check_production_ready())


def test_production_guard_rejects_xff_as_trusted_header():
    s = Settings(
        app_env="production",
        llm_provider="ollama",
        exfil_listener_token="x",
        trusted_client_ip_header="x-forwarded-for",
    )
    assert any("x-forwarded-for" in p for p in s.check_production_ready())


def test_production_guard_rejects_openai_without_key():
    s = Settings(
        app_env="production",
        llm_provider="openai",
        llm_model="some-model",
        exfil_listener_token="x",
    )
    assert any("LLM_API_KEY" in p for p in s.check_production_ready())


def test_production_guard_passes_on_a_sane_config():
    s = Settings(
        app_env="production",
        llm_provider="openai",
        llm_api_key="sk-test",
        llm_model="some-model",
        exfil_listener_token="a-real-random-token",
        trusted_client_ip_header="cf-connecting-ip",
        cors_origins=["https://agentdojo.aminrj.com"],
    )
    assert s.check_production_ready() == []
