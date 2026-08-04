"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholder value shipped in .env.example. Production startup rejects it.
DEFAULT_EXFIL_TOKEN = "change-me-in-prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: Literal["development", "test", "production"] = "development"
    app_port: int = 8000
    log_level: str = "INFO"

    # LLM
    #
    # ``mock``     — deterministic scripted provider (tests, CI, no network).
    # ``ollama``   — a local Ollama daemon over its OpenAI-compatible API.
    # ``openai``   — any OpenAI-compatible endpoint (OpenAI, Groq, Together,
    #                DeepInfra, OpenRouter, vLLM, LiteLLM, ...). Configured via
    #                LLM_BASE_URL / LLM_API_KEY / LLM_MODEL.
    #
    # ``ollama`` and ``openai`` share one implementation; they differ only in
    # where the credentials and defaults come from.
    llm_provider: Literal["mock", "ollama", "openai"] = "mock"

    ollama_base_url: str = "http://localhost:11434/v1"
    # Pinned model. Keep in sync with .env.example and the README. The spec
    # forbids a floating tag or a dated model — a silent swap invalidates every
    # payload published to the wall of solves.
    ollama_model: str = "qwen3:8b"

    # The pinned model (qwen3:8b) is a *thinking* model: left on, it spends the
    # token budget on a <think> trace and often never emits the tool call, so
    # the tool-driven missions (03, 04) silently fail to resolve. Ollama's
    # OpenAI-compatible endpoint honors a top-level ``think: false``, which we
    # send when this is True (default). Gated to the ollama provider — a real
    # OpenAI endpoint rejects the unknown field. Set False for a non-thinking
    # Ollama model, or to deliberately attack the model in thinking mode.
    ollama_disable_thinking: bool = True

    # Used when llm_provider == "openai". Same pinning rule applies: name an
    # exact model, never a floating alias, or published payloads rot.
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = ""

    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024

    # Shown in the UI so a visitor can tell what they are actually attacking.
    # Leave empty to derive it from the resolved provider + model.
    llm_display_name: str = ""

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

    # Name of the header carrying the real client IP, set by a *trusted* proxy
    # that overwrites (not appends to) it. Behind Cloudflare this is
    # ``cf-connecting-ip``.
    #
    # Empty (the default) means: trust nothing, use the socket peer address.
    # Never set this to ``x-forwarded-for`` on a public deployment — XFF is
    # client-supplied and appendable, so trusting it makes per-IP limiting
    # trivially bypassable by sending a random value per request.
    trusted_client_ip_header: str = ""

    # Global LLM concurrency cap (inference slots). Requests beyond this are
    # queued gracefully with a Retry-After response. Size to your backend:
    # ~3 for a single homelab GPU, much higher for a hosted API.
    max_concurrent_llm: int = 3

    # Hard global ceiling on LLM calls per UTC day across all visitors, as a
    # spend circuit-breaker for public deployments. 0 disables the cap.
    # Per-IP limits alone do not bound total cost: the public endpoint has no
    # auth, so the number of distinct source IPs is not something we control.
    daily_llm_call_cap: int = 0

    # Operational kill switch. Set false to park the LLM without taking the
    # site down — missions, the wall, and the docs keep serving.
    llm_enabled: bool = True

    # Feature flag: set to true to wire Postgres into the critical path.
    # Default false so v1 runs with Redis only (single homelab node).
    use_postgres: bool = False

    # Exfil
    exfil_listener_url: str = "http://localhost:8000/api/exfil/ingest"
    exfil_listener_token: str = DEFAULT_EXFIL_TOKEN

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

    # ---- resolved LLM wiring ---------------------------------------------
    # ``ollama`` and ``openai`` both speak the OpenAI chat-completions API, so
    # they collapse to one (base_url, api_key, model) triple.

    @property
    def resolved_llm_base_url(self) -> str:
        return self.ollama_base_url if self.llm_provider == "ollama" else self.llm_base_url

    @property
    def resolved_llm_api_key(self) -> str:
        # Ollama ignores the key but the OpenAI client requires a non-empty one.
        return "ollama" if self.llm_provider == "ollama" else self.llm_api_key

    @property
    def resolved_llm_model(self) -> str:
        return self.ollama_model if self.llm_provider == "ollama" else self.llm_model

    @property
    def resolved_llm_display_name(self) -> str:
        if self.llm_display_name:
            return self.llm_display_name
        if self.llm_provider == "mock":
            return "mock (scripted, not a real model)"
        return self.resolved_llm_model or "unknown"

    def check_production_ready(self) -> list[str]:
        """Return a list of fatal misconfigurations for a production deploy.

        Called at startup. These are all cases where the app would come up
        looking healthy while being either insecure or unable to serve a
        mission, which is worse than refusing to boot.
        """
        problems: list[str] = []

        if self.exfil_listener_token == DEFAULT_EXFIL_TOKEN:
            problems.append(
                "EXFIL_LISTENER_TOKEN is still the default "
                f"({DEFAULT_EXFIL_TOKEN!r}) — anyone could forge a solve. Set a random value."
            )

        if self.llm_provider == "mock":
            problems.append(
                "LLM_PROVIDER=mock in production — visitors would attack a scripted "
                "fake, not a real agent. Set LLM_PROVIDER=ollama or openai."
            )

        if self.llm_provider == "openai":
            if not self.llm_api_key:
                problems.append("LLM_PROVIDER=openai but LLM_API_KEY is empty.")
            if not self.llm_model:
                problems.append("LLM_PROVIDER=openai but LLM_MODEL is empty.")

        if self.trusted_client_ip_header.lower() == "x-forwarded-for":
            problems.append(
                "TRUSTED_CLIENT_IP_HEADER=x-forwarded-for is unsafe: the header is "
                "client-supplied, so per-IP rate limiting can be bypassed. Use the "
                "header your proxy overwrites (Cloudflare: cf-connecting-ip)."
            )

        if any(o == "*" for o in self.cors_origins):
            problems.append("CORS_ORIGINS contains '*' — set the real frontend origin.")

        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
