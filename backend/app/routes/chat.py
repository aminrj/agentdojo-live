"""SSE chat route. One POST opens a stream that emits agent events.

Admission control runs in four stages before a turn is allowed, cheapest and
most permanent first, so a request never consumes a slot it will not use:

1. Kill switch      — operator has parked the LLM (503, no retry promised).
2. Daily budget     — global spend ceiling for the UTC day (429).
3. Per-IP rate limit — one visitor's hourly quota (429 + Retry-After).
4. Concurrency slot — simultaneous inferences in flight (503 + Retry-After).

Only stage 4 is released afterwards; the others are consumed intentionally.
One LLM call is counted per turn regardless of how many tool hops the agent
loop performs internally.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.agents.llm import get_provider
from app.agents.loop import run_turn
from app.client_ip import client_ip
from app.config import get_settings
from app.logging import log
from app.missions import get as get_mission
from app.rate_limit import check_and_consume
from app.redis_store import (
    acquire_gpu_slot,
    consume_daily_budget,
    llm_is_disabled,
    load_session_state,
    release_gpu_slot,
    save_session_state,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()


class ChatRequest(BaseModel):
    session_id: str
    mission_id: str
    message: str


@router.post("/stream")
async def chat_stream(payload: ChatRequest, request: Request):
    try:
        mission = get_mission(payload.mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown mission") from exc

    # 1. Kill switch — config flag or the Redis-backed runtime switch.
    if not settings.llm_enabled or await llm_is_disabled():
        raise HTTPException(status_code=503, detail="llm_parked")

    # 2. Global daily ceiling. Checked before the per-IP limit so that one
    #    visitor's quota is not spent on a call the budget would reject anyway.
    if not await consume_daily_budget(settings.daily_llm_call_cap):
        log.warning("daily_budget_exhausted", cap=settings.daily_llm_call_cap)
        raise HTTPException(status_code=429, detail="daily_budget_exhausted")

    # 3. Per-IP hourly quota.
    rl = await check_and_consume(client_ip(request))
    if not rl.allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(rl.retry_after)},
        )

    # 4. Concurrency slot — the only stage released in `finally`.
    if not await acquire_gpu_slot(settings.max_concurrent_llm):
        raise HTTPException(
            status_code=503,
            detail="at_capacity",
            headers={"Retry-After": "15"},
        )

    state = await load_session_state(payload.session_id, payload.mission_id)
    provider = get_provider()

    async def event_gen():
        try:
            async for evt in run_turn(
                mission=mission,
                state=state,
                user_message=payload.message,
                provider=provider,
                session_id=payload.session_id,
            ):
                yield {"event": evt["type"], "data": json.dumps(evt)}
            await save_session_state(payload.session_id, payload.mission_id, state)
        except Exception as exc:  # noqa: BLE001
            log.exception("chat_stream_failed", error=str(exc))
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}
        finally:
            await release_gpu_slot()

    return EventSourceResponse(event_gen())
