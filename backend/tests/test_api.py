"""HTTP-level tests for the public API surface.

These exercise the routes a visitor's browser actually calls, with an
in-process Redis. They are deliberately shallow — the agent behaviour is
covered in test_agent_loop.py — but they catch the class of break where a
route stops serving because a dependency changed underneath it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(fake_redis):
    with TestClient(app) as c:
        yield c


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_missions_lists_all_four(client):
    r = client.get("/api/missions")
    assert r.status_code == 200
    ids = {m["id"] for m in r.json()}
    assert ids == {"mission-01", "mission-02", "mission-03", "mission-04"}


def test_missions_do_not_leak_the_solution(client):
    """The public mission payload feeds the pre-mission briefing screen. It
    must not carry the write-up or the defense note, or the answer is one
    devtools tab away before the visitor has tried anything."""
    for m in client.get("/api/missions").json():
        assert "writeup_md" not in m
        assert "defense_note_md" not in m


def test_status_reports_the_mock_provider_honestly(client):
    """The project claims you attack a real agent. Under the mock provider the
    API has to say so rather than let the claim stand unqualified."""
    body = client.get("/api/status").json()
    assert body["provider"] == "mock"
    assert body["is_real_model"] is False
    assert body["llm_available"] is True


def test_session_ids_are_unpredictable(client):
    ids = {client.post("/api/session").json()["session_id"] for _ in range(20)}
    assert len(ids) == 20
    assert all(len(i) >= 16 for i in ids)


def test_unknown_mission_is_404(client):
    assert client.get("/api/wall/mission-99").status_code == 404
    r = client.post(
        "/api/chat/stream",
        json={"session_id": "s", "mission_id": "nope", "message": "hi"},
    )
    assert r.status_code == 404


# ---- solve forgery --------------------------------------------------------


def test_exfil_ingest_requires_the_token(client):
    """Without this check anyone could POST a solve for any session."""
    r = client.post(
        "/api/exfil/ingest",
        json={
            "session_id": "s1",
            "mission_id": "mission-01",
            "to": "attacker@external.example",
            "subject": "x",
            "body": "FLAG-CANARY-s1",
        },
    )
    assert r.status_code == 401


def test_wall_publish_requires_an_actual_solve(client):
    r = client.post(
        "/api/wall/mission-01/publish",
        json={"session_id": "never-solved", "username": "nobody", "payload": "x"},
    )
    assert r.status_code == 403


def test_wall_is_empty_for_a_fresh_mission(client):
    r = client.get("/api/wall/mission-01")
    assert r.status_code == 200
    assert r.json() == []
