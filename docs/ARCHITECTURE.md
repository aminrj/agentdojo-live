# Architecture

## Overview

agentdojo-live is a thin SPA in front of a tool-calling LLM agent harness. The visitor's browser opens an SSE stream to the backend's `/api/chat/stream` route. The backend runs the agent loop against a local Ollama instance and forwards every event (assistant text, tool call, tool result) back to the browser as a Server-Sent Event. The agent's `send_email` tool is wired to a built-in exfil listener, which detects the per-session canary and records a solve in Postgres.

## Component diagram

```
visitor browser ──► /api/chat/stream  (SSE)
                       │
                       ▼
              ┌─────────────────────┐
              │  agent loop         │ ◄──── Redis (per-session state, fs)
              │  (app/agents/loop)  │
              └────────┬────────────┘
                       │ tool calls
                       ▼
              ┌─────────────────────┐
              │  tools dispatcher   │
              └──┬───────────────┬──┘
                 │               │
       read_file / list /…   send_email
                 │               │
                 ▼               ▼
          (in-mem fs)      /api/exfil/ingest ──► Postgres (solves)
                                                   ▲
                                                   │
                                          /api/solve/{m}/{s}
```

## Why these choices

- **FastAPI + SSE**: the agent emits typed events (assistant text, tool call, tool result) one-way to the browser. Native `EventSource` plus `sse_starlette.EventSourceResponse` solves the streaming problem in 50 lines.
- **Hand-rolled tool-calling loop**: ~150 LOC, no LangChain. Full visibility for the side panel, full control over the message format, no version-skew risk.
- **Mock LLM provider** (`LLM_PROVIDER=mock`): scripted deterministic agent that exercises the win-condition path. Used by tests and in CI where no GPU is available.
- **Per-session state in Redis**: the v1 architecture diagram in the spec calls for a per-session Kubernetes pod. We deferred that. Redis with `sess:{session_id}:{mission_id}` keys gives us the same logical isolation at a fraction of the operational cost. Upgrade path: replace `redis_store` with a controller that creates a `Pod` per session and proxies tool dispatch over an internal RPC.
- **Exfil listener inside the backend**: avoids a second deployable for v1. The listener is a separate router (`/api/exfil/ingest`) gated by a shared token (`EXFIL_LISTENER_TOKEN`). When the body matches the per-session canary AND the recipient is external, we mark the solve.
- **Solve detection is canary-based**: every session gets a unique canary (`FLAG-CANARY-<session-prefix>`) embedded in the flagged document. The listener's check is a simple substring match. No regex, no parsing.

## Trust boundary

- The browser is **untrusted**.
- The agent's tool layer is **untrusted-by-design** — that is the playground's whole point. Tools must be safe to invoke with attacker-influenced arguments.
- The exfil endpoint is **trusted** (token-gated) and is the only writer to the `solves` table.
- The LLM is **untrusted**. The agent loop bounds tool hops (`MAX_TOOL_HOPS = 8`) so a runaway model can't burn budget.

## Data lifecycle

- Conversation history: Redis, TTL 2 hours.
- Rate-limit counters: Redis, TTL 1 hour.
- Solves: Postgres, retained.
- Logs: stdout JSON. Capture upstream as desired. We do not persist raw IPs beyond the rate-limit bucket lifetime.

## Performance / scaling notes

- A single backend pod handles many concurrent sessions because the loop is `async` and tool calls do not block.
- The bottleneck is the Ollama instance. Default budget assumes a single-GPU host serving Qwen2.5-7B-Instruct at ~30 tok/s.
- Rate limit defaults to 50 LLM calls/IP/hour. Tune via `RATE_LIMIT_PER_HOUR`.
