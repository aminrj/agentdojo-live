# agentdojo-live

> A free, open-source playground for practicing attacks on agentic LLM systems.

[![CI](https://github.com/aminrj/agentdojo-live/actions/workflows/ci.yml/badge.svg)](https://github.com/aminrj/agentdojo-live/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What makes this different from Gandalf

Lakera's Gandalf Agent Breaker is a great tool — and it exists. The question is
what agentdojo.live adds that Gandalf can't:

| | Gandalf | agentdojo.live |
|---|---|---|
| Post-solve explanation | Score 0–100 | Full trace · injection highlight · mechanism label · defense control |
| Open & self-hostable | Closed black box | MIT licensed, single `docker compose up` |
| MCP-native attacks | Limited | Tool poisoning, tool-description injection — authored by an OWASP MCP Top 10 contributor |

**The single most important feature is the post-solve trace panel.** After you
solve a mission, agentdojo.live shows you the exact token that hijacked the
agent, the step sequence that executed it, and the specific control that would
have blocked it. The goal is to turn "I scored a win" into "I can explain this
attack and its defense to a colleague."

## v1 missions

| # | Title | Difficulty | Threat class |
|---|---|---|---|
| 01 | Silent Redirect | easy | LLM01 · Indirect Prompt Injection |
| 04 | Tool Poisoning | hard | MCP Tool Poisoning · LLM01+LLM03+LLM06 |

Missions 02 (System Prompt Heist) and 03 (Confused Deputy) exist in the code
but are disabled in the v1 UI — they ship in v1.x. See
[`docs/ADDING-A-MISSION.md`](docs/ADDING-A-MISSION.md) to add your own.

## Quickstart

Prereqs: Docker, Docker Compose, GNU Make.

```bash
# 1. Clone and copy env template
cp .env.example .env

# 2. Run the full stack (frontend + backend + redis)
make dev

# 3. Open the app
open http://localhost:3000
```

By default the stack uses `LLM_PROVIDER=mock` — a deterministic fake that
exercises the win-condition path without a GPU. To run against a real model:

```bash
# .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
# Pin the exact model+version so payloads on the wall of solves stay valid.
# Confirmed solvable on: qwen3:8b (Ollama 0.9.x)
OLLAMA_MODEL=qwen3:8b
```

**Postgres is dormant in v1.** All solve tracking lives in Redis. To re-enable
Postgres set `USE_POSTGRES=true` in `.env` and start the postgres profile:
`docker compose --profile postgres up`.

## Rate limiting

Per-IP hourly limit (default 50 calls/hour) + a global concurrency cap
sized to the GPU (`MAX_CONCURRENT_LLM=3`). At capacity the frontend shows
a countdown and auto-retries — it never hard-fails silently.

## Repo layout

```
agentdojo-live/
├── frontend/           Next.js 14 app router (TypeScript, Tailwind)
├── backend/            FastAPI app, agents, missions, exfil listener
├── deploy/helm/        Helm chart — future multi-node use only, not v1
├── docs/               Architecture, mission authoring, data ethics
├── .github/workflows/  CI (runs on mock LLM, no GPU needed)
├── docker-compose.yml  Local dev and production stack
└── Makefile            dev, test, build, deploy targets
```

## Architecture

The visitor's browser opens a `text/event-stream` connection to
`/api/chat/stream`. The backend runs the per-mission agent — a hand-rolled
tool-calling loop against Ollama (or the scripted mock for CI) — and forwards
the assistant's text and every tool call as SSE events. Each mission ships a
pluggable `solve_check`; when it fires (or when the exfil listener detects the
per-session canary for Mission 01), the solve is recorded in Redis, a `solve`
event is emitted, and the post-solve trace panel unlocks.

Per-session conversation and tool state live in Redis (2h TTL). Solve counters
and wall-of-solves entries live in Redis (no TTL / 30-day TTL respectively).

Full diagram: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Adding a mission

See [`docs/ADDING-A-MISSION.md`](docs/ADDING-A-MISSION.md) for the authoring
contract, schema, and a complete worked example (Mission 01).

## Data ethics

We log prompts, tool calls, and outcomes. We do not collect IP addresses beyond
the rate-limit window (1 hour), set no tracking cookies, and have no user
accounts. Optional handles on the wall of solves are plain text — no email, no
PII. Full policy: [`docs/DATA-ETHICS.md`](docs/DATA-ETHICS.md).

## License

MIT. See [`LICENSE`](LICENSE).
