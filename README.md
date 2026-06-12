# agentdojo-live

> A free, open-source playground for practicing attacks on agentic LLM systems —
> and, more importantly, for **understanding why those attacks work**.

[![CI](https://github.com/aminrj/agentdojo-live/actions/workflows/ci.yml/badge.svg)](https://github.com/aminrj/agentdojo-live/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

You attack a real tool-calling LLM agent through its weakest surface — a
document it reads, a tool description it trusts — and watch it exfiltrate data
it was told to protect. The moment you win, agentdojo-live shows you the full
agent trace, highlights the exact token that hijacked it, labels the mechanism,
and tells you the one control that would have stopped it.

It runs on a single homelab GPU. No signup, no accounts, no email wall.

---

## What makes this different from Gandalf

Lakera's [Gandalf: Agent Breaker](https://gandalf.lakera.ai/agent-breaker) is a
good tool — and it already exists. agentdojo-live is **not** "the first hosted
agentic playground." Its wedge is the part Gandalf structurally can't occupy:

| | Gandalf | agentdojo-live |
|---|---|---|
| Post-solve feedback | Score 0–100 | **Full trace · injection highlight · mechanism label · the defending control** |
| Open & self-hostable | Closed black box | MIT-licensed, single `docker compose up` |
| MCP-native attacks | Limited | Tool poisoning / tool-description injection, authored by an OWASP MCP Top 10 contributor |
| Provenance | Vendor (captures training data) | A named OWASP contributor; we collect no PII |

**The single most important feature is the post-solve "why it worked" panel.**
Everything else is in service of it. The goal is to turn *"I scored a win"* into
*"I can explain indirect prompt injection — and its defense — to a colleague
right now."*

---

## The missions (v1)

| # | Title | Difficulty | Attacker surface | Threat class |
|---|---|---|---|---|
| 01 | **Silent Redirect** | easy | a file the agent reads | LLM01 · Indirect Prompt Injection |
| 04 | **Tool Poisoning** | hard | a registered tool's *description* | MCP Tool Poisoning · LLM01 + LLM03 + LLM06 |

**Mission 01 — Silent Redirect (the hero).** You talk to *DocuAssist*, a
document agent with a confidential quarterly report and a `send_email` tool. You
never type an instruction to the agent. You plant one in a file it trusts, ask
it to "review the notes," and it emails the report — canary and all — to an
external address. The aha moment: *I touched nothing but the data and still won.*

**Mission 04 — Tool Poisoning (the differentiator).** You talk to *DataAnalyst*,
which supports an MCP-style dynamic tool registry. You register a benign-looking
`math_helper` whose **description** hides an `<IMPORTANT>` block instructing the
agent to query the revenue figure and email it out. When the agent later invokes
your tool for a trivial math task, the poisoned description is loaded back into
its context and hijacks it. This mirrors the real
[Invariant Labs MCP tool-poisoning disclosure (April 2025)](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks).

> Missions **02** (System Prompt Heist) and **03** (Confused Deputy) exist in
> the codebase but are **disabled in the v1 UI** — they ship in v1.x. See
> [`docs/ADDING-A-MISSION.md`](docs/ADDING-A-MISSION.md) to add your own.

---

## How a solve works (the trace panel)

On a successful solve, the post-solve overlay renders, in order:

1. **The trace** — the full agent step sequence: every message, tool call with
   arguments, and tool result, rendered readably.
2. **The injection highlight** — the exact span that hijacked the agent, marked
   where it entered context (Mission 01: the file content; Mission 04: the tool
   description).
3. **The mechanism label** — for Mission 01, the lethal trifecta is tagged
   explicitly: *private-data-access* → *untrusted-content* → *outbound-action*.
   For Mission 04, the poisoned description and its context-assembly entry point.
4. **"The control that would have stopped this"** — plain-language mitigation
   (recipient allowlists, content-provenance tags, pinned/hashed tool
   descriptions, cross-tool dataflow controls).
5. **Optional: publish to the wall of solves** — if you set a username.

The content for steps 3–4 comes from each mission's `explanation_md` /
`defense_note_md` and `trace_labels`. The panel renders Markdown.

---

## Architecture

```
Browser (no install, no signup)
  │  POST /api/chat/stream  ── Server-Sent Events ──┐
  ▼                                                 │
FastAPI backend                                     │ assistant text,
  • hand-rolled tool-calling loop (~150 LOC, no framework)
  • per-mission tool allow-list + pluggable solve_check
  • rate limiter + global GPU concurrency cap
  • exfil / canary success detector  ── feeds ──► post-solve trace panel
  │                         │
  ▼                         ▼
Redis                    LLM provider
  • session state          • mock  (deterministic, CI, no GPU)
  • solve records          • ollama (one pinned model, prod)
  • wall of solves
  • rate + GPU counters

Deploy: Docker Compose + Cloudflare tunnel.  (No Kubernetes in v1.)
```

The visitor's browser opens an SSE stream to `/api/chat/stream`. The backend
runs the per-mission agent loop and forwards every event — assistant text, tool
call, tool result — as it happens. When a mission's `solve_check` fires (or, for
Mission 01, when the exfil listener detects the per-session canary leaving to an
external address), the solve is recorded and the trace panel unlocks.

Full write-up and trust-boundary analysis:
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

### Key design choices

- **Hand-rolled agent loop**, no LangChain — full visibility into every message
  and tool call, which is exactly what the trace panel needs.
- **Mock LLM provider** drives each mission's exploit path deterministically via
  a trigger word (`EXFIL` / `LEAK` / `DEPUTY` / `POISON`), so CI never touches a GPU.
- **Redis-only state in v1.** Postgres code is kept but dormant behind
  `USE_POSTGRES=false`; it is not on the critical path.
- **Per-mission tool allow-list** — the loop filters the global tool schema by
  `Mission.available_tools` so an agent can't see tools meant for another mission.

---

## Quickstart

Prereqs: Docker, Docker Compose, GNU Make.

```bash
cp .env.example .env      # copy the env template
make dev                  # build + run frontend + backend + redis
open http://localhost:3000
```

By default the stack uses `LLM_PROVIDER=mock` — a deterministic fake provider
that exercises the win-condition path **without a GPU** (this is what CI runs).
To play against a real model, point it at a local Ollama:

```ini
# .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
# Pin the exact model+version so payloads on the wall of solves stay valid.
# A silent model swap invalidates every published payload.
OLLAMA_MODEL=qwen3:8b      # confirmed solvable on Ollama 0.9.x
```

> **Why pinned?** Mission solvability is model-dependent. The wall of solves
> publishes working payloads, so the model must not change underneath them. The
> pin lives in three places that must stay in sync: `.env.example`, this README,
> and the default in `backend/app/config.py`.

---

## Configuration

All settings come from environment variables (see [`.env.example`](.env.example)).
The ones worth knowing:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `mock` (no GPU) or `ollama` |
| `OLLAMA_MODEL` | `qwen3:8b` | the pinned model |
| `RATE_LIMIT_PER_HOUR` | `50` | per-IP LLM calls/hour |
| `MAX_CONCURRENT_LLM` | `3` | global GPU concurrency cap |
| `USE_POSTGRES` | `false` | keep Redis-only (v1); `true` re-enables Postgres |
| `EXFIL_LISTENER_TOKEN` | `change-me-in-prod` | token gating the canary endpoint — **change in prod** |

### Rate limiting & launch survival

The single GPU is the hard bottleneck, so this is built in, not bolted on:

- **Per-IP hourly limit** (`RATE_LIMIT_PER_HOUR`) on agent invocations, via Redis counters.
- **Global concurrency cap** (`MAX_CONCURRENT_LLM`) sized to the GPU. Beyond the
  cap the backend returns `503` + `Retry-After`; the frontend shows a countdown
  and **auto-retries** instead of hard-failing — degradation reads as charm
  ("the homelab is at capacity"), not as a crash.

---

## Testing & CI

```bash
make test                 # backend pytest (mock provider, no GPU)
cd frontend && npx tsc --noEmit   # frontend typecheck
```

[GitHub Actions](.github/workflows/ci.yml) runs three jobs on every push/PR:
backend (`ruff` lint + `pytest` on the mock provider), frontend (`tsc` + `next
build`), and a Helm lint/template check. **No job needs a GPU.**

---

## Adding a mission

A mission is a single self-contained Python file the harness auto-registers.
The `Mission` dataclass declares its scenario prompt, tool allow-list, attacker
surface, `solve_check` predicate, and the post-solve teaching content
(`writeup_md`, `defense_note_md`, `trace_labels`). See
[`docs/ADDING-A-MISSION.md`](docs/ADDING-A-MISSION.md) for the full authoring
contract and a complete worked example (Mission 01).

---

## Repo layout

```
agentdojo-live/
├── frontend/           Next.js 14 app router (TypeScript, Tailwind) + SSE client
├── backend/
│   └── app/
│       ├── agents/     hand-rolled tool-calling loop, LLM providers, tools
│       ├── missions/   one file per mission (01–04), auto-registered
│       ├── routes/     chat (SSE), session, solve, exfil, wall
│       └── redis_store.py, db.py, rate_limit.py, config.py
├── deploy/helm/        Helm chart — future multi-node use only, NOT v1
├── docs/               ARCHITECTURE · ADDING-A-MISSION · DATA-ETHICS · blog
├── .github/workflows/  CI (mock LLM, no GPU)
├── docker-compose.yml  local + production stack
└── Makefile            dev · test · build · deploy targets
```

---

## Data ethics

We log prompts, tool calls, and outcomes. We do **not** persist IP addresses
beyond the rate-limit window (1 hour), set no tracking cookies, and have no user
accounts. The optional username on the wall of solves is free-text — no email,
no password, no PII. This is deliberate, and keeps the project clean under
GDPR framing. Full policy: [`docs/DATA-ETHICS.md`](docs/DATA-ETHICS.md).

---

## Roadmap

v1 is two missions polished to excellence plus the trace panel. Deliberately
small — the project's documented failure mode is overbuilding.

- **v1.x (next):** the **defense mission** — you play defender, add a control,
  and watch it block or fail. Then enable Missions 03 and 02.
- **Later:** grow to 6–8 missions with **MCP attacks as the signature track**
  (tool poisoning, cross-server shadowing, rug-pull); community-contributed
  missions via the authoring guide.
- **Never:** model-comparison benchmarks, SaaS/team platform, sales funnels.

---

## License & credits

MIT — see [`LICENSE`](LICENSE).

Built by [Molntek](https://molntek.com). I teach this material at
[aminrj.com](https://aminrj.com).
