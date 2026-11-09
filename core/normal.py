"""What an ordinary session looks like — the baseline a state is measured against.

Every threshold in `core/recommend.py` was a constant somebody picked. A state is only
meaningful relative to normal, so normal is measured with the same instrument: turns,
tool calls, failures, and how long this person works between states.

Counts only. No message text is read, and nothing is written outside the plugin data dir.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import storage

FILENAME = "normal.json"
TURN_WINDOW = 200
STRETCH_WINDOW = 50

#: below this many ordinary turns nothing is claimed.
MIN_TURNS = 20
#: below this many stretches the threshold stays fixed.
MIN_STRETCHES = 5

#: the fixed fallback, and the clamp that keeps a measurement from going absurd.
FALLBACK_MINUTES = 90
FLOOR_MINUTES = 60
CAP_MINUTES = 180


def path() -> Path:
    return storage.data_dir() / FILENAME


def _load() -> Dict[str, Any]:
    try:
        data = json.loads(path().read_text())
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"turns": [], "stretches": []}


def _save(data: Dict[str, Any]) -> None:
    path().parent.mkdir(parents=True, exist_ok=True)
    tmp = path().with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(path())


def observe_turn(tools: int, fails: int) -> None:
    """One ordinary turn: recorded only when no state is active."""
    data = _load()
    turns: List[Dict[str, int]] = list(data.get("turns") or [])
    turns.append({"tools": int(tools), "fails": int(fails)})
    data["turns"] = turns[-TURN_WINDOW:]
    _save(data)


def observe_stretch(minutes: float) -> None:
    """How long this person worked before asking for a state.

    Recorded on entry, not on exit: an abandoned state should not teach the plugin that a
    two-minute stretch is normal.
    """
    if minutes <= 0:
        return
    data = _load()
    stretches = [int(m) for m in (data.get("stretches") or [])]
    stretches.append(int(minutes))
    data["stretches"] = stretches[-STRETCH_WINDOW:]
    _save(data)


def observe_completion(state: str, turns: int, seconds: float, reason: str) -> None:
    """Turns-to-dose and seconds-to-dose, per state. The measurement Ryan asked for.

    Recording is not claiming: a distribution is built here, and a comparison across
    models is a later artefact that reads it.
    """
    data = _load()
    runs = list(data.get("completions") or [])
    runs.append({"state": state, "turns": int(turns), "seconds": int(seconds),
                 "reason": reason})
    data["completions"] = runs[-200:]
    _save(data)


def completion_stats() -> Dict[str, Any]:
    """Turns-to-dose per state, for whoever wants to compare models later."""
    runs = [r for r in (_load().get("completions") or []) if isinstance(r, dict)]
    out: Dict[str, Any] = {}
    for run in runs:
        key = str(run.get("state") or "")
        out.setdefault(key, []).append(int(run.get("turns") or 0))
    return {k: {"runs": len(v), "median_turns": statistics.median(v)} for k, v in out.items()}


def stats() -> Dict[str, Any]:
    """The baseline, or an honest statement that there isn't one yet."""
    data = _load()
    turns = [t for t in (data.get("turns") or []) if isinstance(t, dict)]
    stretches = [int(m) for m in (data.get("stretches") or []) if m]
    out: Dict[str, Any] = {
        "measured": False,
        "turns": len(turns),
        "stretches": len(stretches),
    }
    if len(turns) >= MIN_TURNS:
        out["measured"] = True
        out["tools_per_turn"] = round(statistics.median([int(t.get("tools") or 0) for t in turns]), 1)
        total_tools = sum(int(t.get("tools") or 0) for t in turns) or 1
        out["fail_rate"] = round(sum(int(t.get("fails") or 0) for t in turns) / total_tools, 3)
    if len(stretches) >= MIN_STRETCHES:
        ordered = sorted(stretches)
        cut = max(0, int(len(ordered) * 0.75) - 1)
        out["stretch_p75"] = ordered[cut]
        out["stretch_median"] = int(statistics.median(ordered))
    return out


def long_stretch_threshold() -> Dict[str, Any]:
    """The minutes that count as a long stretch, and where that number came from."""
    s = stats()
    if s.get("stretch_p75"):
        raw = int(s["stretch_p75"])
        value = max(FLOOR_MINUTES, min(CAP_MINUTES, raw))
        return {"minutes": value, "source": "measured", "raw": raw, "usual": s.get("stretch_median")}
    return {"minutes": FALLBACK_MINUTES, "source": "fixed", "raw": None, "usual": None}


def clear() -> None:
    path().unlink(missing_ok=True)
