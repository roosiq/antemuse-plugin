"""Phases of concept discovery and movement.

Two kinds of phase:

  move    - produces a spark from the current seed (unpack / flip / shift / connect)
  state   - changes the seed, the player, or the room without producing anything
            (walk / daydream / dream / dissociate / doomscroll)
  converge- freezes the arc's keeper and opens a new arc

The rotation alternates move and state phases, so a room breathes: produce,
step back, produce. Automation advances one phase per tick; a state phase never
blocks on a model call.
"""
from __future__ import annotations

from typing import Dict, List

MOVES = ("unpack", "flip", "shift", "connect")

PHASES: Dict[str, Dict] = {
    "discover": {
        "kind": "move", "move": "unpack", "label": "DISCOVER",
        "asks": "Name the ingredient nobody accounted for. One dimension only.",
    },
    "flip": {
        "kind": "move", "move": "flip", "label": "FLIP",
        "asks": "Reverse exactly one default. Say what the default was.",
    },
    "shift": {
        "kind": "move", "move": "shift", "label": "SHIFT",
        "asks": "Move exactly one frame: actor, scale, time, setting, medium.",
    },
    "connect": {
        "kind": "move", "move": "connect", "label": "CONNECT",
        "asks": "Borrow one mechanism from another domain. Name the source and the transfer.",
    },
    "walk": {
        "kind": "state", "label": "WALK", "minutes": 8,
        "effect": "relief",
        "asks": "Eight minutes outside, no phone. The seed stays as it is; you come back to it.",
    },
    "daydream": {
        "kind": "state", "label": "DAYDREAM", "minutes": 10,
        "effect": "relief",
        "asks": "Ten minutes on something undemanding. No input, no screen.",
    },
    "dream": {
        "kind": "state", "label": "DREAM", "minutes": 480,
        "effect": "recombine",
        "asks": "Overnight. Two earlier sparks get recombined into the seed.",
    },
    "dissociate": {
        "kind": "state", "label": "DISSOCIATE", "minutes": 2,
        "effect": "distance",
        "asks": "Hand the seed to someone else: a stranger in 2036 inherits it.",
    },
    "doomscroll": {
        "kind": "state", "label": "DOOMSCROLL", "minutes": 20,
        "effect": "sabotage",
        "asks": "Consume instead of producing. The room will charge you for it.",
    },
    "converge": {
        "kind": "converge", "label": "CONVERGE",
        "asks": "Keep the best spark of this arc and open a new one.",
    },
}

ROTATION: List[str] = ["discover", "flip", "walk", "shift", "connect", "daydream", "dissociate", "converge"]

ALIASES = {
    "unpack": "discover",
    "take_a_walk": "walk",
    "take-a-walk": "walk",
    "nap": "dream",
    "sleep": "dream",
    "scroll": "doomscroll",
}


def resolve(name: str) -> str | None:
    key = (name or "").strip().lower().replace(" ", "_")
    key = ALIASES.get(key, key)
    return key if key in PHASES else None


def phase(key: str) -> Dict:
    return PHASES[key]


def is_move(key: str) -> bool:
    return PHASES[key]["kind"] == "move"


def next_phase(rotation: List[str], current: str) -> str:
    if current not in rotation:
        return rotation[0]
    return rotation[(rotation.index(current) + 1) % len(rotation)]


def palette() -> str:
    lines = ["PHASES"]
    for key, spec in PHASES.items():
        kind = spec["kind"]
        move = f" · move {spec['move']}" if kind == "move" else ""
        minutes = f" · {spec['minutes']} min" if spec.get("minutes") else ""
        lines.append(f"  {key:<11} {kind:<9}{move}{minutes}  {spec['asks']}")
    lines.append("")
    lines.append("rotation: " + " → ".join(ROTATION))
    return "\n".join(lines)
