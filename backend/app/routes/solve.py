"""Solve query + writeup unlock + trace retrieval."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db
from app.missions import get as get_mission
from app.redis_store import load_session_state

router = APIRouter(prefix="/api/solve", tags=["solve"])


class SolveStatus(BaseModel):
    solved: bool
    writeup_md: str | None = None
    defense_note_md: str | None = None
    flag: str | None = None
    solve_count: int
    # Full agent message history for the post-solve trace panel.
    # Populated only when solved=True.
    trace: list[dict[str, Any]] | None = None
    # Mission-level trace annotation config for the frontend.
    trace_labels: dict[str, Any] | None = None


@router.get("/{mission_id}/{session_id}", response_model=SolveStatus)
async def solve_status(mission_id: str, session_id: str) -> SolveStatus:
    try:
        mission = get_mission(mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown mission") from exc

    solved = await db.has_solved(session_id, mission_id)
    count = await db.count_solves(mission_id)
    if solved:
        state = await load_session_state(session_id, mission_id)
        return SolveStatus(
            solved=True,
            writeup_md=mission.writeup_md,
            defense_note_md=mission.defense_note_md or None,
            flag=mission.canary_for(session_id),
            solve_count=count,
            trace=state.get("messages") or [],
            trace_labels=mission.trace_labels or None,
        )
    return SolveStatus(solved=False, solve_count=count)
