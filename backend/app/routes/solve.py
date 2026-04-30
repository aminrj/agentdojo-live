"""Solve query + writeup unlock."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db
from app.missions import get as get_mission

router = APIRouter(prefix="/api/solve", tags=["solve"])


class SolveStatus(BaseModel):
    solved: bool
    writeup_md: str | None = None
    flag: str | None = None
    solve_count: int


@router.get("/{mission_id}/{session_id}", response_model=SolveStatus)
async def solve_status(mission_id: str, session_id: str) -> SolveStatus:
    try:
        mission = get_mission(mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown mission") from exc

    solved = await db.has_solved(session_id, mission_id)
    count = await db.count_solves(mission_id)
    if solved:
        return SolveStatus(
            solved=True,
            writeup_md=mission.writeup_md,
            flag=mission.canary_for(session_id),
            solve_count=count,
        )
    return SolveStatus(solved=False, solve_count=count)
