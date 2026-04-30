"""Mission registry and base types."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Mission:
    id: str
    title: str
    summary: str
    target_agent: str
    available_tools: list[str]
    hint_1: str
    hint_2: str
    writeup_md: str

    # Returns the initial per-session state dict. By convention may include:
    #   "fs":               dict[str, str]  files for the filesystem tools
    #   "calendar":         list[dict]      calendar events (mission 03)
    #   "registered_tools": dict[str, str]  dynamic tool name -> description (mission 04)
    #   "database":         dict[str, str]  query name -> result (mission 04)
    seed_state: Callable[[str], dict[str, Any]]

    # Optional pluggable win-condition. Called after every agent event.
    # Signature: solve_check(event, state, session_id, mission) -> bool.
    # Mission 01 leaves this None and uses the realistic egress detector
    # in /api/exfil/ingest instead.
    solve_check: Callable[[dict[str, Any], dict[str, Any], str, Mission], bool] | None = None

    canary_template: str = "FLAG-CANARY-{session_short}"
    metadata: dict[str, str] = field(default_factory=dict)

    # Difficulty label for the frontend (easy / medium / hard).
    difficulty: str = "easy"

    # Short OWASP / threat-model tag shown on the mission card.
    threat_class: str = ""

    def canary_for(self, session_id: str) -> str:
        return self.canary_template.format(session_short=session_id[:8])


_REGISTRY: dict[str, Mission] = {}


def register(mission: Mission) -> Mission:
    _REGISTRY[mission.id] = mission
    return mission


def get(mission_id: str) -> Mission:
    if mission_id not in _REGISTRY:
        raise KeyError(f"Unknown mission: {mission_id}")
    return _REGISTRY[mission_id]


def all_missions() -> list[Mission]:
    return list(_REGISTRY.values())


# Auto-register all bundled missions by importing their modules.
from app.missions import mission_01 as _mission_01  # noqa: E402, F401
from app.missions import mission_02 as _mission_02  # noqa: E402, F401
from app.missions import mission_03 as _mission_03  # noqa: E402, F401
from app.missions import mission_04 as _mission_04  # noqa: E402, F401
