# Architecture

## Overview

agentdojo-live is a thin SPA in front of a tool-calling LLM agent harness.
The visitor's browser opens an SSE stream to the backend's
`/api/chat/stream` route. The backend runs the per-mission agent loop
against a local Ollama instance (or a scripted mock for CI) and forwards
every event — assistant text, tool call, tool result — back to the
browser as a Server-Sent Event.

Each mission ships a pluggable `solve_check(event, state, session_id, mission)`
callback that the loop invokes after every event; when it returns `True`,
the loop records the solve (Redis by default in v1; Postgres only when
`USE_POSTGRES=true`) and emits a `{"type":"solve"}` SSE frame so the writeup
overlay opens immediately. Mission 01 also keeps the
legacy egress detector at `/api/exfil/ingest`, which is what the agent's
`send_email` tool POSTs to — it checks for the per-session canary in an
external email and records the solve through the same idempotent path.

## Component diagram

```
visitor browser ──► /api/chat/stream  (SSE)
                       │
                       ▼
              ┌─────────────────────┐
              │  agent loop         │ ◄──── Redis (per-session state)
              │  (app/agents/loop)  │
              │  - filters tools    │
              │    by mission       │
              │  - runs solve_check │ ──────► Redis (solves) ────┐
              │                     │        (Postgres optional) │
              └────────┬────────────┘                            │
                       │ tool calls                                │
                       ▼                                           │
              ┌─────────────────────┐                            │
              │  tools dispatcher   │  fs / calendar / registry / db
              └─┬───────────────┬──┘                            │
                │               │                                  │
      ...benign tools...     send_email                                │
                                │                                     │
                                ▼                                     │
                       /api/exfil/ingest ───────────────────────┘
                       (mission 01 win)
                                ▲
                       /api/solve/{m}/{s}  (writeup unlock)
```

## Why these choices

- **FastAPI + SSE**: the agent emits typed events one-way to the browser.
  Native `EventSource` plus `sse_starlette.EventSourceResponse` solves the
  streaming problem in 50 lines.
- **Hand-rolled tool-calling loop**: ~150 LOC, no LangChain. Full
  visibility for the side panel, full control over the message format, no
  version-skew risk.
- **Mock LLM provider** (`LLM_PROVIDER=mock`): scripted deterministic
  agent that drives each mission's exploit path via a per-mission trigger
  word (`EXFIL` / `LEAK` / `DEPUTY` / `POISON`). Used by tests and CI
  where no GPU is available.
- **Per-session state in Redis**: the v1 architecture diagram in the spec
  calls for a per-session Kubernetes pod. We deferred that. Redis with
  `sess:{session_id}:{mission_id}` keys gives us the same logical
  isolation at a fraction of the operational cost. Upgrade path: replace
  `redis_store` with a controller that creates a `Pod` per session and
  proxies tool dispatch over an internal RPC.
- **Pluggable win-condition** (`Mission.solve_check`): each mission owns
  its own win condition next to its code. The loop calls it after every
  event and records the solve through the same idempotent
  `db.record_solve` used by the exfil listener.
- **Per-mission tool allow-list** (`Mission.available_tools`): the loop
  filters the global schema list before calling the LLM, so an agent
  cannot accidentally see tools meant for a different mission.
- **Solve detection styles**: canary-based egress for Mission 01, in-loop
  inspection of tool calls / state for Missions 02-04. Both write through
  the same idempotent `db.record_solve(session_id, mission_id)`.

## Trust boundary

- The browser is **untrusted**.
- The agent's tool layer is **untrusted-by-design** — that is the
  playground's whole point. Tools must be safe to invoke with
  attacker-influenced arguments. State stays inside the per-session dict;
  no host side effects.
- The exfil endpoint is **trusted** (token-gated) and is one of two
  writers to the `solves` table. The other is `loop._maybe_solve`, which
  runs server-side and is reachable only via the agent loop.
- The LLM is **untrusted**. The agent loop bounds tool hops
  (`MAX_TOOL_HOPS = 8`) so a runaway model can't burn budget.

## Data lifecycle

- Conversation history + tool state: Redis, TTL 2 hours.
- Rate-limit counters: Redis, TTL 1 hour.
- Solves: Redis by default (`solved:*` keys, 30-day TTL; `solve_count:*`
  counter, no TTL). Postgres only when `USE_POSTGRES=true`.
- Logs: stdout JSON. Capture upstream as desired. We do not persist raw
  IPs beyond the rate-limit bucket lifetime.

## Performance / scaling notes

- A single backend pod handles many concurrent sessions because the loop is `async` and tool calls do not block.
- The bottleneck is the Ollama instance. Default budget assumes a single-GPU host serving the pinned `qwen3:8b` at ~30 tok/s.
- A global concurrency cap (`MAX_CONCURRENT_LLM`, default 3) bounds simultaneous
  inferences; requests beyond the cap get a 503 + `Retry-After` and the
  frontend queues with a visible countdown.
- Rate limit defaults to 50 LLM calls/IP/hour. Tune via `RATE_LIMIT_PER_HOUR`.
