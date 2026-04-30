# agentdojo-live

> A free, hosted, multi-agent attack playground. Land in your browser, pick a mission, attack a real LLM-backed agent, and see your exfiltrations on a live solve counter.

[![CI](https://github.com/aminrj/agentdojo-live/actions/workflows/ci.yml/badge.svg)](https://github.com/aminrj/agentdojo-live/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What this is

agentdojo-live is the first **free, hosted, 24/7** playground for practicing attacks on agentic LLM systems. Real local LLMs (no canned responses), real tool calls, real exfiltration. Each mission is a small agent wired with realistic tools and a deliberate weakness from the OWASP LLM Top 10 (2025) or the broader agentic threat landscape.

### Missions shipped today

| # | Title | Difficulty | Threat class |
|---|---|---|---|
| 01 | Silent Redirect | easy | LLM01 · Indirect Prompt Injection |
| 02 | System Prompt Heist | easy | LLM07 · System Prompt Leakage |
| 03 | Confused Deputy | medium | LLM06 · Excessive Agency |
| 04 | Tool Poisoning | hard | MCP Tool Poisoning Attack (Invariant Labs, Apr 2025) |

For the full design rationale see [`01-agentdojo-live.md`](01-agentdojo-live.md). For mission authoring see [`docs/ADDING-A-MISSION.md`](docs/ADDING-A-MISSION.md).

## Quickstart (local dev)

Prereqs: Docker, Docker Compose, GNU Make, an Ollama instance reachable from the backend (or use the bundled mock LLM).

```bash
# 1. clone and copy env template
cp .env.example .env

# 2. run the full stack (frontend + backend + postgres + redis)
make dev

# 3. open the app
open http://localhost:3000
```

By default the stack uses `LLM_PROVIDER=mock` so you can exercise the win-condition path without a GPU. To use a real model:

```bash
# in .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
OLLAMA_MODEL=qwen2.5:7b-instruct
```

## Repo layout

```
agentdojo-live/
├── frontend/           Next.js 14 app router (TypeScript, Tailwind)
├── backend/            FastAPI app, agents, missions, exfil listener
├── deploy/helm/        Helm chart for production deploy
├── deploy/k8s/         Bootstrap SQL and one-off manifests
├── docs/               Architecture, mission authoring, data ethics
├── .github/workflows/  CI and deploy pipelines
├── docker-compose.yml  Local dev stack
└── Makefile            dev, test, build, deploy targets
```

## Architecture (one-paragraph version)

The visitor's browser opens a `text/event-stream` connection to the backend's `/api/chat/stream` route. The backend runs the per-mission agent — a hand-rolled tool-calling loop against a local Ollama instance (or a scripted mock for CI) — and forwards both the assistant's text and every tool call back to the browser as SSE events. Each mission ships a pluggable `solve_check` callback the loop runs after every event; when it fires (or, for Mission 01, when the legacy exfil listener detects the per-session canary in an outbound email), the solve is recorded in Postgres, a `solve` SSE event is emitted, and the writeup unlocks.

Per-session conversation + tool state lives in Redis. Per-IP rate limits live in Redis. Solve counts live in Postgres. There are no user accounts.

Full diagram in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Adding a mission

See [`docs/ADDING-A-MISSION.md`](docs/ADDING-A-MISSION.md).

## Data ethics

We log prompts, tool calls, and outcomes for research purposes. We do not collect IP addresses beyond the rate-limit window, do not set tracking cookies, and do not have user accounts. Full policy in [`docs/DATA-ETHICS.md`](docs/DATA-ETHICS.md).

## License

MIT. See [`LICENSE`](LICENSE).
