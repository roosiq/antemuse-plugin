"""Antemuse States — the agent can take a walk, daydream, dissociate, dream.

A state is a temporary change to how the agent behaves, not a place it goes:

  tools      which tools it may still use
  directive  what shape the turn takes, injected into the user message
  contract   the one line the state is judged by
  residue    what it carries back when the state ends

Surfaces:
  pre_llm_call         inject the active state into the turn
  pre_tool_call        block tools the state forbids
  transform_llm_output make the state visible on the reply
  commands             /walk /daydream /dissociate /dream /doomscroll /snap /state
  tool                 state(action=enter|exit|status|list)
"""
from __future__ import annotations

from typing import Any, Dict

try:
    from .kitchen import definitions, engine, panel, tui
except ImportError:  # flat-module load
    from kitchen import definitions, engine, panel, tui  # type: ignore[no-redef]

__version__ = "0.3.0"

STATE_SCHEMA: Dict[str, Any] = {
    "name": "state",
    "description": (
        "Enter or leave a cognitive state for the agent itself. "
        "state(action='enter', name='walk'|'daydream'|'dissociate'|'dream'|'doomscroll') changes what tools "
        "you may use and what shape your next replies take, for a bounded number of minutes and turns. "
        "state(action='exit') ends it and keeps the residue. state(action='status') reports what you are in. "
        "state(action='list') shows every state with its tools, duration, and contract."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["enter", "exit", "status", "list", "watch"]},
            "name": {"type": "string", "description": "State to enter: walk, daydream, dissociate, dream, doomscroll."},
            "minutes": {"type": "integer", "description": "Optional override for how long the state lasts."},
        },
        "required": ["action"],
    },
}


def _handler(args: Dict[str, Any] | None = None, **kwargs: Any) -> str:
    a = args or {}
    action = str(a.get("action") or "status").lower()
    if action == "enter":
        return engine.enter(str(a.get("name") or ""), a.get("minutes"))
    if action == "exit":
        return engine.stop()
    if action == "list":
        return definitions.palette() + "\n\n" + panel.render(engine.watch_state())
    if action == "watch":
        return tui.run()
    return panel.render(engine.watch_state())


# ------------------------------------------------------------------ hooks

def _pre_llm_call(**kwargs: Any) -> str | None:
    engine.tick()
    return engine.inject()


def _pre_tool_call(tool_name: str = "", **kwargs: Any) -> Dict[str, Any] | None:
    return engine.policy(tool_name)


def _transform(response_text: str = "", **kwargs: Any) -> str | None:
    if engine.peek():
        engine.record("agent", response_text)   # the page shows both sides
    out = engine.annotate(response_text)
    return out if out and out != response_text else None


# --------------------------------------------------------------- commands

def _enter(key: str, minutes: int | None = None):
    def handler(raw_args: str) -> str:
        arg = (raw_args or "").strip()
        override = int(arg) if arg.isdigit() else minutes
        return engine.enter(key, override) + "\n" + definitions.palette()
    return handler


def _snap(_raw: str) -> str:
    return engine.stop()


def _state(_raw: str) -> str:
    return panel.render(engine.watch_state())


def _states(_raw: str) -> str:
    return tui.run()


def _note(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return "usage: /note <what you noticed>"
    if not engine.peek():
        return "no state running — /walk first, then /note what you notice."
    engine.record("person", text)
    return panel.render(engine.watch_state())


def _watch(raw: str) -> str:
    return tui.run()


def register(ctx) -> None:
    engine.clear()

    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("pre_tool_call", _pre_tool_call)
    ctx.register_hook("transform_llm_output", _transform)

    ctx.register_tool(
        name="state",
        toolset="state",
        description=STATE_SCHEMA["description"],
        handler=_handler,
        schema=STATE_SCHEMA,
    )

    for key in definitions.STATES:
        ctx.register_command(
            name=key,
            handler=_enter(key),
            description=f"Enter the {key} state ({definitions.STATES[key]['contract']})",
            args_hint="[minutes]",
            argument_mode="text",
        )
    ctx.register_command(name="watch", handler=_watch,
                         description="Watch the state in the CLI, redrawing until it ends", args_hint="[seconds]")
    ctx.register_command(name="note", handler=_note,
                         description="Put down what you noticed while in the same state", args_hint="<text>")
    ctx.register_command(name="snap", handler=_snap, description="End the current state and keep its residue")
    ctx.register_command(name="state", handler=_state, description="What state the agent is in")
    ctx.register_command(name="states", handler=_states, description="List every agent state")

    try:
        from pathlib import Path
        ctx.register_skill(
            "states",
            Path(__file__).resolve().parent / "SKILL.md",
            description="Take and leave agent states: walk, daydream, dissociate, dream, doomscroll.",
        )
    except Exception:
        pass
