"""Database (Postgres) bootstrap. Holds the `solves` table for v1."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings

settings = get_settings()


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
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _SessionLocal() as session:
        yield session


async def record_solve(session_id: str, mission_id: str, turns: int) -> None:
    async with _SessionLocal() as session:
        # Idempotent: only one solve per (session_id, mission_id).
        existing = await session.execute(
            select(Solve).where(
                Solve.session_id == session_id, Solve.mission_id == mission_id
            )
        )
        if existing.scalar_one_or_none() is not None:
            return
        session.add(Solve(session_id=session_id, mission_id=mission_id, turns=turns))
        await session.commit()


async def count_solves(mission_id: str) -> int:
    async with _SessionLocal() as session:
        result = await session.execute(
            select(func.count(Solve.id)).where(Solve.mission_id == mission_id)
        )
        return int(result.scalar_one() or 0)


async def has_solved(session_id: str, mission_id: str) -> bool:
    async with _SessionLocal() as session:
        result = await session.execute(
            select(Solve.id).where(
                Solve.session_id == session_id, Solve.mission_id == mission_id
            )
        )
        return result.scalar_one_or_none() is not None
