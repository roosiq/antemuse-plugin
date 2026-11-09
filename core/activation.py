"""Which concepts are firing right now, and how hot.

A state serves concepts turn by turn; the ledger records every serving with its move, session
and time. This module turns that record into an activation map: each concept gets a weight that
decays with age, so the picture shows what is live *now* and what just cooled off.

Two rules carried over from the rest of the plugin:

- **Derived, never authoritative.** An activation is a view of the ledger. Nothing here writes,
  nothing here decides what a state does next, and a missing ledger is an empty map.
- **No text.** Weights are numbers. Turning them into a picture is the renderer's job, and the
  picture carries no labels — the human card is a picture.
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional

#: A concept that was served two turns ago is at half the weight of one served now. Expressed in
#: seconds of real time rather than turns, because a state's cadence is per turn but its clock
#: is not under our control.
HALF_LIFE_S = 180.0
FLOOR = 0.25


def _rows(sql: str, args=()) -> List[tuple]:
    from . import history
    try:
        return history._query(sql, args)
    except Exception:
        return []


def activations(session: str = "", move: Optional[str] = None, now: Optional[float] = None,
                half_life: float = HALF_LIFE_S, limit: int = 600) -> Dict[str, Dict[str, Any]]:
    """Concept label -> weight in 0..1, decaying with age. Empty on a missing ledger."""
    now = now if now is not None else time.time()
    # every serving counts by default — a state's own moves and the session scan are both
    # "firing"; naming a move narrows it to that state
    # the time bound belongs in the query: limiting to the newest N rows *before* filtering by
    # time made every early frame of a session empty
    sql = """SELECT c.label, s.at FROM served s JOIN concepts c ON c.id = s.concept_id
             WHERE s.session = ? AND s.at <= ?"""
    args: List[Any] = [session, now]
    if move:
        sql += " AND s.move = ?"
        args.append(move)
    sql += " ORDER BY s.at DESC LIMIT ?"
    args.append(limit)

    out: Dict[str, Dict[str, Any]] = {}
    for label, at in _rows(sql, tuple(args)):
        at = float(at)
        if at > now:
            # a serving that has not happened yet at this moment is not active — without this
            # every concept in a long session lights up in the first frame
            continue
        age = now - at
        weight = math.exp(-age / half_life * math.log(2))
        slot = out.setdefault(label, {"weight": 0.0, "count": 0, "last": at})
        # the freshest sighting wins: summing makes a word repeated all day outrank one that
        # is firing right now
        slot["weight"] = max(slot["weight"], weight)
        slot["count"] += 1
        slot["last"] = max(slot["last"], at)

    top = max((v["weight"] for v in out.values()), default=0.0) or 1.0
    for slot in out.values():
        slot["weight"] = round(min(1.0, slot["weight"] / top), 4)
    return {k: v for k, v in out.items() if v["weight"] >= FLOOR}


def sequence(session: str, move: Optional[str] = None, steps: int = 12,
             half_life: float = HALF_LIFE_S) -> List[Dict[str, Any]]:
    """Activation at real moments of one session — the material for an animation.

    Frames are taken at the timestamps servings actually happened, sampled evenly, rather than
    at evenly spaced clock times: a session is bursty, and uniform sampling spends most of its
    frames on the gaps between turns.
    """
    sql = """SELECT at FROM served WHERE session = ?"""
    args: List[Any] = [session]
    if move:
        sql += " AND move = ?"
        args.append(move)
    sql += " ORDER BY at"
    times = [float(row[0]) for row in _rows(sql, tuple(args))]
    if not times:
        return []
    moments = sorted(set(times))
    if len(moments) <= steps:
        picked = moments
    else:
        picked = [moments[int(round(i * (len(moments) - 1) / (steps - 1)))] for i in range(steps)]
    return [{"at": at, "activations": activations(session, move, now=at, half_life=half_life)}
            for at in picked]


def hot(frames: List[Dict[str, Any]], limit: int = 8) -> List[str]:
    """The concepts that were hottest anywhere in the sequence — what the story was about."""
    peak: Dict[str, float] = {}
    for frame in frames:
        for label, slot in frame["activations"].items():
            peak[label] = max(peak.get(label, 0.0), slot["weight"])
    return [label for label, _ in sorted(peak.items(), key=lambda kv: kv[1], reverse=True)[:limit]]


def summary(frames: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not frames:
        return {"frames": 0, "concepts": 0}
    seen = set()
    for frame in frames:
        seen.update(frame["activations"])
    return {"frames": len(frames), "concepts": len(seen),
            "peak_concurrent": max((len(f["activations"]) for f in frames), default=0)}


# ------------------------------------------------------------------ as glyphs

#: Brightness ramp for the picture, darkest first. Only these characters are ever drawn: the
#: state visual carries no words.
RAMP = " .:-=+*#%@"


def _positions(labels: List[str], cols: int, rows: int) -> Dict[str, tuple]:
    """Semantic coordinates for these labels, fitted to a character grid.

    Falls back to a deterministic circle when no vectors cover the labels — a shape that says
    "no projection available" without pretending to be one.
    """
    try:
        import json
        import os
        from pathlib import Path

        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")).expanduser()
        payload = json.loads((base / "antemuse" / "embeddings.json").read_text())
        vectors = payload.get("vectors", {})
        usable = [label for label in labels if label in vectors]
        if not usable:
            raise ValueError("no vectors")
        coords = _pca(vectors, usable)
    except Exception:
        if not labels:
            return {}
        coords = {label: (math.cos(2 * math.pi * i / len(labels)),
                          math.sin(2 * math.pi * i / len(labels)))
                  for i, label in enumerate(labels)}
    xs = [c[0] for c in coords.values()]
    ys = [c[1] for c in coords.values()]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    # a character cell is about twice as tall as it is wide, so the y axis is compressed
    out = {}
    for label, (x, y) in coords.items():
        cx = 0.5 if x1 == x0 else (x - x0) / (x1 - x0)
        cy = 0.5 if y1 == y0 else (y - y0) / (y1 - y0)
        out[label] = (int(round(cx * (cols - 1))), int(round((1 - cy) * (rows - 1))))
    return out


def _pca(vectors: dict, labels: List[str]) -> Dict[str, tuple]:
    """Two components, power iteration — the same projection the graph export draws."""
    import random
    rng = random.Random(3)
    rows = [vectors[label] for label in labels]
    d = len(rows[0])
    mean = [sum(r[j] for r in rows) / len(rows) for j in range(d)]
    centred = [[r[j] - mean[j] for j in range(d)] for r in rows]
    comps = []
    for _ in range(2):
        vec = [rng.uniform(-1, 1) for _ in range(d)]
        for _ in range(40):
            proj = [sum(a * b for a, b in zip(r, vec)) for r in centred]
            new = [sum(p * r[j] for p, r in zip(proj, centred)) for j in range(d)]
            norm = sum(x * x for x in new) ** 0.5 or 1.0
            vec = [x / norm for x in new]
        comps.append(vec)
        centred = [[r[j] - sum(r[k] * comps[-1][k] for k in range(d)) * comps[-1][j]
                    for j in range(d)] for r in centred]
    return {label: (sum(a * b for a, b in zip(row, comps[0])),
                    sum(a * b for a, b in zip(row, comps[1])))
            for label, row in zip(labels, rows)}


def art(cols: int = 44, rows: int = 12, session: str = "", move: Optional[str] = None,
        now: Optional[float] = None) -> List[str]:
    """The activation map as glyph rows — what the state surfaces actually show.

    Nothing here is text about the state; the characters are the picture. An empty result means
    nothing is firing, and the caller falls back to its baked scene.
    """
    live = activations(session, move, now=now) if session else {}
    if not live:
        return []
    cols = max(8, cols)
    rows = max(3, rows)
    pos = _positions(sorted(live), cols, rows)
    grid = [[" "] * cols for _ in range(rows)]
    # normalised weights cluster near 1, so a weight-to-glyph mapping draws everything the same
    # character; the glyph carries *rank* instead, which is what the eye needs from a picture
    ranked = sorted(live.items(), key=lambda kv: kv[1]["weight"], reverse=True)
    span = max(1, len(ranked) - 1)
    for i, (label, _slot) in enumerate(ranked):
        spot = pos.get(label)
        if not spot:
            continue
        x, y = spot
        level = int(round((1 - i / span) * (len(RAMP) - 2))) + 1
        grid[y][x] = RAMP[max(1, min(len(RAMP) - 1, level))]
    return ["".join(row) for row in grid]
