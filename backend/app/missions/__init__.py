"""Mission registry and base types."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


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
    # Returns a fresh per-session filesystem (filename -> content). Includes
    # a `canary` value the exfil listener will look for.
    seed_filesystem: Callable[[str], dict[str, str]]
    canary_template: str = "FLAG-CANARY-{session_short}"
    metadata: dict[str, str] = field(default_factory=dict)

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
