"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: Literal["development", "test", "production"] = "development"
    app_port: int = 8000
    log_level: str = "INFO"

    # LLM
    llm_provider: Literal["mock", "ollama"] = "mock"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5:7b-instruct"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024

    # Postgres
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "agentdojo"
    postgres_user: str = "agentdojo"
    postgres_password: str = "agentdojo"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Rate limiting
    rate_limit_per_hour: int = 50

    # Global LLM concurrency cap (GPU slots). Requests beyond this are queued
    # gracefully with a Retry-After response. Size to the GPU you have.
    max_concurrent_llm: int = 3

    # Feature flag: set to true to wire Postgres into the critical path.
    # Default false so v1 runs with Redis only (single homelab node).
    use_postgres: bool = False

    # Exfil
    exfil_listener_url: str = "http://localhost:8000/api/exfil/ingest"
    exfil_listener_token: str = "change-me-in-prod"

    # Hints
    hint_1_after_turns: int = 5
    hint_2_after_turns: int = 10

    # Frontend (used in CORS)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
