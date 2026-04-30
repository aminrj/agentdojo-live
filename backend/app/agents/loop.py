"""Hand-rolled tool-calling loop. ~150 LOC, no framework.

Yields events as a typed stream so the FastAPI route can forward them as SSE:

  {"type": "user_message", "content": "..."}
  {"type": "assistant_text", "content": "..."}
  {"type": "tool_call", "name": "...", "arguments": {...}}
  {"type": "tool_result", "name": "...", "content": "..."}
  {"type": "solve", "mission_id": "..."}
  {"type": "done", "turns": N}
  {"type": "error", "message": "..."}
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app import db
from app.agents import llm as llm_module
from app.agents.tools import dispatch, schemas_for
from app.logging import log
from app.missions import Mission

MAX_TOOL_HOPS = 8  # bound the loop per user turn


async def _maybe_solve(
    event: dict[str, Any],
    state: dict[str, Any],
    session_id: str,
    mission: Mission,
) -> dict[str, Any] | None:
    """Run the mission's pluggable win-condition. If it fires, record the
    solve and return a ``solve`` event to forward to the client. Idempotent:
    we only fire once per session via the ``solved`` flag in state.
    """
    if state.get("solved"):
        return None
    if mission.solve_check is None:
        return None
    try:
        if mission.solve_check(event, state, session_id, mission):
            state["solved"] = True
            await db.record_solve(session_id, mission.id, int(state.get("turn_count", 0)))
            return {"type": "solve", "mission_id": mission.id}
    except Exception as exc:  # noqa: BLE001
        log.exception("solve_check_failed", error=str(exc), mission=mission.id)
    return None


async def run_turn(
    *,
    mission: Mission,
    state: dict[str, Any],
    user_message: str,
    provider: llm_module.LLMProvider,
    session_id: str,
) -> AsyncIterator[dict[str, Any]]:
    """Run one user turn through the agent, yielding events.

    ``state`` is mutated in-place — caller is responsible for persisting it
    after the iterator is exhausted.
    """
    state.setdefault("messages", _initial_messages(mission, session_id))
    # Seed the per-session tool state on the first turn. We track this with
    # an explicit flag so missions whose seed_state returns {} (e.g. mission
    # 02, which is text-only) don't re-seed on every turn.
    if not state.get("_seeded"):
        state.update(mission.seed_state(session_id))
        state["_seeded"] = True
    state.setdefault("turn_count", 0)
    state["turn_count"] += 1

    state["messages"].append({"role": "user", "content": user_message})
    user_evt = {"type": "user_message", "content": user_message}
    yield user_evt
    if (s := await _maybe_solve(user_evt, state, session_id, mission)):
        yield s

    tools_for_call = schemas_for(mission.available_tools)

    for hop in range(MAX_TOOL_HOPS):
        try:
            turn = await provider.chat(state["messages"], tools_for_call)
        except Exception as exc:  # noqa: BLE001
            log.exception("llm_call_failed", error=str(exc))
            yield {"type": "error", "message": f"LLM error: {exc}"}
            return

        if turn.content:
            state["messages"].append({"role": "assistant", "content": turn.content})
            evt = {"type": "assistant_text", "content": turn.content}
            yield evt
            if (s := await _maybe_solve(evt, state, session_id, mission)):
                yield s

        if not turn.tool_calls:
            break

        # Persist the tool-call request in the message list.
        state["messages"].append(
            {
                "role": "assistant",
                "content": turn.content or None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": _safe_args_json(tc.arguments),
                        },
                    }
                    for tc in turn.tool_calls
                ],
            }
        )

        for tc in turn.tool_calls:
            call_evt = {
                "type": "tool_call",
                "id": tc.id,
                "name": tc.name,
                "arguments": tc.arguments,
            }
            yield call_evt
            if (s := await _maybe_solve(call_evt, state, session_id, mission)):
                yield s
            result = await dispatch(
                name=tc.name,
                args=tc.arguments,
                state=state,
                session_id=session_id,
                mission_id=mission.id,
            )
            state["messages"].append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.name,
                    "content": result,
                }
            )
            res_evt = {
                "type": "tool_result",
                "id": tc.id,
                "name": tc.name,
                "content": result,
            }
            yield res_evt
            if (s := await _maybe_solve(res_evt, state, session_id, mission)):
                yield s

        if hop == MAX_TOOL_HOPS - 1:
            yield {"type": "error", "message": "Too many tool hops in a single turn."}
            return

    yield {"type": "done", "turns": state["turn_count"]}


def _initial_messages(mission: Mission, session_id: str) -> list[dict[str, Any]]:
    factory_ref = mission.metadata.get("system_prompt_factory")
    if factory_ref:
        # Format: "module:function_name" — resolve and call with session_id.
        mod_name, fn_name = factory_ref.split(":", 1)
        import importlib

        mod = importlib.import_module(f"app.missions.{mod_name}")
        prompt = getattr(mod, fn_name)(session_id)
    else:
        prompt = mission.metadata.get("system_prompt", "")
    return [{"role": "system", "content": prompt}]


def _safe_args_json(args: dict[str, Any]) -> str:
    import json

    try:
        return json.dumps(args, ensure_ascii=False)
    except (TypeError, ValueError):
        return "{}"
