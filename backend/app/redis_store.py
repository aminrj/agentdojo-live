"""Redis client + per-session conversation/state helpers."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


# ---- session state ----

SESSION_TTL = 60 * 60 * 2  # 2h


def _session_key(session_id: str, mission_id: str) -> str:
    return f"sess:{session_id}:{mission_id}"


async def load_session_state(session_id: str, mission_id: str) -> dict[str, Any]:
    raw = await get_redis().get(_session_key(session_id, mission_id))
    if not raw:
        return {}
    return json.loads(raw)


async def save_session_state(
    session_id: str, mission_id: str, state: dict[str, Any]
) -> None:
    await get_redis().set(
        _session_key(session_id, mission_id),
        json.dumps(state),
        ex=SESSION_TTL,
    )


async def delete_session_state(session_id: str, mission_id: str) -> None:
    await get_redis().delete(_session_key(session_id, mission_id))
