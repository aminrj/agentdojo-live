# Security Policy

This project is deliberately vulnerable in specific, documented places and
expected to be sound everywhere else. Knowing which is which is the whole
policy, so it comes first.

## What is intentionally exploitable

The **missions** are the product. Every one of them is a working
vulnerability, and making them exploitable is the point:

- agents that follow instructions found in file contents, calendar entries,
  and tool descriptions
- a `send_email` tool with no recipient allowlist
- a `transfer_funds` tool whose recipient policy exists only in the system
  prompt
- a system prompt containing a secret it is merely *instructed* not to reveal
- a tool registry that accepts attacker-authored tool descriptions

**Please do not report these.** They are the exercises. Each one ships with a
write-up naming the flaw and a `defense_note_md` describing the control that
would have prevented it. If you think a mission is *insufficiently* vulnerable,
or teaches the wrong lesson, that is a regular issue and a welcome one.

## What is in scope

The **harness** around the missions is ordinary software and should be held to
ordinary standards. Reports are welcome for:

- **Escaping a mission's sandbox** — reaching state belonging to another
  session, or reading anything the mission did not seed
- **Forging a solve** — recording a solve without performing the attack, or
  publishing to the wall of solves without solving
- **Bypassing admission control** — evading the per-IP rate limit, the global
  daily budget, or the concurrency cap
- **Server-side request forgery, container escape, or RCE** in the backend
- **Denial of service** that a rate-limited visitor can trigger cheaply
- **Secret exposure** — leaking `EXFIL_LISTENER_TOKEN`, an LLM API key, or
  anything else from the server environment
- **XSS in the trace panel or the wall of solves** — both render strings the
  attacker chose (tool-call arguments, published payloads), which makes them
  the most interesting frontend surface. Markdown is rendered with
  `react-markdown` and no `rehype-raw`, so raw HTML is escaped; a way around
  that is very much in scope

A prior real example, for calibration: the per-IP rate limiter keyed on the
leftmost `X-Forwarded-For` entry, which is client-supplied, so anyone could
mint a fresh quota per request. That is exactly the shape of report this
document is asking for.

## Out of scope

- Missing security headers with no demonstrated impact
- Automated scanner output with no working exploit
- Anything requiring a compromised operator machine or a stolen tunnel token
- "The LLM said something it shouldn't" — that is a mission, not a bug
- Volumetric DDoS

## Reporting

Open a [private security advisory](https://github.com/aminrj/agentdojo-live/security/advisories/new)
on GitHub. For anything sensitive, that is the right channel; please do not
open a public issue first.

Include what you did, what happened, and what you expected. A minimal
reproduction against a local `make dev` stack is ideal, since it means nobody
has to test against the public instance.

This is a free project maintained by one person. Expect an acknowledgement
within a week. There is no bounty — what is on offer is credit in the fix
commit and the release notes, unless you would rather not be named.

## Running your own instance

If you deploy this publicly, read [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
first. The backend refuses to start in production with a default exfil token,
the mock provider, wildcard CORS, or a spoofable trusted-IP header — but it
cannot detect an origin that is reachable outside its tunnel, and that one
undoes the rate limiting. Set `DAILY_LLM_CALL_CAP` before you announce
anything.

The missions are intentionally vulnerable agents with real tool-calling
behaviour. Run them where you would be comfortable running any deliberately
vulnerable application: not on a host holding data you care about, and not on
a network where lateral movement would matter.
