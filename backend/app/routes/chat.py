"""SSE chat route. One POST opens a stream that emits agent events.

Per-IP rate limit applies to each LLM call (counted as one regardless of how
many tool hops the loop performs).

A global concurrency cap (gpu:active counter in Redis) limits simultaneous LLM
inferences to settings.max_concurrent_llm. Beyond the cap, the server returns
503 with Retry-After so the client can queue gracefully instead of hanging.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.agents.llm import get_provider
from app.agents.loop import run_turn
from app.config import get_settings
from app.logging import log
from app.missions import get as get_mission
from app.rate_limit import check_and_consume
from app.redis_store import (
    acquire_gpu_slot,
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


def _client_ip(req: Request) -> str:
    fwd = req.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return req.client.host if req.client else "0.0.0.0"


@router.post("/stream")
async def chat_stream(payload: ChatRequest, request: Request):
    try:
        mission = get_mission(payload.mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown mission") from exc

    rl = await check_and_consume(_client_ip(request))
    if not rl.allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(rl.retry_after)},
        )

    if not await acquire_gpu_slot(settings.max_concurrent_llm):
        raise HTTPException(
            status_code=503,
            detail="homelab_at_capacity",
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
