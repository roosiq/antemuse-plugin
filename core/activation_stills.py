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
#: Read with `struct`: the plugin's dependency set is pillow and nltk, never numpy.
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
        "edge": (120, 120, 134, 34),
        "dim": (110, 110, 122, 110),
        "halo": (214, 156, 74),
        "core": (255, 214, 126),
    },
    "nous": {
        "ground": (25, 25, 46),
        "edge": (142, 142, 200, 26),
        "dim": (126, 126, 176, 96),
        "halo": (0, 40, 242),
        "core": (242, 242, 252),
    },
}


def frame_image(pos: Dict[str, list], edges: List[tuple], active: Dict[str, Dict[str, Any]],
                width: int = STILL_SIZE[0], height: int = STILL_SIZE[1],
                palette: str = "amber"):
    """One still: the map dimmed, the firing concepts lit, nothing written on it."""
    from PIL import Image, ImageDraw, ImageFilter

    ink = PALETTES.get(palette, PALETTES["amber"])
    img = Image.new("RGB", (width, height), ink["ground"])
    draw = ImageDraw.Draw(img, "RGBA")
    for a, b in edges:
        if a in pos and b in pos:
            draw.line([tuple(pos[a]), tuple(pos[b])], fill=ink["edge"], width=1)
    for label, p in pos.items():
        if label in active:
            continue
        draw.ellipse([p[0] - 1.6, p[1] - 1.6, p[0] + 1.6, p[1] + 1.6], fill=ink["dim"])

    glow = Image.new("RGB", (width, height), (0, 0, 0))
    gdraw = ImageDraw.Draw(glow, "RGBA")
    for label, slot in active.items():
        p = pos.get(label)
        if not p:
            continue
        w = max(0.05, float(slot.get("weight", 0.0)))
        r = 4.0 + 16.0 * w
        gdraw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r],
                      fill=(int(ink["halo"][0] * w) + 30, int(ink["halo"][1] * w) + 24,
                            int(ink["halo"][2] * w) + 10, 255))
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
                     fill=(int(ink["core"][0] * w) + 13, int(ink["core"][1] * w) + 40,
                           int(ink["core"][2] * w) + 30, 255))
    return img


def stills(move: str = "", session: str = "", dest: Optional[Path] = None,
           count: int = STILL_COUNT, size: tuple = STILL_SIZE,
           now: Optional[float] = None, palette: str = "amber") -> List[Path]:
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
    # The state narrows the map when that state has servings of its own in this session. When it
    # has none — a walk entered a minute ago, a session scanned under another move — the session's
    # servings are still what is firing, and an empty field would be a lie about the picture.
    frames = activation.sequence(session, move or None, steps=count) if session else []
    if not frames and session and move:
        frames = activation.sequence(session, None, steps=count)
    if not frames:
        moments = [now - 300, now - 150, now]
        frames = [{"at": m, "activations": activation.activations(session, move or None, now=m)}
                  for m in moments]
    labels = sorted({label for f in frames for label in f["activations"]})
    if not labels:
        return []

    pos = fit(coords(labels), *size)
    if not pos:
        return []
    edges = nearest(labels)

    stamp = int(now)
    base = dest / "base"
    base.mkdir(parents=True, exist_ok=True)
    drawn = []
    for i, frame in enumerate(frames):
        path = base / f"f{i}-{stamp}.jpg"
        frame_image(pos, edges, frame["activations"], *size, palette=palette).save(path, quality=86)
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

    # Stable names as well as stamped ones: the desktop pane is a file:// page and can only ask
    # for a path it can predict, not a listing.
    stable_paths = []
    for i, path in enumerate(paths):
        try:
            stable = dest / f"f{i}.jpg"
            if path != stable:
                stable.write_bytes(path.read_bytes())
            stable_paths.append(stable)
        except OSError:
            pass

    # older stills are replaced, not accumulated: a live picture, not an album
    for folder, keep in ((base, drawn), (dest, paths + stable_paths)):
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


def fresh(move: str = "", session: str = "", dest: Optional[Path] = None,
          palette: str = "amber") -> List[Path]:
    """Stills no older than STILL_TTL_S, regenerating when they are stale."""
    dest = Path(dest) if dest else None
    if dest is None:
        try:
            from . import storage as _storage
            dest = _storage.data_dir() / "activation" / (move or "all")
        except Exception:
            return []
    if dest.is_dir():
        # The stamped stills only: f0.jpg..f2.jpg are the aliases the desktop pane asks for, and
        # returning both would serve every frame twice.
        existing = sorted(p for p in dest.glob("f*.jpg") if "-" in p.stem)
        if existing:
            age = time.time() - max(p.stat().st_mtime for p in existing)
            if age < STILL_TTL_S:
                return existing
    return stills(move=move, session=session, dest=dest, palette=palette)
