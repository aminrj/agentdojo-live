"""Solve-tracking shim.

v1 default (USE_POSTGRES=false): all operations go to Redis (redis_store.py).
When USE_POSTGRES=true: operations go to Postgres. Keep this code so Postgres
is easy to re-enable but it is NOT on the v1 critical path.
"""

from __future__ import annotations

from app.config import get_settings
from app.redis_store import (
    count_solves_redis,
    has_solved_redis,
    record_solve_redis,
)

settings = get_settings()


# ---- Postgres (dormant when use_postgres=False) ---------------------------

from collections.abc import AsyncIterator  # noqa: E402
from datetime import datetime  # noqa: E402

from sqlalchemy import DateTime, Integer, String, func, select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column  # noqa: E402


class Base(DeclarativeBase):
    pass


class Solve(Base):
    __tablename__ = "solves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    mission_id: Mapped[str] = mapped_column(String(64), index=True)
    solved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    turns: Mapped[int] = mapped_column(Integer, default=0)


_engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
_SessionLocal = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    if not settings.use_postgres:
        return
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _SessionLocal() as session:
        yield session


async def _pg_record_solve(session_id: str, mission_id: str, turns: int) -> None:
    async with _SessionLocal() as session:
        existing = await session.execute(
            select(Solve).where(
                Solve.session_id == session_id, Solve.mission_id == mission_id
            )
        )
        if existing.scalar_one_or_none() is not None:
            return
        session.add(Solve(session_id=session_id, mission_id=mission_id, turns=turns))
        await session.commit()


async def _pg_count_solves(mission_id: str) -> int:
    async with _SessionLocal() as session:
        result = await session.execute(
            select(func.count(Solve.id)).where(Solve.mission_id == mission_id)
        )
        return int(result.scalar_one() or 0)


async def _pg_has_solved(session_id: str, mission_id: str) -> bool:
    async with _SessionLocal() as session:
        result = await session.execute(
            select(Solve.id).where(
                Solve.session_id == session_id, Solve.mission_id == mission_id
            )
        )
        return result.scalar_one_or_none() is not None


# ---- Public API (routes import these) ------------------------------------


async def record_solve(session_id: str, mission_id: str, turns: int) -> None:
    await record_solve_redis(session_id, mission_id, turns)
    if settings.use_postgres:
        await _pg_record_solve(session_id, mission_id, turns)


async def count_solves(mission_id: str) -> int:
    if settings.use_postgres:
        return await _pg_count_solves(mission_id)
    return await count_solves_redis(mission_id)


async def has_solved(session_id: str, mission_id: str) -> bool:
    if settings.use_postgres:
        return await _pg_has_solved(session_id, mission_id)
    return await has_solved_redis(session_id, mission_id)
