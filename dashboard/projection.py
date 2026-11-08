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

#: Keys that must never appear in a payload, whatever the state holds.
FORBIDDEN = ("directive", "goal", "candidates", "candidate", "journal", "prompt", "text")


def tools_of(spec_tools: Optional[List[str]]) -> Dict[str, Any]:
    """A state's tool policy as three facts instead of a nullable list.

    ``None`` means every tool is open (walk), ``[]`` means none is (daydream,
    dream), a list is an allowlist (doomscroll).
    """
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


def project(
    watch: Dict[str, Any],
    frame: Optional[List[str]] = None,
    *,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """Turn the engine's own projection into the pane's payload."""
    residue = watch.get("residue") or []
    payload: Dict[str, Any] = {
        "generated_at": float(now if now is not None else time.time()),
        "active": None,
        "frame": {"cols": FRAME_COLS, "rows": FRAME_ROWS, "lines": list(frame or [])},
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
        "tools": tools_of(active.get("tools")),
    }
    return payload
