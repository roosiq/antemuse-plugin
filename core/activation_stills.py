"""The activation map as stills for the desktop app.

The pane draws images, not glyphs: a state shows the concept map with its live concepts lit.
This module owns that drawing so there is one renderer (`tools/activation_render.py` imports the
same functions), writes JPEG stills into the plugin's own data directory, and serves them to the
desktop surface through the backend route.

No text is drawn. The card is a picture.
"""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

STILL_COUNT = 3
STILL_SIZE = (960, 600)
STILL_TTL_S = 45.0          # regenerating three stills costs ~200 ms; this keeps it rare
_PEAK = {"shape": (0, 0), "n": 0}


def _embeddings() -> Dict[str, List[float]]:
    import json
    import os
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")).expanduser()
    path = base / "antemuse" / "embeddings.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text()).get("vectors", {})
    except Exception:
        return {}


def coords(labels: List[str]) -> Dict[str, tuple]:
    """Semantic coordinates — the same projection the graph export draws."""
    vectors = _embeddings()
    usable = [label for label in labels if label in vectors]
    if not usable:
        return {}
    import random
    rng = random.Random(3)
    rows = [vectors[label] for label in usable]
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
            for label, row in zip(usable, rows)}


def fit(coords_in: Dict[str, tuple], width: int, height: int, pad: int = 46) -> Dict[str, list]:
    if not coords_in:
        return {}
    xs = [c[0] for c in coords_in.values()]
    ys = [c[1] for c in coords_in.values()]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    sx = (width - 2 * pad) / ((x1 - x0) or 1.0)
    sy = (height - 2 * pad) / ((y1 - y0) or 1.0)
    scale = min(sx, sy)
    off_x = (width - 2 * pad - (x1 - x0) * scale) / 2
    off_y = (height - 2 * pad - (y1 - y0) * scale) / 2
    return {k: [pad + (v[0] - x0) * scale + off_x, pad + (v[1] - y0) * scale + off_y]
            for k, v in coords_in.items()}


def frame_image(pos: Dict[str, list], edges: List[tuple], active: Dict[str, Dict[str, Any]],
                width: int = STILL_SIZE[0], height: int = STILL_SIZE[1]):
    """One still: the map dimmed, the firing concepts lit, nothing written on it."""
    from PIL import Image, ImageDraw, ImageFilter

    img = Image.new("RGB", (width, height), (6, 6, 8))
    draw = ImageDraw.Draw(img, "RGBA")
    for a, b in edges:
        if a in pos and b in pos:
            draw.line([tuple(pos[a]), tuple(pos[b])], fill=(120, 120, 134, 34), width=1)
    for label, p in pos.items():
        if label in active:
            continue
        draw.ellipse([p[0] - 1.6, p[1] - 1.6, p[0] + 1.6, p[1] + 1.6], fill=(110, 110, 122, 110))

    glow = Image.new("RGB", (width, height), (0, 0, 0))
    gdraw = ImageDraw.Draw(glow, "RGBA")
    for label, slot in active.items():
        p = pos.get(label)
        if not p:
            continue
        w = max(0.05, float(slot.get("weight", 0.0)))
        r = 4.0 + 16.0 * w
        gdraw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r],
                      fill=(int(214 * w) + 30, int(156 * w) + 24, int(74 * w) + 10, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=7))
    img = Image.blend(img, Image.composite(glow, img, glow.convert("L")), 0.85)
    draw = ImageDraw.Draw(img, "RGBA")
    for label, slot in active.items():
        p = pos.get(label)
        if not p:
            continue
        w = max(0.05, float(slot.get("weight", 0.0)))
        r = 2.0 + 5.0 * w
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r],
                     fill=(255, int(214 * w) + 40, int(126 * w) + 30, 255))
    return img


def _edges(labels: List[str], vectors: Dict[str, List[float]]) -> List[tuple]:
    usable = [label for label in labels if label in vectors]
    out, seen = [], set()
    for label in usable:
        mine = vectors[label]
        best = sorted(((sum(x * y for x, y in zip(mine, vectors[o])), o)
                       for o in usable if o != label), reverse=True)[:2]
        for _score, other in best:
            key = tuple(sorted((label, other)))
            if key in seen:
                continue
            seen.add(key)
            out.append((label, other))
    return out


def stills(move: str = "", session: str = "", dest: Optional[Path] = None,
           count: int = STILL_COUNT, size: tuple = STILL_SIZE,
           now: Optional[float] = None) -> List[Path]:
    """Write (or reuse) the stills for one state and return their paths, newest first.

    Three stills rather than a loop: the pane cross-fades, and a state's arc is seconds long —
    three moments of it are the story. Empty when nothing is firing, so the caller can fall back
    to its baked scene instead of showing an empty field.
    """
    from . import activation, history

    dest = Path(dest) if dest else None
    if dest is None:
        try:
            from . import storage as _storage
            dest = _storage.data_dir() / "activation" / (move or "all")
        except Exception:
            return []
    dest.mkdir(parents=True, exist_ok=True)

    now = now if now is not None else time.time()
    frames = activation.sequence(session, move or None, steps=count) if session else []
    if not frames:
        moments = [now - 300, now - 150, now]
        frames = [{"at": m, "activations": activation.activations(session, move or None, now=m)}
                  for m in moments]
    labels = sorted({label for f in frames for label in f["activations"]})
    if not labels:
        return []

    vectors = _embeddings()
    pos = fit(coords(labels), *size)
    if not pos:
        return []
    edges = _edges(labels, vectors)

    stamp = int(now)
    base = dest / "base"
    base.mkdir(parents=True, exist_ok=True)
    drawn = []
    for i, frame in enumerate(frames):
        path = base / f"f{i}-{stamp}.jpg"
        frame_image(pos, edges, frame["activations"], *size).save(path, quality=86)
        drawn.append(path)

    # The look, not the information: three.js post-processes the same stills at bake time.
    posted = _postprocess(drawn)
    if len(posted) == len(drawn):
        paths = []
        for path in posted:
            final = dest / path.name
            path.replace(final)
            paths.append(final)
    else:
        paths = drawn

    # older stills are replaced, not accumulated: a live picture, not an album
    for folder, keep in ((base, drawn), (dest, paths)):
        for old in folder.glob("f*.jpg"):
            if old not in keep:
                try:
                    old.unlink()
                except OSError:
                    pass
    return paths


def _postprocess(drawn: List[Path]) -> List[Path]:
    """Run the three.js composer over these stills, or return nothing if it cannot run."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "antemuse_postprocess", Path(__file__).resolve().parents[1] / "tools" / "postprocess_activation.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.apply(drawn)
    except Exception:
        return []


def fresh(move: str = "", session: str = "", dest: Optional[Path] = None) -> List[Path]:
    """Stills no older than STILL_TTL_S, regenerating when they are stale."""
    dest = Path(dest) if dest else None
    if dest is None:
        try:
            from . import storage as _storage
            dest = _storage.data_dir() / "activation" / (move or "all")
        except Exception:
            return []
    if dest.is_dir():
        existing = sorted(dest.glob("f*.jpg"))
        if existing:
            age = time.time() - max(p.stat().st_mtime for p in existing)
            if age < STILL_TTL_S:
                return existing
    return stills(move=move, session=session, dest=dest)
