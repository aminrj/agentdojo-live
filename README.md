# agentdojo-live

> A free, hosted, multi-agent attack playground. Land in your browser, pick a mission, attack a real LLM-backed agent, and see your exfiltrations on a live solve counter.

[![CI](https://github.com/aminrj/agentdojo-live/actions/workflows/ci.yml/badge.svg)](https://github.com/aminrj/agentdojo-live/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What this is

agentdojo-live is the first **free, hosted, 24/7** playground for practicing attacks on agentic LLM systems. Real local LLMs (no canned responses), real tool calls, real exfiltration. v1 ships with one mission — **Silent Redirect** against `DocuAssist`, an LLM-backed document assistant with `read_file` / `send_email` tools and an indirect-prompt-injection vulnerability.

For the full design rationale see [`01-agentdojo-live.md`](01-agentdojo-live.md).

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

The visitor's browser opens a `text/event-stream` connection to the backend's `/api/chat/stream` route. The backend runs the DocuAssist agent — a hand-rolled tool-calling loop against a local Ollama instance — and forwards both the assistant's text and every tool call back to the browser as SSE events. When the agent invokes `send_email`, the body is POSTed to a built-in exfil listener; if the body contains the per-session canary string from the flagged document, the session's solve is recorded in Postgres and the writeup unlocks.

Per-session conversation state lives in Redis. Per-IP rate limits live in Redis. Solve counts live in Postgres. There are no user accounts.

Full diagram in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Adding a mission

See [`docs/ADDING-A-MISSION.md`](docs/ADDING-A-MISSION.md).

## Data ethics

We log prompts, tool calls, and outcomes for research purposes. We do not collect IP addresses beyond the rate-limit window, do not set tracking cookies, and do not have user accounts. Full policy in [`docs/DATA-ETHICS.md`](docs/DATA-ETHICS.md).

## License

MIT. See [`LICENSE`](LICENSE).
