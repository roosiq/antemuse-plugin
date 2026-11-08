"""When to step away, and which way to step.

Mood is not guessed from prose. It comes from two things a plugin can actually
see: what the work has cost (turns, tool calls, failed calls, minutes since the
last state) and what the agent says about itself when asked.

    state(action="mood", feeling="stuck")   the agent reports
    /mood tired                             the person reports for it
    /walk, /daydream, /doomscroll, /dream    the recommendation, taken

Nothing here calls a model. The score is arithmetic on counters, so the same
work always produces the same advice.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

FEELINGS = ("stuck", "tired", "sharp", "flat", "saturated")

# how much each report moves the strain, in the same units as the counters
WEIGHT = {"stuck": 1.0, "tired": 1.0, "saturated": 0.6, "flat": 0.2, "sharp": -0.6}

# what each feeling asks for, and why
SUGGEST = {
    "stuck": ("walk", "a different edge is more useful than another attempt"),
    "tired": ("daydream", "cheapest state: three minutes, memories, no tools taken"),
    "saturated": ("dream", "slow and unstructured; let the input settle"),
    "flat": ("doomscroll", "raw feed: noise to restart attention on something"),
    "sharp": ("walk", "keep the thread, change the frame for ten minutes"),
}

STALE_AFTER_MIN = 240      # a self-report older than four hours stops counting
OFFER_AFTER_MIN = 45       # do not repeat the same nudge more often than this


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
         breaks: List[float], offered_at: float = 0.0, now: Optional[float] = None) -> Dict[str, Any]:
    """Everything the decision needs, computed in one place."""
    now = now or _now()
    last_break = max(breaks) if breaks else (work.get("started_at") or now)
    minutes = max(0.0, (now - last_break) / 60.0)

    since = [m for m in mood if now - float(m.get("at") or 0) <= STALE_AFTER_MIN * 60]
    feeling = (since[-1].get("feeling") if since else None)

    strain = min(1.0, minutes / 90.0)
    strain += min(1.0, float(work.get("turns") or 0) / 30.0)
    strain += min(1.0, float(work.get("fails") or 0) / 6.0)
    strain += WEIGHT.get(feeling or "", 0.0)
    strain = max(0.0, min(3.0, strain))

    due = "carry on" if strain < 1.0 else ("break due" if strain < 2.0 else "break overdue")
    suggested, why = (SUGGEST.get(feeling or "") if feeling else
                      (("walk", "the frame, not the effort") if strain < 2.0
                       else ("daydream", "cheapest way to stop for three minutes")))
    cooling = (now - offered_at) < OFFER_AFTER_MIN * 60

    return {
        "strain": round(strain, 2), "due": due, "minutes": int(minutes),
        "turns": int(work.get("turns") or 0), "fails": int(work.get("fails") or 0),
        "tools": int(work.get("tools") or 0), "feeling": feeling,
        "suggest": suggested, "why": why, "cooling": cooling,
    }


def line(v: Dict[str, Any]) -> str:
    """One line, for the agent's context or for a person reading the terminal."""
    bits = [f"{v['minutes']}m", f"{v['turns']} turn(s)"]
    if v["fails"]:
        bits.append(f"{v['fails']} failed call(s)")
    if v["feeling"]:
        bits.append(f"feeling {v['feeling']}")
    report_only = (v["feeling"] and v["minutes"] < 5 and not v["turns"] and not v["fails"])
    tail = " (on the report alone)" if report_only else ""
    return (f"break: {v['due']}{tail} · " + " · ".join(bits) +
            f" — {v['suggest']} ({v['why']})")


def menu() -> str:
    return "  ".join(f"/{f}" for f in ("walk", "daydream", "doomscroll", "dream"))


def offer(v: Dict[str, Any]) -> str:
    """The nudge injected into a turn, once, when a break is actually due."""
    return (f"[NO STATE {v['due'].upper()} — {v['minutes']}m since the last one, "
            f"{v['turns']} turn(s), {v['fails']} failed tool call(s). "
            f"A {v['suggest']} fits: {v['why']}. Take it with /{v['suggest']}, "
            f"or pick another: /walk|daydream|doomscroll|dream|unstuck. "
            f"Ignore this if the work is nearly done.]")
