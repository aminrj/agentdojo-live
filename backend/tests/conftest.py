"""Pytest configuration: use mock LLM and fakeredis-style mocking via env."""

import os

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_DB", "agentdojo_test")
