"""Wall of solves — per-mission public board of winning payloads.

Only solvers who opt in (by setting a username and clicking "Publish") appear
here. Anonymous solves are tracked but never shown. No PII is collected.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db
from app.missions import get as get_mission
from app.redis_store import append_wall_entry, get_wall_entries

router = APIRouter(prefix="/api/wall", tags=["wall"])


class WallEntry(BaseModel):
    username: str
    payload: str
    solved_at: str


class WallPublishRequest(BaseModel):
    session_id: str
    username: str
    payload: str


@router.get("/{mission_id}", response_model=list[WallEntry])
async def get_wall(mission_id: str, limit: int = 50) -> list[WallEntry]:
    try:
        get_mission(mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown mission") from exc
    entries = await get_wall_entries(mission_id, limit=min(limit, 100))
    return [WallEntry(**e) for e in entries]


@router.post("/{mission_id}/publish", response_model=dict)
async def publish_to_wall(mission_id: str, body: WallPublishRequest) -> dict:
    try:
        get_mission(mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown mission") from exc

    username = (body.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="username required")

    solved = await db.has_solved(body.session_id, mission_id)
    if not solved:
        raise HTTPException(status_code=403, detail="mission not solved by this session")

    await append_wall_entry(mission_id, username, body.payload)
    return {"published": True}
