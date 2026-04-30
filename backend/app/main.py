"""FastAPI entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import get_settings
from app.logging import configure_logging, log
from app.missions import mission_01  # noqa: F401  -- side-effect: registers mission
from app.routes import chat, exfil, session, solve

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    log.info("startup", env=settings.app_env, llm=settings.llm_provider)
    try:
        await db.init_db()
    except Exception as exc:  # noqa: BLE001
        log.warning("db_init_failed", error=str(exc))
    yield
    log.info("shutdown")


app = FastAPI(title="agentdojo-live", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(session.router)
app.include_router(chat.router)
app.include_router(solve.router)
app.include_router(exfil.router)
