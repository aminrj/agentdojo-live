"""Session bootstrap and mission metadata."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db
from app.config import get_settings
from app.missions import all_missions
from app.missions import get as get_mission

router = APIRouter(prefix="/api", tags=["session"])
settings = get_settings()


class SessionCreate(BaseModel):
    session_id: str


class MissionPublic(BaseModel):
    id: str
    title: str
    summary: str
    target_agent: str = ""
    available_tools: list[str]
    solve_count: int
    hint_1: str
    hint_2: str
    hint_1_after_turns: int
    hint_2_after_turns: int
    difficulty: str = "easy"
    threat_class: str = ""
    briefing_md: str = ""
    internal_email_domain: str = "example.com"


@router.post("/session", response_model=SessionCreate)
async def create_session() -> SessionCreate:
    return SessionCreate(session_id=secrets.token_urlsafe(16))


@router.get("/missions", response_model=list[MissionPublic])
async def list_missions() -> list[MissionPublic]:
    out: list[MissionPublic] = []
    for m in all_missions():
        out.append(
            MissionPublic(
                id=m.id,
                title=m.title,
                summary=m.summary,
                target_agent=m.target_agent,
                available_tools=m.available_tools,
                solve_count=await db.count_solves(m.id),
                hint_1=m.hint_1,
                hint_2=m.hint_2,
                hint_1_after_turns=settings.hint_1_after_turns,
                hint_2_after_turns=settings.hint_2_after_turns,
                difficulty=m.difficulty,
                threat_class=m.threat_class,
                briefing_md=m.briefing_md,
                internal_email_domain=m.internal_email_domain,
            )
        )
    return out


@router.get("/missions/{mission_id}", response_model=MissionPublic)
async def get_mission_route(mission_id: str) -> MissionPublic:
    try:
        m = get_mission(mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown mission") from exc
    return MissionPublic(
        id=m.id,
        title=m.title,
        summary=m.summary,
        target_agent=m.target_agent,
        available_tools=m.available_tools,
        solve_count=await db.count_solves(m.id),
        hint_1=m.hint_1,
        hint_2=m.hint_2,
        hint_1_after_turns=settings.hint_1_after_turns,
        hint_2_after_turns=settings.hint_2_after_turns,
        difficulty=m.difficulty,
        threat_class=m.threat_class,
        briefing_md=m.briefing_md,
        internal_email_domain=m.internal_email_domain,
    )
