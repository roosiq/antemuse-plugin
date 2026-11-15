"""The one agent state, and the separate person-driven explore mode."""
from __future__ import annotations

from typing import Dict

# `walk` is the only agent state. `explore` lives below as a separate mode: it is
# person-driven, has no dose or provider, and ends only when the person uses /return.
STATES: Dict[str, Dict] = {
    "walk": {
        "label": "WALKING",
        "turns": 6,
        "dose": {"unit": "hops", "n": 6},
        "waiting": "taking a stroll · hops arrive as you walk",
        "after": (
            "the walk is over and the frame you were in is gone. Do not resume the approach "
            "you were taking. First: state the goal in one line. Then: name the approach you "
            "were stuck in and why it was the obvious one. Then: take a different first step "
            "from the one you would have taken, and work from there. The path you walked is "
            "scenery, not a hint — it is here so you can see the route you took."
        ),
        "tools": None,
        "scene": "walk",
        "feeds": False,
        "restart": True,
        "directive": (
            "You are walking while you work. Keep the task moving and answer what you were asked. "
            "The walk supplies no material: the path you walked is scenery, not a hint, and no "
            "concepts will arrive in this turn. Do not invent a hop, do not offer the walk as "
            "evidence, and do not describe it for its own sake. What the walk changes shows up "
            "later, in what you come back willing to do. "
        ),
        "contract": "work continues · the frame is elsewhere · different on return",
        "residue": "walked: distant concepts taken while the work carried on",
    },
}

EXPLORE: Dict = {
    "label": "EXPLORING",
    "turns": 0,
    "dose": {"unit": "picks", "n": 0},
    "waiting": "at the controls · the map is yours",
    "after": (
        "the explore is over. What the person picked came from their own hands, not from this "
        "plugin's search: name those concepts back, say what they seem to have in common in one "
        "line, and ask whether to work one of them now. Do not praise the session, do not describe "
        "the cockpit, and do not add concepts they did not pick."
    ),
    "tools": None,
    "scene": "walk",
    "feeds": False,
    "directive": (
        "The person is flying the concept map themselves. They steer, they shoot, they stop — "
        "nothing about what gets picked is yours to decide. Do not name concepts for them, do not "
        "offer a route through the map, and do not narrate the session back at them. If they ask "
        "something, answer it plainly; otherwise stay out of the way until they end the state. "
    ),
    "contract": "you fly · you choose · it ends when you end it",
    "residue": "explored: concepts chosen by hand",
}

ALIASES = {
    "take_a_walk": "walk",
    "take-a-walk": "walk",
    "walking": "walk",
}


def resolve(name: str) -> str | None:
    key = (name or "").strip().lower().replace(" ", "_")
    key = ALIASES.get(key, key)
    return key if key in STATES else None


def spec(key: str) -> Dict:
    """Return the agent-state spec, or the separate person-driven explore mode."""
    return EXPLORE if key == "explore" else STATES.get(key, {})


def after(key: str) -> str:
    return str(spec(key).get("after") or "the state is over. Say in one line what it did, then get back to work.")


def waiting(key: str) -> str:
    return str(spec(key).get("waiting") or f"{key} running")


def palette() -> str:
    """The agent-state list: one state and the way out."""
    walk = STATES["walk"]
    return "\n".join([
        "AGENT STATE",
        f"  /walk       {walk['dose']['n']} {walk['dose']['unit']} · all tools",
        f"             {walk['contract']}",
        "  /return     end the current state and keep the residue",
        "",
        "  a walk ends when its dose is delivered; no clock: nothing expires on time",
    ])
