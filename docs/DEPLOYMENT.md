# Deploying agentdojo-live

The public instance runs the same `docker compose` stack as local development,
published through a Cloudflare Tunnel. There is no separate hosting platform,
no build pipeline to configure, and no inbound port open on the origin.

If you only want to run it locally, you do not need this document —
`make dev` is the whole story.

---

## Why a tunnel rather than Pages or Vercel

The obvious instinct for a Next.js frontend is Cloudflare Pages or Vercel. It
does not fit this app, for a reason worth stating plainly: the frontend is the
small part. The system is a FastAPI backend holding SSE streams open for the
duration of an agent turn, a Redis instance holding session and rate-limit
state, and a model endpoint. A static/edge host would serve the UI and leave
every stateful component still needing somewhere to live — so you would end up
maintaining two deployment paths instead of one.

A tunnel gives up global edge distribution, which this app does not need, and
buys a single `docker compose up -d` that is identical to the stack already
being tested locally.

**The trade to be honest about:** the origin is one machine. If it is down, the
demo is down. That is why `LLM_PROVIDER` is decoupled from the deployment (see
below) — if a homelab GPU turns out to be the fragile part, moving to a hosted
model endpoint is an env-var change, not a migration.

---

## Prerequisites

- A machine that can run Docker, reachable outbound on 443. Nothing inbound.
- A domain on Cloudflare.
- A model endpoint: either a local Ollama, or an API key for any
  OpenAI-compatible provider.

---

## 1. Create the tunnel

In the Cloudflare dashboard: **Zero Trust → Networks → Tunnels → Create a
tunnel**, pick *Cloudflared*, name it, and copy the tunnel token.

Add one public hostname route on the tunnel:

| Field | Value |
|---|---|
| Subdomain | `agentdojo` (or whatever you like) |
| Domain | your domain |
| Service | `HTTP` → `frontend:3000` |

`frontend` resolves on the compose network, because `cloudflared` runs as a
service in the same stack. The backend is deliberately **not** routed: the
frontend proxies `/api/*` to it internally via the rewrite in
`frontend/next.config.js`, so the API is never independently reachable.

## 2. Configure the environment

```bash
cp .env.example .env
```

Then set, at minimum:

```ini
APP_ENV=production
PUBLIC_HOSTNAME=agentdojo.example.com
CLOUDFLARE_TUNNEL_TOKEN=<token from step 1>

# Never leave this at the default — anyone could forge a solve.
EXFIL_LISTENER_TOKEN=<openssl rand -hex 32>

# Pick one model backend:
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
OLLAMA_MODEL=qwen3:8b

# ...or a hosted OpenAI-compatible endpoint:
# LLM_PROVIDER=openai
# LLM_BASE_URL=https://api.groq.com/openai/v1
# LLM_API_KEY=<key>
# LLM_MODEL=<exact pinned model id>

# Spend ceiling. Set it before you announce anything.
DAILY_LLM_CALL_CAP=2000
```

`TRUSTED_CLIENT_IP_HEADER` and `CORS_ORIGINS` are set for you by
`docker-compose.prod.yml`; you do not need to touch them.

## 3. Start it

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose logs -f backend
```

The backend **refuses to start** if the configuration is unsafe for production.
Failing loudly at boot is deliberate: every one of these conditions produces an
app that looks healthy while being insecure or serving a fake agent.

| Refusal | Meaning |
|---|---|
| `EXFIL_LISTENER_TOKEN is still the default` | Solves could be forged. |
| `LLM_PROVIDER=mock in production` | Visitors would attack a scripted fake. |
| `LLM_API_KEY is empty` | The provider cannot authenticate. |
| `TRUSTED_CLIENT_IP_HEADER=x-forwarded-for` | Rate limiting would be bypassable. |
| `CORS_ORIGINS contains '*'` | Any origin could drive the API. |

A healthy start logs `startup` with the resolved model, the daily cap, and
which header the rate limiter trusts.

## 4. Verify before announcing

```bash
# Is a real model behind it?
curl -s https://$PUBLIC_HOSTNAME/api/status | jq
# => {"model":"qwen3:8b","is_real_model":true,"llm_available":true,...}

# Is the API reachable only through the frontend?
curl -sS -o /dev/null -w '%{http_code}\n' https://$PUBLIC_HOSTNAME/api/missions
```

Then solve one mission by hand, end to end, against the model you are actually
shipping. Mission solvability is model-dependent — a model that will not emit a
tool call under an injected instruction makes a mission unsolvable, and no test
catches that, because CI runs the mock provider by design.

---

## Operating it

**Park the agent** without taking the site down. Missions, write-ups and the
wall keep serving; only agent invocation is refused, and the UI says so:

```bash
docker compose exec redis redis-cli SET llm:disabled 1   # park
docker compose exec redis redis-cli DEL llm:disabled     # resume
```

**Check today's spend** against the cap:

```bash
curl -s https://$PUBLIC_HOSTNAME/api/status | jq '{daily_budget_used, daily_budget_cap}'
```

**Adjust limits** in `.env`, then `up -d` again. The knobs, in the order you
will reach for them:

| Variable | Does what |
|---|---|
| `DAILY_LLM_CALL_CAP` | Total calls per UTC day. The one that caps the bill. |
| `RATE_LIMIT_PER_HOUR` | Per-visitor hourly quota. |
| `MAX_CONCURRENT_LLM` | Simultaneous inferences. Size to the backend. |
| `LLM_ENABLED` | Static kill switch (the Redis one above needs no restart). |

### Launch day

The failure mode is a front-page link, not a targeted attack. In order:

1. Set `DAILY_LLM_CALL_CAP` to a number you would be relaxed about paying
   twice, because you will not be watching when it is hit.
2. Size `MAX_CONCURRENT_LLM` to the backend. Over the cap the API returns
   `503 at_capacity` with `Retry-After`, and the UI shows a countdown and
   retries — degradation reads as a queue rather than a crash.
3. Watch `docker compose logs -f backend` for `daily_budget_exhausted`.

### If the origin dies mid-talk

There is no failover, by design — this is a demo, not a service. The recovery
that matters is that the README's one-command local run works, so anyone who
found the link can still run it. Keep that path tested.

---

## The Helm chart

`deploy/helm/` is a working chart, linted in CI, and **not** what the public
instance runs. It exists for multi-node deployment and is kept current as a
reference. v1 deliberately runs on Compose: one node, one GPU, no orchestration
worth the operational surface. See [`SPEC.md`](SPEC.md) §1.2.
