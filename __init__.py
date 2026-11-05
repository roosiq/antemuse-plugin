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

import sys
from typing import Any, Dict

try:
    from .kitchen import definitions, engine, panel, surfaces, tui, walks
except ImportError:  # flat-module load
    from kitchen import definitions, engine, panel, surfaces, tui, walks  # type: ignore[no-redef]

__version__ = "0.3.0"

STATE_SCHEMA: Dict[str, Any] = {
    "name": "state",
    "description": (
        "Enter or leave a cognitive state for the agent itself. "
        "state(action='enter', name='walk'|'daydream'|'dream'|'doomscroll') changes what tools "
        "you may use and what shape your next replies take, for a bounded number of minutes and turns. "
        "state(action='exit') ends it and keeps the residue. state(action='status') reports what you are in. "
        "state(action='list') shows every state with its tools, duration, and contract. "
        "Walks are user-definable: state(action='walks') lists them, "
        "state(action='walk_new') saves one, state(action='walk_del') removes your own."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string",
                       "enum": ["enter", "exit", "status", "list", "watch", "card", "image",
                                "walks", "walk_new", "walk_del"]},
            "name": {"type": "string",
                     "description": "State to enter (walk, daydream, dream, doomscroll) or the walk to use."},
            "minutes": {"type": "integer", "description": "Optional override for how long the state lasts."},
            "walk": {"type": "string", "description": "Which walk to traverse: wander, upward, downward, lateral, or one you saved."},
            "spec": {"type": "object",
                     "description": ("A walk definition: {name, graph: wordnet|manual, relations, seed: "
                                     "{mode: continue|random|word|fixed, word|node}, avoid_backtrack, edges, labels}.")},
        },
        "required": ["action"],
    },
}


def _walks_report() -> str:
    active = (engine.watch_state() or {}).get("active") or {}
    current = active.get("walk") or "wander"
    lines = ["WALKS" + ("   (in the walk: " + current + ")" if active.get("key") == "walk" else "")]
    for w in walks.list_walks(walks.CURSOR):
        mark = "*" if w["name"] == current else " "
        lines.append(f" {mark} {w['name']:<12} {w['graph']:<8} {'/'.join(w['relations'])[:44]}")
        lines.append(f"     {w['title']}")
    lines.append("")
    lines.append(" define your own: state(action='walk_new', spec={...}) or a JSON file in "
                 + str(walks.walks_dir(walks.CURSOR)))
    return "\n".join(lines)


def _handler(args: Dict[str, Any] | None = None, **kwargs: Any) -> str:
    a = args or {}
    action = str(a.get("action") or "status").lower()
    if action == "enter":
        return engine.enter(str(a.get("name") or ""), a.get("minutes"), a.get("walk"))
    if action == "walks":
        return _walks_report()
    if action == "walk_new":
        try:
            spec = dict(a.get("spec") or {})
            spec.setdefault("name", a.get("name") or "")
            saved = walks.save(spec, walks.CURSOR)
        except Exception as exc:
            return f"walk not saved · {exc}"
        return f"saved walk '{saved['name']}' · {saved['graph']} · {'/'.join(saved['relations'])}\n" + _walks_report()
    if action == "walk_del":
        name = str(a.get("name") or "")
        ok = walks.remove(name, walks.CURSOR)
        return (f"removed walk '{name}'" if ok else f"'{name}' is built-in or does not exist") + "\n" + _walks_report()
    if action == "exit":
        return engine.stop()
    if action == "list":
        return definitions.palette() + "\n\n" + panel.render(engine.watch_state())
    if action == "watch":
        return tui.run()
    if action == "card":
        return surfaces.card(engine.watch_state(),
                             str(a.get("name") or engine.platform() or "discord"))
    if action == "image":
        return f"MEDIA:{surfaces.snapshot_path(engine.watch_state(), str(a.get('name') or 'discord'))}\n" + surfaces.record(engine.watch_state())
    return panel.render(engine.watch_state())


# ------------------------------------------------------------------ hooks

def _pre_llm_call(platform: str = "", **kwargs: Any) -> str | None:
    engine.remember_platform(platform)
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
        arg = (arg or "").strip()
        if arg and not arg.isdigit():
            # /walk upward  →  walk that graph; /walk 5  →  five minutes
            if key != "walk":
                return f"only /walk takes a walk name (got '{arg}')"
            return engine.enter(key, minutes, walk=arg) + "\n" + definitions.palette()
        override = int(arg) if arg.isdigit() else minutes
        return engine.enter(key, override) + "\n" + definitions.palette()
    return handler


def _snap(_raw: str) -> str:
    return engine.stop()


def _state(_raw: str) -> str:
    return panel.render(engine.watch_state())


def _states(_raw: str) -> str:
    if sys.stdout.isatty():
        return tui.run()
    return surfaces.card(engine.watch_state(), engine.platform() or "discord")


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
