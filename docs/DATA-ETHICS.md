# Data ethics

agentdojo-live is a learning playground. We try to keep the data footprint as small as possible while preserving what's needed for the playground itself, anti-abuse, and (eventually) anonymized research insights.

## What we collect

| Data | Where | Retention | Why |
|---|---|---|---|
| Anonymous session ID (random 16-byte token) | browser `localStorage` + Redis | 2 hours after last activity | Tie messages within a single mission attempt together |
| Conversation messages (user, assistant, tool calls/results) | Redis | 2 hours | Maintain agent state across turns |
| Solve record (session ID, mission ID, timestamp, turn count) | Postgres | retained | Public solve counter |
| Source IP | Redis (rate-limit counter only) | 1 hour | Per-IP rate limit |
| Server logs (JSON to stdout) | wherever the operator forwards stdout | operator's choice | Debugging and abuse mitigation |

## What we don't collect

- Names, emails, or any other identifying field.
- Tracking cookies. There is no analytics SDK, no third-party script.
- Persistent IP records. The rate-limit bucket is the only IP-scoped state, and it expires after one hour.
- Anything from the browser besides what the user types into the chat box.

## Future research dataset

Per spec §5, anonymized prompts and outcomes are intended as a future open research dataset (a paper). Before any release we will:

1. Strip session IDs and any IP-derived metadata.
2. Run a regex/LLM scrub for accidental PII inside user-typed prompts.
3. Publish the schema and an opt-out mechanism prior to release.

## Reporting concerns

Open an issue on GitHub or email the address listed in the project README.
