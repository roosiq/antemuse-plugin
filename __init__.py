"""Concept Kitchen plugin entry point.

Registers:
  - the ``cook`` tool (agents play here, action=start|submit|hint|pass|board|rules|status)
  - the ``/cook`` slash command (humans play here, same actions)
  - a bundled skill so an agent can learn the game without a tutorial round
"""
from __future__ import annotations

from typing import Any, Dict

try:
    from .kitchen import game
except ImportError:  # loaded as a flat module
    from kitchen import game  # type: ignore[no-redef]

__version__ = "0.1.0"

COOK_SCHEMA: Dict[str, Any] = {
    "name": "cook",
    "description": (
        "Play Concept Kitchen, a five-round creative-move game with a deterministic judge. "
        "action=start deals a seed and one move; action=submit takes 'title :: because ... :: do this first' "
        "and returns a scored card (move discipline, mechanism, actionability, novelty); hint costs 8 points; "
        "pass ends the service; board shows the human+agent leaderboard; rules prints the scoring contract. "
        "Each round's seed is your previous spark, so a generative idea scores better than a clever one."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start", "submit", "hint", "pass", "board", "rules", "status"],
                "description": "What to do in the kitchen.",
            },
            "text": {
                "type": "string",
                "description": "For action=submit: 'title :: because ... :: do this first'. All three parts are required.",
            },
            "seed": {
                "type": "string",
                "description": "Optional first seed for action=start. Omit to deal from the deck.",
            },
            "player": {
                "type": "string",
                "description": "Leaderboard name for this player. Defaults to the OS user.",
            },
            "model": {
                "type": "string",
                "description": "Optional model label shown on the board row.",
            },
        },
        "required": ["action"],
    },
}


def _handler(args: Dict[str, Any] | None = None, **kwargs: Any) -> str:
    a = args or {}
    action = str(a.get("action") or "status").lower()
    p = game.player(a.get("player"), kind="agent", model=str(a.get("model") or ""))
    if action == "start":
        return game.start(p, a.get("seed"))
    if action == "submit":
        return game.submit(p, str(a.get("text") or ""))
    if action == "hint":
        return game.hint(p)
    if action == "pass":
        return game.pass_service(p)
    if action == "board":
        return game.board(p)
    if action == "rules":
        return game.rules(p)
    return game.status(p)


def _command(raw_args: str) -> str:
    """Slash-command surface: /cook <verb> [args]."""
    raw = (raw_args or "").strip()
    verb, _, rest = raw.partition(" ")
    verb = verb.lower() or "status"
    p = game.player(None, kind="human")
    if verb in ("play", "start", "deal", "new"):
        return game.start(p, rest.strip() or None)
    if verb in ("submit", "s", "answer"):
        return game.submit(p, rest)
    if verb in ("hint", "h"):
        return game.hint(p)
    if verb in ("pass", "skip", "end"):
        return game.pass_service(p)
    if verb in ("board", "leaderboard", "scores"):
        return game.board(p)
    if verb in ("rules", "how"):
        return game.rules(p)
    if verb in ("status", "now", ""):
        return game.status(p)
    return game.status(p)


def register(ctx) -> None:
    cfg = None
    try:
        cfg = ctx.config.get("antemuse-kitchen")
    except Exception:
        cfg = None
    game.configure(cfg)

    ctx.register_tool(
        name="cook",
        toolset="kitchen",
        description=COOK_SCHEMA["description"],
        handler=_handler,
        schema=COOK_SCHEMA,
    )

    ctx.register_command(
        name="cook",
        handler=_command,
        description="Concept Kitchen — a five-round creative-move minigame for humans and agents",
        args_hint="play|submit|hint|pass|board|rules",
        argument_mode="text",
    )

    try:
        from pathlib import Path
        ctx.register_skill(
            "kitchen",
            Path(__file__).resolve().parent / "SKILL.md",
            description="Play Concept Kitchen: the five-round creative-move minigame and its scoring contract.",
        )
    except Exception:
        pass
