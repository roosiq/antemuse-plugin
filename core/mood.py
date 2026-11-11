"""When to step away, and which way to step.

Mood is not guessed from prose. It comes from two things a plugin can actually
see: what the work has cost (turns, tool calls, failed calls, turns since the last
state) and what the agent says about itself when asked.

    state(action="mood", feeling="stuck")   the agent reports
    /walk, /daydream, /doomscroll, /dream    the recommendation, taken

This module **measures; it does not recommend.** It used to sum the counters into a
"strain" score and name a state from that arithmetic, which was a timer pretending to be
a judgement: 122 minutes became "break overdue", and overdue picked daydream because the
number was large. Naming a state is `core/recommend.py`'s job, and it must be able to
point at the counter that justified it.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

FEELINGS = ("stuck", "tired", "sharp", "flat", "saturated")

STALE_AFTER_MIN = 240      # a self-report older than four hours stops counting
OFFER_AFTER_TURNS = 10     # fallback only: the live value is settings.recommend_cooling_turns


def _now() -> float:
    return time.time()


def observe_tool(ok: bool) -> None:
    """One tool call, from the post_tool_call hook."""
    # counters live in memory and are flushed by engine on each turn; a write per
    # tool call would mean a JSON rewrite for every grep.
    global _TOOLS, _FAILS
    _TOOLS += 1
    if not ok:
        _FAILS += 1


def take_counters() -> Dict[str, int]:
    """Hand the accumulated counters to the engine and reset them."""
    global _TOOLS, _FAILS
    out = {"tools": _TOOLS, "fails": _FAILS}
    _TOOLS, _FAILS = 0, 0
    return out


_TOOLS = 0
_FAILS = 0


def view(work: Dict[str, Any], mood: List[Dict[str, Any]],
         breaks: List[float], since_offer: Optional[int] = None,
         now: Optional[float] = None) -> Dict[str, Any]:
    """Everything the decision needs, computed in one place.

    There is no clock here. A stretch is counted in turns worked since the last state, and
    the cooling window is counted in turns since the last recommendation, so a slow day and a
    fast one are read the same way.
    """
    now = now or _now()

    since = [m for m in mood if now - float(m.get("at") or 0) <= STALE_AFTER_MIN * 60]
    feeling = (since[-1].get("feeling") if since else None)

    try:
        from . import settings
        cooling_turns = settings.number("recommend_cooling_turns")
    except Exception:
        cooling_turns = OFFER_AFTER_TURNS
    # Nothing offered yet in this stretch means the first one is allowed at once.
    cooling = since_offer is not None and int(since_offer) < cooling_turns

    return {
        "turns_since_offer": since_offer,
        "turns": int(work.get("turns") or 0),
        "fails": int(work.get("fails") or 0),
        "tools": int(work.get("tools") or 0),
        "streak": int(work.get("streak") or 0),
        "feeling": feeling,
        "cooling": cooling,
    }


def line(v: Dict[str, Any]) -> str:
    """The measured facts, and nothing else: no score, no suggested state."""
    bits = [f"{v['turns']} turn(s) since the last state"]
    if v["fails"]:
        bits.append(f"{v['fails']} failed call(s)")
    if v["streak"]:
        bits.append(f"{v['streak']} in a row")
    if v["feeling"]:
        bits.append(f"reported {v['feeling']}")
    return " · ".join(bits)
