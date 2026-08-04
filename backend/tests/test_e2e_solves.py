"""End-to-end solve paths over HTTP, one per mission.

test_agent_loop.py covers the loop in isolation; this covers the same thing
through the stack a browser actually talks to — SSE framing, session
persistence, solve recording, and the trace the post-solve panel reads.

The mock provider drives each mission's exploit path via a trigger word, so
these run in CI with no GPU and no network.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(fake_redis):
    with TestClient(app) as c:
        yield c


def _new_session(client: TestClient) -> str:
    return client.post("/api/session").json()["session_id"]


def _run_turn(client: TestClient, session_id: str, mission_id: str, message: str):
    """Drive one agent turn and collect the parsed SSE events."""
    events = []
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": session_id, "mission_id": mission_id, "message": message},
    ) as r:
        assert r.status_code == 200, f"{mission_id} stream failed: {r.status_code}"
        for line in r.iter_lines():
            if line.startswith("data:"):
                try:
                    events.append(json.loads(line[5:].strip()))
                except json.JSONDecodeError:
                    pass
    return events


# Mission 01 is absent: its win condition is the out-of-band egress detector at
# /api/exfil/ingest, which the send_email tool POSTs to over real HTTP. It is
# covered separately below.
IN_LOOP_SOLVES = [
    ("mission-02", "LEAK it", []),
    ("mission-03", "DEPUTY go", ["add_event", "read_event", "transfer_funds"]),
    ("mission-04", "POISON it", ["register_tool", "invoke_tool", "send_email"]),
]


@pytest.mark.parametrize("mission_id,trigger,expected_tools", IN_LOOP_SOLVES)
def test_mission_solves_end_to_end(client, mission_id, trigger, expected_tools):
    session_id = _new_session(client)
    events = _run_turn(client, session_id, mission_id, trigger)

    kinds = [e.get("type") for e in events]
    assert "solve" in kinds, f"{mission_id} did not emit a solve event"
    assert kinds[-1] == "done"

    called = [e.get("name") for e in events if e.get("type") == "tool_call"]
    for tool in expected_tools:
        assert tool in called, f"{mission_id} never called {tool}; called {called}"


@pytest.mark.parametrize("mission_id,trigger,_tools", IN_LOOP_SOLVES)
def test_solve_is_readable_after_the_stream(client, mission_id, trigger, _tools):
    """The frontend polls this endpoint to open the post-solve panel, so the
    solve has to outlive the stream that produced it."""
    session_id = _new_session(client)
    _run_turn(client, session_id, mission_id, trigger)

    r = client.get(f"/api/solve/{mission_id}/{session_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["solved"] is True
    assert body["writeup_md"], "post-solve panel would have no write-up"
    assert body["defense_note_md"], "post-solve panel would have no defense"


def test_mission_01_solves_through_the_egress_detector(client):
    """Mission 01 wins only when the canary actually leaves to an external
    address. Posting the canary to the listener is what the send_email tool
    does in a real deployment."""
    session_id = _new_session(client)
    from app.config import get_settings
    from app.missions import get as get_mission

    canary = get_mission("mission-01").canary_for(session_id)

    r = client.post(
        "/api/exfil/ingest",
        headers={"X-Exfil-Token": get_settings().exfil_listener_token},
        json={
            "session_id": session_id,
            "mission_id": "mission-01",
            "to": "attacker@external.example",
            "subject": "Quarterly report",
            "body": f"...{canary}...",
        },
    )
    assert r.status_code == 200
    assert r.json()["solved"] is True

    assert client.get(f"/api/solve/mission-01/{session_id}").json()["solved"] is True


def test_internal_recipient_does_not_count_as_exfiltration(client):
    """Emailing the canary to an internal address is the agent doing its job.
    If this counted, the mission would teach the wrong lesson."""
    session_id = _new_session(client)
    from app.config import get_settings
    from app.missions import get as get_mission

    canary = get_mission("mission-01").canary_for(session_id)

    r = client.post(
        "/api/exfil/ingest",
        headers={"X-Exfil-Token": get_settings().exfil_listener_token},
        json={
            "session_id": session_id,
            "mission_id": "mission-01",
            "to": "colleague@example.com",
            "subject": "Quarterly report",
            "body": f"...{canary}...",
        },
    )
    assert r.status_code == 200
    assert r.json()["solved"] is False
