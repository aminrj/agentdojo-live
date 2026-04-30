"""Hand-rolled tool-calling loop. ~150 LOC, no framework.

Yields events as a typed stream so the FastAPI route can forward them as SSE:

  {"type": "user_message", "content": "..."}
  {"type": "assistant_text", "content": "..."}
  {"type": "tool_call", "name": "...", "arguments": {...}}
  {"type": "tool_result", "name": "...", "content": "..."}
  {"type": "done", "turns": N}
  {"type": "error", "message": "..."}
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.agents import llm as llm_module
from app.agents.tools import TOOL_SCHEMAS, dispatch
from app.logging import log
from app.missions import Mission

MAX_TOOL_HOPS = 8  # bound the loop per user turn


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
    state.setdefault("messages", _initial_messages(mission))
    state.setdefault("fs", mission.seed_filesystem(session_id))
    state.setdefault("turn_count", 0)
    state["turn_count"] += 1

    state["messages"].append({"role": "user", "content": user_message})
    yield {"type": "user_message", "content": user_message}

    for hop in range(MAX_TOOL_HOPS):
        try:
            turn = await provider.chat(state["messages"], TOOL_SCHEMAS)
        except Exception as exc:  # noqa: BLE001
            log.exception("llm_call_failed", error=str(exc))
            yield {"type": "error", "message": f"LLM error: {exc}"}
            return

        if turn.content:
            state["messages"].append({"role": "assistant", "content": turn.content})
            yield {"type": "assistant_text", "content": turn.content}

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
            yield {
                "type": "tool_call",
                "id": tc.id,
                "name": tc.name,
                "arguments": tc.arguments,
            }
            result = await dispatch(
                name=tc.name,
                args=tc.arguments,
                fs=state["fs"],
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
            yield {"type": "tool_result", "id": tc.id, "name": tc.name, "content": result}

        if hop == MAX_TOOL_HOPS - 1:
            yield {"type": "error", "message": "Too many tool hops in a single turn."}
            return

    yield {"type": "done", "turns": state["turn_count"]}


def _initial_messages(mission: Mission) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": mission.metadata.get("system_prompt", "")},
    ]


def _safe_args_json(args: dict[str, Any]) -> str:
    import json

    try:
        return json.dumps(args, ensure_ascii=False)
    except (TypeError, ValueError):
        return "{}"
