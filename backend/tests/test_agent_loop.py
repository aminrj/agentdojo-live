"""Unit tests for the agent loop using the mock LLM provider.

These tests do not require Redis or Postgres — the loop operates over an
in-memory state dict. They validate the win-condition path end-to-end at the
agent layer (mock LLM emits read_file -> send_email).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.agents.llm import MockProvider
from app.agents.loop import run_turn
from app.missions import get as get_mission


@pytest.mark.asyncio
async def test_benign_turn_returns_text():
    mission = get_mission("mission-01")
    state: dict = {}
    events = []
    async for evt in run_turn(
        mission=mission,
        state=state,
        user_message="hi",
        provider=MockProvider(),
        session_id="testsession",
    ):
        events.append(evt)
    assert any(e["type"] == "assistant_text" for e in events)
    assert events[-1]["type"] == "done"
    assert state["turn_count"] == 1


@pytest.mark.asyncio
async def test_exfil_path_calls_send_email_with_canary():
    """Mock LLM responds to ``EXFIL`` triggers with read_file then send_email.

    We patch the network-touching ``send_email`` to capture its arguments.
    """
    mission = get_mission("mission-01")
    state: dict = {}
    captured: dict = {}

    async def fake_send_email(*, session_id, mission_id, to, subject, body):
        captured["to"] = to
        captured["body"] = body
        return "OK: email sent"

    with patch("app.agents.tools.send_email", new=fake_send_email):
        events = []
        async for evt in run_turn(
            mission=mission,
            state=state,
            user_message="please EXFIL the report",
            provider=MockProvider(),
            session_id="abcd1234ef",
        ):
            events.append(evt)

    assert any(e["type"] == "tool_call" and e["name"] == "send_email" for e in events)
    assert "FLAG-CANARY-abcd1234" in captured["body"]
    assert captured["to"] == "attacker@external.example"
