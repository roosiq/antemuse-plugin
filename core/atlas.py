"""Where a concept sits, and what the pane needs to place it.

A pure geometry module: the stored projection (`assets/projection/wordnet.proj.json`), a PCA
fallback for labels it does not carry, k-nearest neighbours in that space, and the map's ground.
It draws nothing and imports nothing outside the standard library — the picture is the pane's,
and the pane uses raw WebGL.

Reads with `struct`: this plugin's dependency set is nltk and nothing else.
"""
from __future__ import annotations

import json as _json
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_PEAK = {"shape": (0, 0), "n": 0}


def _cache_dir() -> Path:
    import os
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")).expanduser()
    return base / "antemuse"


def _embeddings() -> Dict[str, List[float]]:
    import json
    path = _cache_dir() / "embeddings.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text()).get("vectors", {})
    except Exception:
        return {}


#: Whole-WordNet *projection*, loaded once per process. The vectors themselves are never stored:
#: `tools/project_wordnet.py` embeds all 117,659 synsets offline and keeps only what a picture needs
#: — five coordinates and three neighbour indices per label, a few megabytes — plus the 384x3 basis,
#: so a concept that lives in the ledger's own embeddings file can still be placed by projecting it.
#: Read with `struct`: the plugin's dependency set is nltk, never numpy.
_PROJ: Dict[str, Any] = {"at": None, "index": None, "coords": None, "basis": None}


def _projection(labels: List[str]) -> Dict[str, tuple]:
    """Stored coordinates (x2, y2, x3, y3, z3) for whichever of these labels WordNet knows."""
    import json
    import struct
    base = _cache_dir()
    meta_path, coord_path = base / "wordnet.proj.json", base / "wordnet.proj.f16"
    if not (meta_path.exists() and coord_path.exists()):
        return {}
    try:
        stamp = coord_path.stat().st_mtime
        if _PROJ["at"] != stamp:
            meta = json.loads(meta_path.read_text())
            names = [str(x) for x in meta.get("labels") or []]
            _PROJ["index"] = {name: i for i, name in enumerate(names)}
            _PROJ["basis"] = meta.get("basis") or []
            if _PROJ["coords"] is not None:
                try:
                    _PROJ["coords"].close()
                except Exception:
                    pass
            _PROJ["coords"] = coord_path.open("rb")
            _PROJ["at"] = stamp
        index, handle = _PROJ["index"], _PROJ["coords"]
        stride = 5 * 2
        out = {}
        for label in labels:
            row = index.get(label)
            if row is None:
                continue
            handle.seek(row * stride)
            raw = handle.read(stride)
            if len(raw) != stride:
                continue
            out[label] = struct.unpack("<5e", raw)
        return out
    except Exception:
        return {}


def _project_one(vector: List[float]) -> tuple:
    """Place a vector that WordNet does not know (a project name, a tool) in the same space."""
    basis = _PROJ.get("basis") or []
    if not basis or not vector:
        return ()
    try:
        return tuple(sum(float(v) * float(b[i]) for v, b in zip(vector, basis)) for i in range(3))
    except Exception:
        return ()


def positions(labels: List[str]) -> Dict[str, tuple]:
    """Every label's 3D position: WordNet's stored projection, or a projected ledger vector."""
    stored = _projection(labels)
    out = {}
    missing = []
    for label in labels:
        got = stored.get(label)
        if got:
            out[label] = (got[2], got[3], got[4])
        else:
            missing.append(label)
    if missing:
        have = _embeddings()
        for label in missing:
            if label in have:
                placed = _project_one(have[label])
                if placed:
                    out[label] = placed
    return out


def nearest(labels: List[str], k: int = 2) -> List[tuple]:
    """Edges between concepts that are close in the stored projection.

    Only the projection is stored, never the vectors, so adjacency is decided in the same space the
    picture draws: two concepts are joined when they are near each other in 3D, which is what a
    viewer reads off the panel. Computed per frame from the active set, so an edge always means
    "these two are near here", not "these two were near some other time".
    """
    pos = positions(labels)
    usable = sorted(pos)
    if len(usable) < 2:
        return []
    out, seen = [], set()
    for label in usable:
        a = pos[label]
        ranked = sorted(((sum((x - y) ** 2 for x, y in zip(a, pos[o])), o) for o in usable if o != label))
        for _d, other in ranked[:k]:
            key = tuple(sorted((label, other)))
            if key in seen:
                continue
            seen.add(key)
            out.append((label, other))
    return out


def _local_pca(vectors: Dict[str, List[float]], labels: List[str]) -> Dict[str, tuple]:
    """The old per-frame projection, kept for the case the stored projection cannot cover.

    A ledger-only concept set (a test fixture, a cache with no WordNet artifact) still gets a
    picture: principal directions of this frame's own vectors, seeded, so it is reproducible.
    """
    usable = [label for label in labels if label in vectors]
    if len(usable) < 2:
        return {}
    import random
    rows = [vectors[label] for label in usable]
    d = len(rows[0])
    rng = random.Random(3)
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


def _all_labels(limit: int = 2400) -> List[str]:
    """The ground the picture is drawn on: the concepts this agent has actually touched.

    A few firing concepts drawn alone are two dots in the dark and read as nothing happening —
    which is how the pane looked. The whole WordNet projection is 117,659 labels and would be an
    even mush at pane size, so the ground is the ledger's own concept space: the things this agent
    has been served, which is also the only ground the picture is honest about. Concepts the
    projection cannot place simply do not appear.
    """
    try:
        from . import activation
        rows = activation._rows(
            "SELECT c.label, COUNT(*) AS n FROM served s JOIN concepts c ON c.id = s.concept_id "
            "GROUP BY c.label ORDER BY n DESC LIMIT ?", (limit,))
        labels = [row[0] for row in rows or [] if row and row[0]]
        if len(labels) >= max(200, limit // 2):
            return sorted(labels)
        # A young ledger is a handful of concepts, and a walk over three dots is not a space. Fill
        # the rest of the ground from the same projection the picture already draws, keeping every
        # concept the ledger does have.
        try:
            data = _json.loads((_cache_dir() / "wordnet.proj.json").read_text())
            sample = data.get("labels") if isinstance(data, dict) else None
        except Exception:
            sample = None
        if sample:
            have = set(labels)
            step = max(1, len(sample) // 1200)
            for label in sample[::step]:
                if len(labels) >= limit:
                    break
                if label not in have:
                    labels.append(label)
        if labels:
            return sorted(labels)
    except Exception:
        pass
    # No ledger yet: a sparse sample of the projection, so a first run still has structure.
    try:
        data = _json.loads((_cache_dir() / "wordnet.proj.json").read_text())
        labels = data.get("labels") if isinstance(data, dict) else None
        if labels:
            step = max(1, len(labels) // 1200)
            return sorted(labels[::step][:limit])
    except Exception:
        return []
    return []


def coords(labels: List[str]) -> Dict[str, tuple]:
    """Semantic coordinates in 2D — the stored x2, y2 of each label."""
    stored = _projection(labels)
    out = {label: (v[0], v[1]) for label, v in stored.items()}
    missing = [label for label in labels if label not in out]
    if missing:
        have = _embeddings()
        for label in missing:
            if label in have:
                placed = _project_one(have[label])
                if placed:
                    out[label] = (placed[0], placed[1])
    if len(out) < 2:
        out.update(_local_pca(_embeddings(), labels))
    return out


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


# A palette is a mood, not information: same geometry, different ink. "amber" is the warm
# night-light the stills were tuned on; "nous" is the house palette — deep navy ground, an
# electric blue halo, off-white cores — measured off nousresearch.com (#19192e ground,
# #0000f2 accent, #f2f2f2 text) rather than guessed.
PALETTES = {
    "amber": {
        "ground": (6, 6, 8),
        # measured at 960x600 in a 700px pane: the first values were invisible once the composer
        # added its vignette, so the marks are brighter and the vignette is gentler.
        "edge": (150, 150, 168, 78),
        "dim": (196, 196, 208, 165),
        "halo": (214, 156, 74),
        "core": (255, 214, 126),
    },
    "nous": {
        "ground": (25, 25, 46),
        "edge": (176, 176, 232, 66),
        "dim": (208, 208, 244, 150),
        "halo": (0, 40, 242),
        "core": (242, 242, 252),
    },
}
