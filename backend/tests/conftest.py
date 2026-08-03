"""Pytest configuration: mock LLM provider and an in-process Redis.

Env is set before any app module is imported, because ``Settings`` is cached
with ``lru_cache`` on first access.
"""

import os

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_DB", "agentdojo_test")

import fakeredis.aioredis  # noqa: E402
import pytest  # noqa: E402

from app import redis_store  # noqa: E402


@pytest.fixture
def fake_redis(monkeypatch):
    """Swap the module-global Redis client for an in-process fake.

    Returns the fake so a test can assert on stored state directly. Each test
    gets a clean instance, so counters never leak between tests.
    """
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_store, "_client", fake)
    return fake
