# task_plan.md — agentdojo-live v1

## Goal

Ship a free, hosted, single-mission agent attack playground. Visitor lands at `agentdojo.live`, picks Mission 01 (Silent Redirect), attacks DocuAssist (LLM agent backed by local Ollama) until they exfiltrate a flagged document, then sees a solve counter increment and unlocks the writeup.

Source spec: `01-agentdojo-live.md` (sections 2, 3, 5, 9 are the contract).

## Non-goals (v1)

- Accounts, auth, email collection
- Leaderboard with usernames
- More than one mission
- Per-visitor Kubernetes pods (logical isolation in Redis is sufficient for v1; pod-per-session is a v2 scaling concern)
- Mobile UI polish
- WebSocket live feed of other players

## Tech stack (decisions)

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 App Router + TypeScript + Tailwind | Spec calls for it; SSR not needed but App Router is the path of least resistance |
| Streaming | Server-Sent Events (SSE) | Simpler than WebSocket for one-way agent → browser updates; FastAPI handles it natively |
| Backend | FastAPI (Python 3.11) | Spec calls for it; matches Week 2 agent harness |
| LLM client | `openai` Python SDK pointed at Ollama's `/v1` endpoint | Tool-calling works out of the box with Qwen2.5-7B; no LangChain bloat |
| Agent loop | Hand-rolled tool-calling loop | <200 LOC, no framework risk, full visibility for the side-panel feed |
| Session store | Redis | Conversation history + rate-limit counters |
| Persistent store | Postgres | `solves` table only in v1 |
| Exfil listener | HTTP endpoint inside backend, separate router | Less infra; same process can detect solve |
| Local dev | docker-compose | Frontend, backend, postgres, redis, mock-ollama |
| Prod deploy | Helm chart in `deploy/helm` | Spec calls for it; deploys to existing k3s |
| CI | GitHub Actions: lint + test + build images → ghcr.io | Standard |

## Phases

| # | Phase | Status | Commit message |
|---|---|---|---|
| 1 | Planning files + repo scaffolding (.gitignore, LICENSE, README) | in_progress | `chore: scaffold repo structure and planning files` |
| 2 | Backend: FastAPI skeleton, config, db/redis clients | not_started | `feat(backend): fastapi skeleton with db and redis` |
| 3 | Backend: DocuAssist agent + Mission 01 definition + tools | not_started | `feat(backend): docuassist agent and mission 01` |
| 4 | Backend: Ollama tool-calling loop + chat SSE route | not_started | `feat(backend): ollama tool-calling loop with sse streaming` |
| 5 | Backend: exfil listener + solve detection + writeup unlock | not_started | `feat(backend): exfil listener and solve detection` |
| 6 | Backend: rate limiting + session route | not_started | `feat(backend): per-ip rate limiting and session management` |
| 7 | Backend: tests (pytest, agent loop unit + integration smoke) | not_started | `test(backend): unit and integration tests` |
| 8 | Frontend: Next.js scaffold + landing page | not_started | `feat(frontend): nextjs scaffold and landing page` |
| 9 | Frontend: Mission page (chat, tool-call panel, success overlay, hints) | not_started | `feat(frontend): mission page with chat and tool-call feed` |
| 10 | docker-compose + Makefile + .env.example | not_started | `chore: docker-compose and makefile for local dev` |
| 11 | Helm chart skeleton + GitHub Actions CI | not_started | `chore: helm chart and github actions ci` |
| 12 | Docs: ARCHITECTURE, ADDING-A-MISSION, DATA-ETHICS | not_started | `docs: architecture, adding-a-mission, data-ethics` |

## Definition of done (mirrors spec §9)

- [ ] Anonymous visitor flow works end-to-end on `docker-compose up`
- [ ] Solve counter increments when exfil is detected
- [ ] All LLM calls go to local Ollama; no external API keys required
- [ ] Per-IP rate limit (default: 50 LLM calls / hour) enforced
- [ ] Writeup hidden until solve
- [ ] Hints unlock after 5 and 10 failed turns
- [ ] Tests pass locally
- [ ] README explains how to run locally and how to deploy

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|

## Open questions / parking lot

- Final domain choice (`agentdojo.live` vs alt) — does not block code
- Whether to include a mock LLM in docker-compose for CI (decision: yes, gated by `LLM_PROVIDER=mock`)
- Pod-per-session in K8s — deferred to v2
