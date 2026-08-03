# Contributing

The most useful contribution is **a new mission**. The harness exists to make
missions cheap to write; adding one is a single self-contained Python file that
the registry picks up automatically.

Read [`docs/ADDING-A-MISSION.md`](docs/ADDING-A-MISSION.md) for the authoring
contract and a full worked example.

## The bar for a mission

A mission is not accepted because the attack works. It is accepted because
someone who solves it can explain the vulnerability afterwards. Concretely,
every mission must ship:

| Field | What it has to do |
|---|---|
| `briefing_md` | Describe the target and the objective **without spoiling the exploit** |
| `writeup_md` | Name the vulnerability class and why the attack worked |
| `defense_note_md` | The control that would have stopped it, in plain language |
| `trace_labels` | Label the attack chain so the trace panel can annotate it |
| `hint_1`, `hint_2` | Progressive nudges, not answers |
| `solve_check` | A win condition that cannot be faked by saying the right words |

These are enforced by tests in `backend/tests/test_missions.py`. Two missions
once sat unshippable for a release because nothing checked them, which is why
the checks exist.

The acceptance question for `defense_note_md`: **could a solver explain this
defense to a colleague immediately after reading it?** If it needs a paper to
follow, it is not there yet.

## Scope

This project stays small on purpose. [`docs/SPEC.md`](docs/SPEC.md) §1.2 lists
what is deliberately not being built and why — model leaderboards, accounts,
team features, in-product sales funnels. Please read it before proposing
something structural; a rejected large PR wastes your time more than mine.

New missions, better teaching content, and fixes are always in scope.

## Development

```bash
cp .env.example .env
make dev                 # full stack, mock LLM, no GPU
```

Before opening a PR:

```bash
make test                          # backend: pytest on the mock provider
cd backend && ruff check .
cd frontend && npx tsc --noEmit && npm run build
```

CI runs the same three checks and needs no GPU — the mock provider drives each
mission's exploit path deterministically via a trigger word. If you add a
mission, add its path to `MockProvider` so CI can exercise the win condition.

Please verify a new mission against a **real** model too, and say which one in
the PR. Solvability is model-dependent, and the mock provider proves the
plumbing works, not that the attack does.

## Security

Do not report the missions' vulnerabilities — those are the exercises. For
anything in the harness around them, see [`SECURITY.md`](SECURITY.md).

## Conduct

Be straightforward and assume good faith. This is a small project about
breaking things safely; keep it that way.
