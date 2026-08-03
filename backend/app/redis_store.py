"""Redis client + per-session conversation/state helpers.

v1 data model (all in Redis, no Postgres in the critical path):
  sess:{session_id}:{mission_id}   — per-session state + message history (2h TTL)
  solved:{session_id}:{mission_id} — solve record (30d TTL, set on first solve)
  solve_count:{mission_id}         — global solve counter (no TTL)
  wall:{mission_id}                — Redis list of JSON wall entries (capped)
  rl:{ip}:{hour_bucket}            — per-IP rate-limit counter (1h TTL)
  gpu:active                       — global concurrency counter for LLM calls
  budget:{yyyy-mm-dd}              — global daily LLM call counter (26h TTL)
  llm:disabled                     — operator kill switch (presence = parked)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
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


# ---- session state --------------------------------------------------------

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


# ---- solve tracking -------------------------------------------------------
# Used when use_postgres=False (v1 default). Postgres path lives in db.py.

SOLVE_TTL = 60 * 60 * 24 * 30  # 30 days


def _solve_key(session_id: str, mission_id: str) -> str:
    return f"solved:{session_id}:{mission_id}"


def _solve_count_key(mission_id: str) -> str:
    return f"solve_count:{mission_id}"


async def record_solve_redis(session_id: str, mission_id: str, turns: int) -> None:
    r = get_redis()
    key = _solve_key(session_id, mission_id)
    was_new = await r.setnx(key, turns)
    if was_new:
        await r.expire(key, SOLVE_TTL)
        await r.incr(_solve_count_key(mission_id))


async def count_solves_redis(mission_id: str) -> int:
    raw = await get_redis().get(_solve_count_key(mission_id))
    return int(raw) if raw else 0


async def has_solved_redis(session_id: str, mission_id: str) -> bool:
    return bool(await get_redis().exists(_solve_key(session_id, mission_id)))


# ---- wall of solves -------------------------------------------------------

WALL_CAP = 100  # max entries per mission (most recent N)


def _wall_key(mission_id: str) -> str:
    return f"wall:{mission_id}"


async def append_wall_entry(mission_id: str, username: str, payload: str) -> None:
    r = get_redis()
    key = _wall_key(mission_id)
    entry = json.dumps(
        {
            "username": username[:32],
            "payload": payload[:1000],
            "solved_at": datetime.now(UTC).isoformat(),
        }
    )
    await r.rpush(key, entry)
    await r.ltrim(key, -WALL_CAP, -1)


async def get_wall_entries(mission_id: str, limit: int = 50) -> list[dict[str, Any]]:
    r = get_redis()
    raw_entries = await r.lrange(_wall_key(mission_id), -limit, -1)
    result = []
    for raw in reversed(raw_entries):
        try:
            result.append(json.loads(raw))
        except (json.JSONDecodeError, ValueError):
            pass
    return result


# ---- global LLM concurrency cap (GPU semaphore) --------------------------

_GPU_KEY = "gpu:active"
_GPU_TTL = 300  # 5 min fallback TTL in case a slot leaks (e.g., crash mid-request)


async def acquire_gpu_slot(max_concurrent: int) -> bool:
    r = get_redis()
    current = await r.incr(_GPU_KEY)
    await r.expire(_GPU_KEY, _GPU_TTL)
    if current > max_concurrent:
        await r.decr(_GPU_KEY)
        return False
    return True


async def release_gpu_slot() -> None:
    r = get_redis()
    val = await r.decr(_GPU_KEY)
    if val < 0:
        await r.set(_GPU_KEY, 0)


# ---- global daily budget (spend circuit-breaker) -------------------------
# Per-IP limits bound one visitor; they do not bound total cost, because the
# endpoint is unauthenticated and the number of source IPs is not ours to
# control. This is the ceiling that actually caps the bill.

_BUDGET_TTL = 60 * 60 * 26  # one day + slack, so the key self-cleans


def _budget_key() -> str:
    return f"budget:{datetime.now(UTC).date().isoformat()}"


async def consume_daily_budget(cap: int) -> bool:
    """Consume one unit of today's global call budget.

    Returns True if the call is within budget (or if ``cap`` is 0, meaning
    uncapped). Refunds and returns False when the cap is exceeded.
    """
    if cap <= 0:
        return True
    r = get_redis()
    key = _budget_key()
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, _BUDGET_TTL)
    used, _ = await pipe.execute()
    if int(used) > cap:
        await r.decr(key)
        return False
    return True


async def daily_budget_used() -> int:
    raw = await get_redis().get(_budget_key())
    return int(raw) if raw else 0


# ---- operational kill switch ---------------------------------------------
# Lets an operator park the LLM without a redeploy or an outage: missions, the
# wall, and the docs keep serving; only agent invocation is refused.

_KILL_KEY = "llm:disabled"


async def llm_is_disabled() -> bool:
    return bool(await get_redis().exists(_KILL_KEY))


async def set_llm_disabled(disabled: bool) -> None:
    r = get_redis()
    if disabled:
        await r.set(_KILL_KEY, "1")
    else:
        await r.delete(_KILL_KEY)
