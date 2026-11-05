"""Antemuse Room — an automated cycle of concept discovery and movement.

Surfaces:
  tool  room(action=...)      agents drive the machine
  cmd   /room <verb>          humans drive the same machine

Phases alternate between movement (discover/unpack, flip, shift, connect) and
state (walk, daydream, dream, dissociate, doomscroll), with converge closing an
arc. One tick advances one phase; a state phase resolves itself, a move phase
hands out a brief and waits for a spark.
"""
from __future__ import annotations

from typing import Any, Dict

try:
    from .kitchen import phases, room as room_mod, store
except ImportError:  # flat-module load
    from kitchen import phases, room as room_mod, store  # type: ignore[no-redef]

__version__ = "0.2.0"

ROOM_SCHEMA: Dict[str, Any] = {
    "name": "room",
    "description": (
        "Antemuse Room: an automated room that cycles through phases of concept discovery and movement. "
        "action=step advances one phase and returns what to write; a state phase (walk, daydream, dream, "
        "dissociate, doomscroll) resolves itself, a move phase (discover, flip, shift, connect) expects a spark. "
        "action=commit takes 'title :: because ... :: do this first', scores it, places it in the room, and "
        "advances the phase. action=poster returns a PNG path for humans and vision models; action=status returns "
        "the text projection for language models. Keep calling step/commit to let the room run."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["step", "commit", "status", "poster", "phases", "phase", "reset"],
                "description": "What to do in the room.",
            },
            "text": {"type": "string", "description": "For action=commit: 'title :: because ... :: do this first'."},
            "with_phase": {"type": "string", "description": "For action=phase: jump to this phase key."},
            "seed": {"type": "string", "description": "For action=reset: optional first seed."},
        },
        "required": ["action"],
    },
}


def _room_or_new(seed: str | None = None) -> Dict[str, Any]:
    existing = room_mod.load()
    return existing or room_mod.create(seed)


def _handler(args: Dict[str, Any] | None = None, **kwargs: Any) -> str:
    a = args or {}
    action = str(a.get("action") or "status").lower()

    if action == "reset":
        room_mod.save(None)
        return "room cleared.\n\n" + room_mod.step(room_mod.create(a.get("seed")))

    if action == "phases":
        return phases.palette()

    room = _room_or_new(a.get("seed"))

    if action == "phase":
        key = phases.resolve(str(a.get("with_phase") or ""))
        if not key:
            return f"unknown phase. one of: {', '.join(phases.PHASES)}"
        room["phase"] = key
        room_mod.save(room)
        return room_mod.step(room)

    if action == "step":
        return room_mod.step(room)

    if action == "commit":
        card, _spark = room_mod.commit(room, str(a.get("text") or ""))
        nxt = room_mod.step(room)
        return card + "\n\n" + nxt

    if action == "poster":
        path = room_mod.poster(room)
        return room_mod.transcript(room) + f"\n\nMEDIA:{path}"

    return room_mod.transcript(room)


def _command(raw_args: str) -> str:
    raw = (raw_args or "").strip()
    verb, _, rest = raw.partition(" ")
    verb = verb.lower() or "status"

    if verb in ("phases", "help", "how"):
        return phases.palette()
    if verb in ("reset", "clear", "new"):
        room_mod.save(None)
        return "room cleared.\n\n" + room_mod.step(room_mod.create(rest.strip() or None))
    if verb in ("step", "tick", "next"):
        return room_mod.step(_room_or_new())
    if verb in ("commit", "say", "spark"):
        room = _room_or_new()
        card, _ = room_mod.commit(room, rest)
        return card + "\n\n" + room_mod.step(room)
    if verb in ("poster", "image", "show"):
        room = _room_or_new()
        path = room_mod.poster(room)
        return room_mod.transcript(room) + f"\n\nMEDIA:{path}"

    key = phases.resolve(verb)
    if key:
        room = _room_or_new()
        room["phase"] = key
        room_mod.save(room)
        return room_mod.step(room)

    return room_mod.transcript(_room_or_new())


def register(ctx) -> None:
    ctx.register_tool(
        name="room",
        toolset="room",
        description=ROOM_SCHEMA["description"],
        handler=_handler,
        schema=ROOM_SCHEMA,
    )
    ctx.register_command(
        name="room",
        handler=_command,
        description="Antemuse Room — an automated cycle of concept discovery and movement",
        args_hint="step|commit|poster|phases|walk|flip",
        argument_mode="text",
    )
    try:
        from pathlib import Path
        ctx.register_skill(
            "room",
            Path(__file__).resolve().parent / "SKILL.md",
            description="Operate the Antemuse Room: phases, ticks, sparks, and the two projections.",
        )
    except Exception:
        pass
