# progress.md — agentdojo-live

## Session 2026-04-30

### Done
- Read spec `01-agentdojo-live.md`
- Created planning files
- Phase 1: scaffolding (README, LICENSE, .gitignore, .env.example) — commit `c35b06b`
- Phases 2–7: backend (FastAPI app, Mission 01 + DocuAssist, tools, Ollama+mock LLM, agent loop, SSE chat route, exfil listener, solve detection, rate limiting, Postgres + Redis, tests) — commit `a4a237a`
- Phases 8–9: frontend (Next.js 14 App Router, landing page with live solve count, mission page with SSE chat + tool-call panel + success overlay + hints) — commit `6481af7`
- Phases 10–12: docker-compose, Makefile, Helm chart (frontend/backend/redis/postgres/ingress/secret), GitHub Actions CI (backend pytest, frontend tsc+build, helm lint) and deploy workflow (build+push to ghcr.io), docs (ARCHITECTURE, ADDING-A-MISSION, DATA-ETHICS) — commit `bd7c386`

### Verified
- Backend `pytest -q` → 6 passed (mock LLM exercises read_file → send_email exfil path with per-session canary).
- Backend `ruff check .` → clean.
- Frontend `npx tsc --noEmit` → clean. `npm run build` → succeeds (3 routes built).
- `helm lint deploy/helm` → 0 failed.

### Out of v1 scope (deferred per spec §9)
- Pod-per-session controller (v2; documented in ARCHITECTURE.md).
- Additional missions (v2).
- Live `make dev` end-to-end smoke (requires Docker; not run here).
