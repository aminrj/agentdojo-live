"""Per-IP token-bucket rate limiting backed by Redis.

Window: 1 hour. Counter increments on each LLM call. Returns the remaining
quota and whether the request is allowed. The HTTP layer raises 429 on deny.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.config import get_settings
from app.redis_store import get_redis

settings = get_settings()


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: int  # seconds


def _bucket_key(ip: str) -> str:
    bucket = int(time.time() // 3600)
    return f"rl:{ip}:{bucket}"


async def check_and_consume(ip: str, cost: int = 1) -> RateLimitResult:
    key = _bucket_key(ip)
    r = get_redis()
    pipe = r.pipeline()
    pipe.incrby(key, cost)
    pipe.expire(key, 3600)
    new_count, _ = await pipe.execute()

    limit = settings.rate_limit_per_hour
    remaining = max(0, limit - int(new_count))
    if int(new_count) > limit:
        # The request put us over budget; refund and deny.
        await r.decrby(key, cost)
        retry = 3600 - int(time.time() % 3600)
        return RateLimitResult(allowed=False, remaining=0, retry_after=retry)
    return RateLimitResult(allowed=True, remaining=remaining, retry_after=0)


async def peek(ip: str) -> int:
    """Return how many calls have been used in the current bucket."""
    raw = await get_redis().get(_bucket_key(ip))
    return int(raw) if raw else 0
