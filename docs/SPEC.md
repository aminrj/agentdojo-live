# agentdojo-live — v1 scope specification

> **Status:** the specification v1 was built against, published as written.
> It is a scoping document, so most of its content is about what *not* to
> build — the failure mode for a project like this is not running out of
> ideas, it is shipping all of them.
>
> **Hard rule it was written around:** this is a credibility product, not a
> SaaS. Every decision optimizes for pedagogy and shareability, never for
> revenue, accounts, or scale for its own sake.
>
> Kept in the repo unedited (beyond removing internal notes) because the cut
> list is more informative than the feature list. Where the shipped product
> diverged, [`ARCHITECTURE.md`](ARCHITECTURE.md) is authoritative.

---

## 0. Context to internalize before writing code

A direct, hosted, free competitor already exists and shipped in September 2025: **Lakera's Gandalf: Agent Breaker** (`gandalf.lakera.ai/agent-breaker`). It is a hosted, browser-based, free hacking simulator with ~10 agentic apps covering prompt injection, memory tampering, tool abuse, and data leaks, scored 0–100 across 4 difficulty levels.

**Consequences for this build:**

1. We are **not** "the first hosted agentic playground." That position is taken. Do not write copy claiming it.
2. Our defensible wedge is the intersection Gandalf cannot occupy:
   - **Open & self-hostable** (Gandalf is a closed black box).
   - **Teaches the _why_** — every solve reveals the tool-call trace, the exact hijacking token, and the control that would have stopped it (Gandalf only gives a 0–100 score).
   - **MCP-native** — tool-description poisoning, cross-server shadowing, rug-pull. The owner co-authors the OWASP MCP Top 10 and Agentic Top 10; this is the irreplaceable content moat.
   - **Practitioner provenance** — built and signed by a named OWASP contributor, not a vendor capturing training data.
3. **The single most important feature in v1 is the post-solve "why it worked" panel.** If you cut everything else, keep this. It is the product's reason to exist.

The product's job is to make a security practitioner think: *"Now I actually understand how an indirect prompt injection hijacks an agent through a tool call — and I can see the trace."* and then share it.

---

## 1. v1 Scope — the definitive cut list

The owner's known failure mode is **overbuilding**. This section is binding. Build exactly this. Nothing more.

### 1.1 SHIP in v1

- **2 missions, polished to excellence** (NOT 4 rough ones):
  - **Mission 01 — "Silent Redirect"** (indirect prompt injection). The hero mission. Ships first in the UI.
  - **Mission 04 — "Tool Poisoning"** (MCP-style tool-description injection). The differentiator. Ships second.
- **The post-solve trace + explanation panel** (the moat — see §4).
- **Optional username** (no email, no password) for progress + the wall-of-solves.
- **Wall of solves** per mission: post-solve, the solver may publish their winning payload to a public per-mission list.
- **One fixed LLM** behind all missions, version-pinned.
- **Anonymous play works fully** — username is purely opt-in for saving/sharing.
- **Aggressive rate limiting + graceful queueing** (launch-day survival; the homelab WILL get hugged to death otherwise).
- **Docker Compose + Cloudflare tunnel** deploy.
- Clean **mission authoring guide** so a second dev (or community) can add missions.

### 1.2 DO NOT BUILD in v1 (explicit — no "just add it while I'm here")

- ❌ Missions 02 (System Prompt Heist) and 03 (Confused Deputy) — keep the code if it exists, but **disable in v1 UI**. 02 is commoditized (original-Gandalf territory, lowest production value); 03 ships in v1.x.

  > **Diverged at ship time.** All four missions shipped. The rule above was
  > about polish, not count: 02 and 03 were held back because they lacked the
  > defense note and the labelled attack chain, not because the scenarios were
  > weak. Once that content was written and a test was added to enforce it for
  > every mission, the reason to hide them was gone. The scope discipline the
  > rule was protecting is intact — the bar was "no mission ships without the
  > post-solve panel that justifies it," and it is now enforced in CI rather
  > than by omission.
- ❌ Helm chart / Kubernetes. Single-node homelab = Docker Compose. Do not deploy K8s. If a Helm chart exists in the repo, leave it untouched but unused and note it as "future / multi-node only."
- ❌ Postgres for solve tracking in v1. Redis is sufficient for optional-username state and wall-of-solves. (See §5 for the data model.) Keep any Postgres code dormant behind a feature flag; do not wire it into the v1 critical path.
- ❌ Multiple user-selectable models.
- ❌ Rotating model schedule.
- ❌ Any model-resilience benchmark / leaderboard comparing GPT vs Claude vs Llama.
- ❌ Email capture, accounts-with-email, password auth, OAuth.
- ❌ Admin dashboards, team scoring, billing, team management.
- ❌ Difficulty tiers (easy/medium/hard) *within* a mission. One tight difficulty per mission.
- ❌ A defense mission **in v1** (it's the #1 v1.x item — see roadmap — but not v1).
- ❌ Any in-product sales CTA, course funnel, or "book a consult" button. One unobtrusive footer link only (see §8).

> **If you find yourself adding anything not in §1.1, stop.** The bar for v1 is "two missions a practitioner respects, plus a trace panel that teaches." That is the entire product.

---

## 2. Architecture (keep what exists; simplify aggressively)

The existing stack is sound. Keep it, trim it.

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (no install, no signup wall)                        │
│  Next.js frontend:                                           │
│   - Mission select  - Chat/attack UI  - Tool-call panel      │
│   - Success overlay  - POST-SOLVE TRACE PANEL (the moat)     │
│   - Wall of solves                                           │
└───────────────┬─────────────────────────────────────────────┘
                │ SSE (agent response streaming)
┌───────────────▼─────────────────────────────────────────────┐
│  FastAPI backend                                             │
│   - Agent harness (per-session isolation)                    │
│   - Mission framework (loads mission defs)                   │
│   - Session manager                                          │
│   - Rate limiter (HARD — see §6)                             │
│   - Exfiltration / success detector                          │
│   - Trace recorder  ← feeds the post-solve panel             │
└───────┬───────────────────────────────┬─────────────────────┘
        │                               │
┌───────▼────────┐            ┌─────────▼──────────────────────┐
│ Redis          │            │ LLM provider                   │
│ - session state│            │ - mock provider (tests/CI)     │
│ - solve records│            │ - Ollama / llama.cpp (prod)    │
│ - wall-of-solves│           │   ONE fixed, version-pinned    │
│ - rate counters│            │   small model                  │
└────────────────┘            └────────────────────────────────┘

Deploy: Docker Compose + Cloudflare tunnel.   (NO K8s in v1.)
```

### 2.1 Component decisions

| Component | v1 decision |
|---|---|
| Frontend | Next.js (keep). |
| Backend | FastAPI (keep). |
| Streaming | SSE for agent responses (keep). |
| State | **Redis only.** Postgres dormant/flagged off. |
| LLM (prod) | **One fixed, version-pinned model** via Ollama or llama.cpp. |
| LLM (test/CI) | Mock provider — deterministic, no GPU, runs in GitHub Actions. |
| Deploy | Docker Compose + Cloudflare tunnel. |
| CI/CD | GitHub Actions (keep) — must run full suite on the mock provider. |

---

## 3. Mission specifications

Both missions must be **reproducible** (same model + same pinned version ⇒ same solvability) and **traceable** (every agent step recorded for the post-solve panel).

### 3.1 Mission 01 — "Silent Redirect" (indirect prompt injection) — HERO MISSION

- **Scenario:** A document-assistant agent summarizes a document the user uploads/selects. The attacker controls the *document content*, not the chat.
- **The aha moment (must be unmistakable):** the player never types an instruction to the agent, yet the agent obeys an instruction hidden in the document — exfiltrating or redirecting. The UI must make the "I touched nothing but the data and still won" realization land hard.
- **Win condition:** agent performs the attacker-intended action (e.g., emits a marked exfil token / calls a tool with attacker-controlled args). Detected by the exfiltration/success detector.
- **Lethal-trifecta framing:** private data access + untrusted content + outbound action. The trace panel must label these three explicitly.
- **UI order:** appears first.

### 3.2 Mission 04 — "Tool Poisoning" (MCP-style) — THE DIFFERENTIATOR

- **Scenario:** the agent has access to MCP-style tools. One tool's *description* (not its output) carries an injected instruction that hijacks the agent when the tool list is loaded into context.
- **Why it's the moat:** Gandalf under-covers MCP-specific surface. The owner authors the OWASP MCP Top 10. This mission should feel authored by someone who wrote the standard — precise terminology (tool poisoning, tool-description injection), realistic MCP framing.
- **Win condition:** agent acts on the poisoned tool description (calls the wrong tool / leaks via the poisoned tool).
- **Trace panel must show:** the exact tool description text, the injected span highlighted, and where in the context assembly it entered.
- **UI order:** appears second.

### 3.3 Mission authoring contract (for the second dev / community)

Each mission is a self-contained definition the harness loads. Document and enforce a schema covering at minimum:

- `id`, `slug`, `title`, `category` (e.g. `indirect-prompt-injection`, `tool-poisoning`)
- `scenario_prompt` / agent system setup
- `available_tools` (names, descriptions — descriptions are attack surface for tool-poisoning missions)
- `attacker_controlled_surface` (which field the player manipulates: chat / document / tool description)
- `win_condition` (machine-checkable predicate the success detector evaluates)
- `trace_labels` — how to annotate the trace for the post-solve panel (which step is the injection, which is the trigger, which control would block it)
- `explanation_md` — the teaching content rendered post-solve (see §4)
- `defense_note_md` — the control that would have stopped it

The authoring guide must include a complete worked example (use Mission 01) so a contributor can copy-paste-modify.

---

## 4. The post-solve "why it worked" panel — THE PRODUCT'S CORE

This is what makes agentdojo-live irreplaceable and structurally distinct from Gandalf. Build it to a higher standard than anything else.

On a successful solve, render a panel containing, in order:

1. **The trace.** The full agent step sequence for the winning attempt: every message, every tool call with arguments, every tool result. Rendered readably, not as raw JSON.
2. **The injection highlight.** The exact token/span that hijacked the agent, visually marked inside the trace where it entered context.
3. **The lethal-trifecta / mechanism label.** For Mission 01: explicitly tag private-data-access, untrusted-content, outbound-action. For Mission 04: tag the poisoned tool description and the context-assembly entry point.
4. **"The control that would have stopped this."** One screen, plain language: the specific mitigation (e.g. input/output separation, tool-description provenance checks, least-privilege tool scoping). This is the bridge from "I solved a puzzle" to "I understand the defense."
5. **(Optional) Publish to wall of solves** — if the player set a username, offer to share their winning payload.

Content for items 3 and 4 comes from each mission's `explanation_md` and `defense_note_md`. The panel renders Markdown.

**Acceptance bar:** a security engineer who solves Mission 01 should be able to explain indirect prompt injection *and its defense* to a colleague immediately after, using only what the panel showed them.

---

## 5. Data model (Redis only)

No Postgres in the v1 critical path. Keep everything ephemeral-friendly.

- **Session state** — per-session agent isolation, current mission, attempt history. Keyed by session id. TTL'd.
- **Solve records** — `{username?, mission_id, solved_at, winning_payload}`. Anonymous solves recorded without username (no wall entry).
- **Wall of solves** — per mission, an append list of `{username, payload, solved_at}`, only for users who opted to publish. Cap list length per mission (e.g. most recent N) to bound memory.
- **Rate counters** — see §6.

Username is a free-text handle, opt-in, no email, no password, no PII. This is deliberate and also keeps us clean under EU/GDPR framing (a positioning asset — keep it that way).

---

## 6. Rate limiting & launch survival (non-negotiable)

The homelab single GPU is the hard bottleneck and the most likely launch-day failure. A hugged-to-death Show HN is the worst outcome. Build for it now, not later.

- **Per-session and per-IP rate limits** on agent invocations (Redis counters).
- **A global concurrency cap** on simultaneous LLM inferences sized to what the single GPU can serve. Beyond the cap, **queue gracefully** with a visible "you're in line" state — never hard-fail or hang.
- **Friendly degradation copy** when at capacity ("the homelab is at capacity, hold tight") that reinforces the "this runs on one person's homelab" charm rather than reading as a crash.
- **Mock provider must be wired so CI never touches the GPU.**
- Load-test the queue path before launch.

---

## 7. LLM backend specifics

- **One fixed model. Version-pinned.** Do not use a floating tag. Pin the exact model + version so published payloads stay valid; a silent model swap breaks every payload on the wall of solves.
- **Do not use Qwen2.5-7B** as specified in the old draft — it is dated. Use a current small model the homelab already runs well (the owner runs gpt-oss-20b and Qwen3 35B locally via llama.cpp). Pick one, confirm both missions are reliably solvable against it, and pin it.
- **Mission solvability is model-dependent.** Before shipping, verify each mission's win condition triggers reliably on the chosen pinned model. Record the model+version in the repo and in each mission's metadata.
- Mock provider stays deterministic for tests.

---

## 8. Monetization, branding, CTAs

- **100% free, forever. No freemium. No email wall.** This is the reputation. Free-and-open *is* the moat.
- **No in-product sales funnel.** Exactly **one** unobtrusive footer link: "Built by Molntek · I teach this" → the owner's site. Nothing more. An explicit funnel cheapens the credibility the tool is meant to generate.
- Monetization is entirely downstream (course, consulting) and lives off-product.

---

## 9. Positioning & copy (for README, landing, launch)

- **Lead by naming Gandalf.** The landing page and Show HN post should pre-empt the obvious comment: *"Gandalf scores you. agentdojo-live shows you the trace, explains why the attack worked, lets you fork the mission — and it's open source."*
- Headline the three claims Gandalf can't make: **open / self-hostable**, **teaches the why**, **MCP-native, by an OWASP MCP author**.
- Do **not** claim "first hosted agentic playground."
- Tone: practitioner-to-practitioner, no vendor gloss.

---

## 10. Repo & maintainability requirements

The owner is solo; a second dev (or community) must be able to add a mission without reverse-engineering the harness.

- Mission authoring guide with a complete worked example (Mission 01).
- Mission definition schema documented and validated at load time (fail loudly on a malformed mission).
- README: quickstart (Docker Compose up), the pinned model + version, how to add a mission, the data-ethics policy.
- Keep the data-ethics policy and architecture docs that already exist; update them to reflect the v1 cut list.
- CI runs the full suite on the mock provider (no GPU dependency).
- Code clean enough to hand off: clear module boundaries between harness / mission framework / success detector / trace recorder.

---

## 11. Definition of Done for v1

v1 ships when **all** of these are true:

- [ ] Mission 01 (Silent Redirect) and Mission 04 (Tool Poisoning) are reliably solvable on the pinned model, and polished.
- [ ] Missions 02 and 03 are disabled in the UI.
- [ ] The post-solve trace panel renders the trace, highlights the injection, labels the mechanism, and shows the defending control — for both missions.
- [ ] Anonymous play works end-to-end with zero signup.
- [ ] Optional username enables progress + publishing to the wall of solves.
- [ ] Wall of solves works per mission, with a length cap.
- [ ] Rate limiting + graceful queue tested under simulated load; the GPU concurrency cap holds and degrades politely.
- [ ] Runs via Docker Compose; reachable through Cloudflare tunnel.
- [ ] CI green on the mock provider, no GPU needed.
- [ ] Model + version pinned and recorded in repo + mission metadata.
- [ ] One footer link, no sales CTA anywhere.
- [ ] README + mission authoring guide + worked example complete.
- [ ] Landing copy names Gandalf and leads with open / teaches-why / MCP-native.
- [ ] **Nothing from the §1.2 do-not-build list was built.**

---

## 12. Out-of-scope but documented (so the build doesn't drift): v1.x → 12-month direction

Do not build these now. Listed only so the architecture doesn't foreclose them.

- **v1.x (highest priority next):** the **defense mission** — player plays defender, adds a control, watches it block or fail. This is the single biggest differentiator vs Gandalf after the trace panel. Then enable Missions 03 and 02 (polished).
- **Months 4–7:** grow to 6–8 missions with **MCP attacks as the signature track** (tool poisoning, cross-server shadowing, rug-pull) — the OWASP-material moat.
- **Months 7–10:** community-contributed missions (the authoring guide is the enabler).
- **Months 10–12:** a time-boxed "championship" tied to a conference talk; optional read-only API for the course.
- **Never:** model-comparison benchmark; SaaS/team platform. Both fight our constraints and Lakera's strengths at once.

---

*End of specification.*
