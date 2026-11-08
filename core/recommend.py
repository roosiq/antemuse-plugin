"""Name the state that fits the shape of the work — from counters, never from feelings.

The recommendation in the injected block used to be a nudge: "break due". That tells a
person to stop and gives them no name. This module reads the counters the plugin already
keeps and says *which* state the shape of the work suggests, with the evidence attached:

    this looks like a walk · same tool failed 3× in a row · /walk 5

Rules that are not negotiable (see `specs/changes/pattern-recommendation`):

- **Recommend, never enter.** The line is text. Entering is the person's decision.
- **Measured, never inferred.** Every trigger is a counter: turns, tool failures,
  provider failures, the times states were entered. No sentiment, no model call.
- **Silence is the default.** No pattern matched, no line.
- **One state, one piece of evidence.** A menu is not a recommendation.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

#: "same tool failed N times in a row" — the loop.
LOOP_FAILS = 3
#: a long stretch without a state, with a failure close behind it.
GRIND_TURNS = 20
GRIND_WINDOW = 3
#: one thread, a long time.
SATURATION_TURNS = 60
#: provider failures inside the recent window.
WALL_FAILS = 2
WALL_WINDOW = 4
#: the same state twice inside this many seconds is a rut.
RUT_SECONDS = 600

#: what each pattern recommends, and why that state and not another.
WHY = {
    "rut": "the same move on the same pattern is the definition of stuck",
    "loop": "the thread matters and the frame does not",
    "wall": "a feed breaks attention off a blocked dependency",
    "saturation": "slow and unstructured: let the open decisions recombine",
    "grind": "cheapest interruption there is",
}


def _loop(work: Dict[str, Any]) -> Optional[str]:
    streak = int(work.get("streak") or 0)
    if streak >= LOOP_FAILS:
        return f"same tool failed {streak}× in a row"
    return None


def _grind(work: Dict[str, Any]) -> Optional[str]:
    turns = int(work.get("turns") or 0)
    if turns < GRIND_TURNS:
        return None
    recent = [int(t) for t in (work.get("fail_turns") or [])]
    if any(turns - t <= GRIND_WINDOW for t in recent):
        return f"{turns} turns without a state, a failure in the last {GRIND_WINDOW}"
    return None


def _saturation(work: Dict[str, Any], open_decisions: int) -> Optional[str]:
    turns = int(work.get("turns") or 0)
    if turns >= SATURATION_TURNS:
        return f"{turns} turns in one thread"
    if open_decisions >= 3:
        return f"{open_decisions} decisions left open"
    return None


def _wall(work: Dict[str, Any]) -> Optional[str]:
    turns = int(work.get("turns") or 0)
    recent = [int(t) for t in (work.get("source_fail_turns") or [])]
    inside = [t for t in recent if turns - t <= WALL_WINDOW]
    if len(inside) >= WALL_FAILS:
        return f"{len(inside)} sources failed in the last {WALL_WINDOW} turns"
    return None


def _rut(entries: List[Dict[str, Any]], active: Optional[Dict[str, Any]],
         now: float) -> Optional[Dict[str, str]]:
    """Two entries of the same state inside ten minutes, or the same twice in a row."""
    current = (active or {}).get("key")
    keys = [str(e.get("key") or "") for e in entries[-2:]]
    times = [float(e.get("at") or 0) for e in entries[-2:]]
    if current and keys and keys[-1] == current:
        if len(times) >= 2 and now - times[-2] <= RUT_SECONDS:
            return {"state": _other(current, keys), "evidence": f"just chose {current} again"}
        return {"state": _other(current, keys), "evidence": f"the last state was {current} too"}
    return None


def _other(current: str, keys: List[str]) -> str:
    """Pick a different state. Which one is a fixed rotation, not a mood read."""
    order = ["walk", "daydream", "dream", "doomscroll"]
    if current in order:
        return order[(order.index(current) + 1) % len(order)]
    return "walk"


def suggest(data: Dict[str, Any], *, open_decisions: int = 0,
            now: Optional[float] = None) -> Optional[Dict[str, str]]:
    """The one recommendation this moment earns, or None.

    Precedence is deliberate: a rut is about the *state* and outranks anything about
    the work; a loop outranks a wall (a blocked tool is more actionable than a blocked
    URL); saturation outranks grind because the advice differs.
    """
    now = now if now is not None else time.time()
    work = data.get("work") or {}
    active = data.get("active") or None

    if active:
        # Inside a state only `rut` may speak: nagging mid-state is how a helper
        # becomes a distraction.
        rut = _rut(data.get("entries") or [], active, now)
        if rut:
            return {"pattern": "rut", "line": f"this looks like a rut · {rut['evidence']} · /{rut['state']}"}
        return None

    for pattern, state, evidence in (
        ("loop", "walk", _loop(work)),
        ("wall", "doomscroll", _wall(work)),
        ("saturation", "dream", _saturation(work, open_decisions)),
        ("grind", "daydream", _grind(work)),
    ):
        if evidence:
            return {"pattern": pattern,
                    "line": f"this looks like a {state} · {evidence} · /{state} 5"}
    return None
