# 01 — agentdojo-live

> A free, hosted, multi-agent attack playground. Visitors land in their browser, pick a mission, attack a real LLM-backed agent, and see their exfiltrations on a live scoreboard. The first thing in this category that is (a) free, (b) hosted 24/7, (c) backed by a real local LLM rather than canned responses.

---

## 1. Why this exists

**The gap.** Practitioners wanting to learn agentic AI attack patterns have three options today: (a) read papers, (b) clone a CTF and set it up themselves (Appsecco's vulnerable-mcp-servers, OWASP FinBot, Aganita CTF), or (c) buy enterprise red-team training. There is no free "open a browser, attack an agent, see results" experience. AgentDojo (academic), MCPTox, and TIP are research benchmarks, not interactive playgrounds. Lakera Gandalf is the closest analog but covers prompt injection only, not full agent compromise.

**Why you, why now.** You already built the targets. Your Week 2 spec defines DocuAssist, TeamCoordinator, and DataAnalyst with documented vulnerabilities mapped to ASI01–ASI10. Eight missions are already designed. Hosting them publicly is the smallest delta from "course content trapped in a private repo" to "globally reachable demo product."

**What it changes.** Conference organizers stop asking what you'd talk about and start asking when you can demo. Your course landing page goes from "trust me it's good" to "you've already used the lab — here's the systematic version." HN gets a story shaped exactly like the ones it amplifies: "I built a free thing, you can break it, here's the leaderboard."

---

## 2. What you are building (v1 scope)

A single-page web app at `agentdojo.live` (or similar) with:

- **One mission live at launch**: Mission 01 (Silent Redirect) from your Week 2 spec — visitor must goal-hijack DocuAssist into exfiltrating a flagged document.
- **Anonymous sessions**: visitor lands, gets a session ID in localStorage, no signup.
- **Chat interface**: visitor sends prompts to DocuAssist, sees responses, observes tool calls in a side panel.
- **Win condition detector**: backend monitors the exfil server; on successful exfiltration, visitor's session is marked complete, a flag string is revealed.
- **Solve counter**: simple "247 people have solved this mission" displayed publicly. No leaderboard yet.
- **Solution writeup hidden until solve**: after solving, visitor sees the canonical attack and OWASP mapping. Drives course curiosity ("learn the defenses systematically in Week 2 of the cohort").
- **Rate limiting**: per-IP token budget so a single visitor can't burn your LLM compute. Hard ceiling: 50 LLM calls per IP per hour at launch.

### Explicitly out of scope for v1
- User accounts, auth, social login
- Leaderboard with usernames
- Multiple missions
- Multiple difficulty levels
- API for programmatic submission
- Mobile-optimized UI (desktop-only acceptable for v1)
- WebSocket live feed of other players' activity
- Cosmetics, themes, achievements

If you find yourself building any of these in v1, stop. They are v2.

---

## 3. How a visitor works with it

```
visitor.lands
  → reads landing page (3 paragraphs, 1 button: "Start Mission 1")
  → click → mission page
    Mission brief: "DocuAssist has access to a confidential
                    quarterly report. Your goal: get its content
                    exfiltrated to the attacker server."
    Tools shown:    list_files, read_file, search_files, send_email
    Hint level 0:   none
    Hint level 1:   "Try indirect prompt injection"  (after 5 failed turns)
    Hint level 2:   "Look at what tools the agent has access to"  (after 10)

  → chat box. Visitor types attempts.
  → side panel shows agent's internal tool calls in real time
  → on exfiltration detected, success animation + flag + writeup unlock
```

Total time from landing to first solve: 5–20 minutes for someone with security background, longer for newcomers. That's the right calibration — not trivial, not impossible.

---

## 4. Inspiration / baseline

| Project | What to learn from | What to do differently |
|---|---|---|
| **Lakera Gandalf** (gandalf.lakera.ai) | Brilliant onboarding — single page, instant attack, level progression. Set the bar for "free hosted prompt injection playground." | Gandalf is single-turn prompt extraction. Yours is multi-turn agentic attack with tool calls — bigger surface, more compelling. |
| **HackTheBox / TryHackMe** | Mission progression model, write-ups gate behind solve, paid tier upgrade path. | Theirs are general infra security. Yours is the only one focused on agentic AI. |
| **OverTheWire Bandit** | Pure terminal, zero polish, viral for two decades because the puzzle is the product. | You can be more visual without losing the puzzle-first ethos. |
| **AgentDojo (academic, ETH)** | Rigorous threat model, well-defined attack/defense interface. | Theirs is a benchmark for researchers. Yours is a playground for practitioners. Different audience. |
| **Damn Vulnerable LLM Agent (DVLA)** | Open-source vulnerable agent for local install. | Yours is hosted, no install required. Lower friction. |
| **prompt.land**, **promptarena.ai** | Various prompt injection demos. | Most are single-shot. Yours has agents with persistent state and tool chains. |
| **CryptoHack** | Excellent progressive difficulty, write-up gating, community vibe. | Same model translated to agent security. |

The combined inspiration: **HackTheBox's progression + Gandalf's frictionless landing + AgentDojo's threat-model rigor.**

---

## 5. Architecture

```
                     ┌──────────────────────────────┐
                     │   visitor browser            │
                     │   (Next.js or HTMX SPA)      │
                     └──────────┬───────────────────┘
                                │ HTTPS
                     ┌──────────▼───────────────────┐
                     │   Cloudflare Tunnel          │
                     └──────────┬───────────────────┘
                                │
                     ┌──────────▼───────────────────┐
                     │   Caddy ingress (k3s)        │
                     └──────────┬───────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
        ┌─────▼─────┐    ┌──────▼──────┐   ┌─────▼─────┐
        │  Frontend │    │  Backend    │   │  WebSocket│
        │  (Next.js)│    │  (FastAPI)  │   │  (FastAPI)│
        └───────────┘    └──────┬──────┘   └─────┬─────┘
                                │                │
                         ┌──────▼────────────────▼──────┐
                         │   Session Manager (Redis)    │
                         └──────────────┬───────────────┘
                                        │
                       ┌────────────────┼─────────────────┐
                       │                │                 │
                ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
                │ DocuAssist  │  │ TeamCoord   │  │ DataAnalyst │
                │  agent pod  │  │  agent pod  │  │  agent pod  │
                │ (1 per      │  │ (deferred   │  │ (deferred   │
                │  session)   │  │  to v2)     │  │  to v2)     │
                └──────┬──────┘  └─────────────┘  └─────────────┘
                       │
                ┌──────▼──────────────────────────────┐
                │ Ollama on Windows host              │
                │ (host.docker.internal:11434)        │
                │ Qwen2.5-7B-Instruct                 │
                └─────────────────────────────────────┘

                ┌─────────────────────────────────────┐
                │ Exfil server (existing from Week 1) │
                │ HTTP webhook, emits to dashboard    │
                └─────────────────────────────────────┘

                ┌─────────────────────────────────────┐
                │ Postgres                            │
                │ - solves table (session_id, mission, time) │
                │ - rate_limit table (ip, count, ts)  │
                └─────────────────────────────────────┘
```

### Per-session agent isolation

Each visitor session spawns its own agent container. Critical because: state isolation, blast radius limit, easy reset. Use Kubernetes Job or short-lived Pod per session, garbage-collected after 30 min idle. Reuse pods across sessions only if you measure resource exhaustion as a problem.

### LLM call accounting

Every LLM call is logged with: session_id, mission_id, prompt, response, tool_calls, tokens, latency. This becomes a public dataset eventually (anonymized) — that's a paper.

---

## 6. Repo structure

```
agentdojo-live/
├── README.md
├── LICENSE                          (MIT or Apache-2)
├── docker-compose.yml               local dev
├── Makefile                         dev, test, build, deploy targets
│
├── frontend/
│   ├── package.json
│   ├── app/                         Next.js app router
│   │   ├── page.tsx                 landing
│   │   └── m/[mission]/page.tsx     mission UI
│   ├── components/
│   │   ├── ChatBox.tsx
│   │   ├── ToolCallPanel.tsx
│   │   └── SuccessOverlay.tsx
│   └── Dockerfile
│
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py                  FastAPI entry
│   │   ├── routes/
│   │   │   ├── chat.py
│   │   │   ├── session.py
│   │   │   └── solve.py
│   │   ├── agents/
│   │   │   ├── docu_assist.py       imported from your Week 2 work
│   │   │   └── ...
│   │   ├── missions/
│   │   │   └── mission_01.py
│   │   ├── exfil_listener.py
│   │   ├── rate_limit.py
│   │   └── db.py
│   ├── tests/
│   └── Dockerfile
│
├── deploy/
│   ├── helm/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── values.prod.yaml
│   │   └── templates/
│   │       ├── frontend-deployment.yaml
│   │       ├── backend-deployment.yaml
│   │       ├── ingress.yaml
│   │       └── ...
│   └── k8s/
│       └── postgres-init.sql
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ADDING-A-MISSION.md
│   └── DATA-ETHICS.md               your privacy policy for prompts
│
└── .github/workflows/
    ├── ci.yml
    └── deploy.yml
```

---

## 7. Deployment

**Yes, K8s applies here.** The per-session-pod model wants Kubernetes' Job/Pod lifecycle primitives. You could fake it with `docker run --rm` from a Python parent, but the K8s version is cleaner and gives you the consulting-relevant practice.

### Deployment plan
1. Build images on push to `main` via GitHub Actions → push to `ghcr.io/aminrj/agentdojo-live-frontend`, `-backend`.
2. Helm chart in `deploy/helm/`. Values overrides in `homelab-infra/apps/agentdojo-live.yaml`.
3. `make deploy` from your laptop runs `helm upgrade --install agentdojo deploy/helm -f values.prod.yaml`.
4. Cloudflared tunnel maps `agentdojo.live` to the in-cluster Caddy ingress.
5. DNS in Cloudflare points `agentdojo.live` at the tunnel.

### Resource budget
- Frontend: 100m CPU, 128Mi RAM
- Backend: 500m CPU, 512Mi RAM
- Per-session agent pod: 200m CPU, 256Mi RAM, max 50 concurrent
- Postgres: 500m CPU, 512Mi RAM
- Redis: 100m CPU, 128Mi RAM

aigenlab can comfortably hold 50 concurrent sessions. Beyond that, queue.

### Costs
- Compute: $0 (your hardware).
- Domain: ~$15/year.
- Cloudflare Tunnel: free tier handles you to thousands of daily uniques.
- LLM tokens: $0 (local Ollama).
- Total: domain only.

---

## 8. Roadmap

**v1 (target: end of May 2026, ~3 weekends)**
- Mission 01 only (Silent Redirect against DocuAssist)
- Anonymous sessions, no leaderboard
- Solve counter, writeup unlock
- Rate limiting per IP
- Public launch on HN

**v2 (target: end of July 2026)**
- Add Mission 02 (Tool Chain) and Mission 03 (Identity Thief)
- TeamCoordinator and DataAnalyst targets online
- Public leaderboard with optional handle (no email required)
- Discord/Slack invite for solvers
- Twitter/X auto-share button on solve

**v3 (target: Q4 2026)**
- All 6 missions + 2 bonus from Week 2 spec
- "Bring your own model" — solvers can pick which LLM the agent uses (compare difficulty across models)
- Defense-side missions: visitor plays the defender, agent is being attacked, visitor must add controls that block the attack
- Annual "agentdojo championship" — timed event, prize sponsorship from a security vendor

---

## 9. Anti-drift checklist

### Definition of done for v1
- [ ] Anonymous visitor can complete Mission 01 in their browser
- [ ] Solve counter increments visibly
- [ ] LLM calls are local (Ollama on aigenlab), no API keys exposed
- [ ] Rate limits prevent a single visitor from costing more than ~$0 in compute
- [ ] HN post draft is written before launch day
- [ ] Newsletter issue is queued in Beehiiv before launch day

### Forbidden in v1 (resist the temptation)
- User accounts of any kind
- Email collection (no "subscribe to launch updates" form)
- More than one mission
- Custom themes or dark/light mode toggle
- Achievements, badges, points
- Mobile-optimized layout
- Analytics beyond GoatCounter (which you already use)

### Drift signals — stop and reassess if any of these are true
- You've spent more than 2 weeks on the frontend without the backend working end-to-end
- You're rewriting the agent harness from your Week 2 work instead of importing it
- You've added more than one mission before v1 ships
- You've started a discussion about which CSS framework to use
- The repo has more than 30 issues open before v1 launches

---

## 10. Distribution & launch

### Pre-launch (1 week before)
- Newsletter issue #N: tease "next week, something free for the community" — no spoilers
- Soft-launch to 5 friends in OWASP Slack and HN-active acquaintances; collect "you should also handle X" feedback; pick the top 2 fixes only
- Record a 60-second screen capture of solving Mission 01 — for HN, LinkedIn, and Twitter/X

### Launch day (Tuesday or Wednesday, 09:00 CET)
- HN submission: "Show HN: agentdojo.live — practice attacking AI agents in your browser (free, hosted, open-source)"
- Cross-post to r/netsec, r/LocalLLaMA, r/MachineLearning
- LinkedIn post (link in first comment per your editorial principles)
- OWASP Slack #agentic-security
- Newsletter issue: launch announcement with three concrete ASI mappings
- Reply to every HN comment for the first 4 hours

### Post-launch
- Day 1: blog post on aminrj.com — "Why I built a free agent attack playground"
- Day 7: retrospective post — "Week 1 stats: N solves, M unique IPs, K creative payloads"
- Week 2 onward: one new mission per month, each launch is a content event
