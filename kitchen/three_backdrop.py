"""Optional three.js backdrop: headless-rendered frames, replayed as terminal art.

Frames are produced offline (chromium + swiftshader -> PNG), converted to
upper-half blocks at playback size, and cached. Playback costs nothing: the
takeover just cycles pre-built strings.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image


def _fit(im, w: int, h: int):
    """Crop to the cell aspect before scaling, so scenes are not stretched."""
    target = (w / max(1, h)) * 0.5          # a cell is about twice as tall as wide
    iw, ih = im.size
    ratio = iw / ih
    if ratio > target:
        new_w = int(ih * target)
        left = (iw - new_w) // 2
        im = im.crop((left, 0, left + new_w, ih))
    elif ratio < target:
        new_h = int(iw / target)
        top = (ih - new_h) // 2
        im = im.crop((0, top, iw, top + new_h))
    return im

from . import store

CACHE: Dict[Tuple[int, int], List[List[str]]] = {}
FLOOR = 21.0


def _dir() -> Path:
    return store.data_dir() / "three_frames"


def available() -> bool:
    if not _dir().is_dir():
        return False
    if any(_dir().glob("*.png")):
        return True
    return any(d.is_dir() and any(d.glob("*.png")) for d in _dir().iterdir())


def _lum(c) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _grid(png: Path, cols: int, rows: int):
    im = Image.open(png).convert("RGB")
    w0, h0 = im.size
    im = im.crop((int(w0 * 0.20), int(h0 * 0.12), int(w0 * 0.80), int(h0 * 0.88)))
    im = _fit(im, cols, rows)
    w, h = im.size
    px = im.load()
    step_x, step_y = w / cols, h / (rows * 2)
    out = []
    for r in range(rows):
        row = []
        for c in range(cols):
            x = min(w - 1, int((c + 0.5) * step_x))
            top = px[x, min(h - 1, int((r * 2 + 0.5) * step_y))]
            bot = px[x, min(h - 1, int((r * 2 + 1.5) * step_y))]
            row.append((top, bot))
        out.append(row)
    return out


def _ansi(grid, floor: float = FLOOR) -> List[str]:
    lines: List[str] = []
    for row in grid:
        out, fg, bgc = [], None, None
        for top, bot in row:
            if _lum(top) < floor and _lum(bot) < floor:
                if fg is not None or bgc is not None:
                    out.append("\x1b[0m")
                    fg = bgc = None
                out.append(" ")
                continue
            if top != fg:
                out.append("\x1b[38;2;%d;%d;%dm" % top)
                fg = top
            if bot != bgc:
                out.append("\x1b[48;2;%d;%d;%dm" % bot)
                bgc = bot
            out.append("▀")
        out.append("\x1b[0m")
        lines.append("".join(out))
    return lines


def _pngs(scene: str = "") -> List[Path]:
    if not available():
        return []
    sub = _dir() / scene
    pngs = sorted(sub.glob("*.png")) if scene and sub.is_dir() else []
    return pngs or sorted(_dir().glob("*.png"))


def frames(cols: int = 46, rows: int = 14, scene: str = "") -> List[List[str]]:
    key = (cols, rows, scene)
    if key in CACHE:
        return CACHE[key]
    pngs = _pngs(scene)
    if not pngs:
        return []
    built = [_ansi(_grid(p, cols, rows)) for p in pngs]
    CACHE[key] = built
    return built


def count() -> int:
    if not available():
        return 0
    return len(list(_dir().glob("*.png"))) or sum(
        1 for d in _dir().iterdir() if d.is_dir() for _ in d.glob("*.png")
    )
