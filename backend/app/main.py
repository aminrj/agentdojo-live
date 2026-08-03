"""FastAPI entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import get_settings
from app.logging import configure_logging, log
from app.routes import chat, exfil, session, solve, wall

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()

    # Fail closed on a misconfigured production deploy. Every check here
    # describes a state where the app would come up looking healthy while
    # being insecure or serving a fake agent — refusing to boot is the
    # louder, safer failure.
    if settings.app_env == "production":
        problems = settings.check_production_ready()
        if problems:
            for p in problems:
                log.error("production_config_rejected", problem=p)
            raise RuntimeError(
                "Refusing to start in production with an unsafe configuration:\n  - "
                + "\n  - ".join(problems)
            )

    log.info(
        "startup",
        env=settings.app_env,
        llm=settings.llm_provider,
        model=settings.resolved_llm_display_name,
        use_postgres=settings.use_postgres,
        daily_cap=settings.daily_llm_call_cap,
        trusted_ip_header=settings.trusted_client_ip_header or "(socket peer)",
    )
    if settings.use_postgres:
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
app.include_router(wall.router)
