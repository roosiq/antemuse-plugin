"""The pane's payload, as a pure function — no FastAPI, no profile, no I/O.

Kept separate from ``plugin_api.py`` so the shape can be tested without the web
server (and so the test suite keeps its dependency list). The rule this file
exists to enforce: the pane gets counts, names and glyph lines, never the
state's ``directive``, never a goal, never a candidate.

A missing field is reported as missing. Nothing here invents a state, a label or
a count, and an idle agent returns ``active: None`` rather than a default.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

FRAME_COLS = 44
FRAME_ROWS = 12

#: The envelope a surface may negotiate inside. The defaults above stay what a
#: destination that says nothing gets, so chat-facing behaviour cannot drift.
MIN_COLS, MIN_ROWS = 24, 8
MAX_COLS, MAX_ROWS = 200, 80


def grid(cols: Any = None, rows: Any = None) -> "tuple[int, int]":
    """Clamp a requested grid. Returns what will actually be drawn.

    A pane knows its own pixel box; the server owns the envelope. Neither guesses
    the other's business, and an out-of-range request is clamped rather than
    refused, because a surface that misreports its size should still get a frame.
    """
    def one(value: Any, low: int, high: int, fallback: int) -> int:
        try:
            n = int(value)
        except (TypeError, ValueError):
            return fallback
        return max(low, min(high, n))

    return (one(cols, MIN_COLS, MAX_COLS, FRAME_COLS),
            one(rows, MIN_ROWS, MAX_ROWS, FRAME_ROWS))

#: Keys that must never appear in a payload, whatever the state holds.
FORBIDDEN = ("directive", "goal", "candidates", "candidate", "journal", "prompt", "text")


def tools_of(spec_tools: Optional[List[str]], block: bool = False,
             allow: Optional[List[str]] = None) -> Dict[str, Any]:
    """A state's tool policy as facts instead of a nullable list.

    ``free`` is the default now: the state is an aside, not a lock, so nothing is
    taken away unless the entry asked for it. Only a blocking entry reports
    ``all``/``some``/``none``.
    """
    if not block:
        return {"mode": "free", "allowed": [], "blocked": []}
    if allow:
        return {"mode": "some", "allowed": sorted(str(t) for t in allow), "blocked": []}
    if spec_tools is None:
        return {"mode": "all", "allowed": [], "blocked": []}
    if not spec_tools:
        return {"mode": "none", "allowed": [], "blocked": []}
    return {"mode": "some", "allowed": sorted(str(t) for t in spec_tools), "blocked": []}


def _kind(entry: Any) -> str:
    """A residue entry's kind, tolerating the legacy bare-string form."""
    if isinstance(entry, dict):
        return str(entry.get("kind") or "legacy")
    return "legacy"


def _dose_left(active) -> int:
    """Remaining dose in the unit the state counts in (see core.engine._dose_left)."""
    dose = int(active.get("dose") or active.get("turns_left") or 0)
    unit = str(active.get("unit") or "turn(s)")
    served = int(active.get("served") or 0) if unit != "turn(s)" else int(active.get("turns") or 0)
    return max(0, dose - served)


def project(
    watch: Dict[str, Any],
    frame: Optional[List[str]] = None,
    *,
    now: Optional[float] = None,
    cols: Any = None,
    rows: Any = None,
) -> Dict[str, Any]:
    """Turn the engine's own projection into the pane's payload."""
    residue = watch.get("residue") or []
    payload: Dict[str, Any] = {
        "generated_at": float(now if now is not None else time.time()),
        "active": None,
        "frame": dict(zip(("cols", "rows"), grid(cols, rows)), lines=list(frame or [])),
        "residue": {
            "count": len(residue),
            "kinds": sorted({_kind(entry) for entry in residue}),
        },
    }
    active = watch.get("active")
    if not active:
        return payload
    payload["active"] = {
        "key": str(active.get("key") or ""),
        "label": str(active.get("label") or ""),
        "walk": active.get("walk"),
        "contract": str(active.get("contract") or ""),
        "ends_at": active.get("ends_at"),
        "seconds_left": int(active.get("seconds_left") or 0),
        "total_seconds": int(active.get("total_seconds") or 0),
        "turns_left": int(active.get("turns_left") or 0),
        # the dose in the state's own unit, so a pane can say "2 pairs" instead of "2 turns"
        # the state's own count, never spec["turns"]: an unstuck owes one direction, not three
        "dose": int(active.get("dose") or active.get("turns_left") or 0),
        "unit": str(active.get("unit") or "turn(s)"),
        "dose_left": _dose_left(active),
        "tools": tools_of(
            active.get("tools"),
            block=bool((active.get("options") or {}).get("block")),
            allow=(active.get("options") or {}).get("allow"),
        ),
    }
    return payload
