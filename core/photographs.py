"""Pictures in the terminal: two real pixels per cell, drifting, dissolving.

The scenes are rendered offline by the local SD server (`tools/gen_frames.py`)
and kept as PNGs under `<data>/real/<state>/`. The same cell model serves the
snapshot frames under `<data>/three_frames/` and any other picture the takeover
draws, so there is exactly one way a photograph becomes characters.

A cell is `▀`: foreground is the top pixel, background the bottom pixel, so a
110x30 terminal shows a 110x60 pixel image. Detail that fine is invisible at
100% zoom, but it is exactly what makes a dark frame read as a *place* rather
than a colour field.

Two motions keep a still frame alive:

* a slow crop drift (the frame breathes left and right over ~26 s), and
* a Bayer dissolve between successive frames of the same state.

A state change dissolves too, and it does it from the frame that was on screen,
so the picture never cuts.
"""
from __future__ import annotations

import math
import pathlib
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageOps

from . import storage

Pixel = Tuple[int, int, int]
Cell = Tuple[Pixel, Pixel]          # (top, bottom)
Cells = List[List[Cell]]

RESET = "\x1b[0m"
_FILTER = getattr(Image, "Resampling", Image).LANCZOS

BAYER8 = [
    [0, 32, 8, 40, 2, 34, 10, 42],
    [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38],
    [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41],
    [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37],
    [63, 31, 55, 23, 61, 29, 53, 21],
]

HOLD_S = 11.0          # how long one photograph stays up
FADE_S = 2.4           # dissolve into the next one
DRIFT_S = 26.0         # one full left-right breath
DRIFT = 0.06           # fraction of width the crop can travel

_IMAGES: Dict[str, Image.Image] = {}
_CELLS: Dict[Tuple, Cells] = {}
_LAST: Dict[str, object] = {"state": None, "cells": None, "at": None}


# ------------------------------------------------------------------ pixels

def load(path: pathlib.Path | str) -> Image.Image:
    """Open and lift a PNG; terminals crush shadow detail and carry little light."""
    key = str(path)
    im = _IMAGES.get(key)
    if im is None:
        im = Image.open(path).convert("RGB")
        im = ImageOps.autocontrast(im, cutoff=1.0)
        lut = [min(255, int(255 * (v / 255) ** 0.70)) for v in range(256)]
        im = im.point(lut * 3)
        _IMAGES[key] = im
    return im


def _crop(im: Image.Image, cols: int, rows: int, drift: float = 0.0) -> Image.Image:
    """Crop to the cell aspect (a cell is twice as tall as wide), then drift."""
    target = (cols / max(1, rows)) * 2.0
    iw, ih = im.size
    ratio = iw / ih
    if ratio > target:
        new_w = max(1, int(ih * target))
        left = (iw - new_w) // 2
        im = im.crop((left, 0, left + new_w, ih))
    elif ratio < target:
        new_h = max(1, int(iw / target))
        top = (ih - new_h) // 2
        im = im.crop((0, top, iw, top + new_h))

    iw, ih = im.size
    span = int(iw * DRIFT)
    if span > 0:
        shift = int(span * max(0.0, min(1.0, drift)))
        keep = iw - span
        im = im.crop((max(0, shift), 0, max(1, shift + keep), ih))
    return im


def _px(raw: bytes, i: int) -> Pixel:
    return (raw[i], raw[i + 1], raw[i + 2])


def cells(path: pathlib.Path | str, cols: int, rows: int, drift: float = 0.0) -> Cells:
    """Downsample one image to `cols` x `rows*2` pixels, as (top, bottom) cells."""
    key = (str(path), cols, rows, round(drift, 3))
    hit = _CELLS.get(key)
    if hit is not None:
        return hit

    im = _crop(load(path), cols, rows, drift).resize((cols, rows * 2), _FILTER)
    raw = im.tobytes()              # RGB, `rows*2` lines of `cols*3` bytes
    stride = cols * 3
    out: Cells = []
    for y in range(rows):
        top = y * 2 * stride
        bottom = top + stride
        out.append([(_px(raw, top + x * 3), _px(raw, bottom + x * 3))
                    for x in range(cols)])
    if len(_CELLS) > 24:
        _CELLS.clear()
    _CELLS[key] = out
    return out


def solid(colour: Pixel, cols: int, rows: int) -> Cells:
    """A flat field, for the empty screen before any picture exists."""
    return [[(colour, colour) for _ in range(cols)] for _ in range(rows)]


def blend(a: Cells, b: Cells, t: float) -> Cells:
    """Ordered dissolve from a to b; t=0 is all a, t=1 is all b."""
    if t <= 0:
        return a
    if t >= 1:
        return b
    out: Cells = []
    for y, brow in enumerate(b):
        arow = a[y] if y < len(a) else []
        row = []
        for x, cell in enumerate(brow):
            before = arow[x] if x < len(arow) else cell
            row.append(cell if BAYER8[y % 8][x % 8] / 64.0 < t else before)
        out.append(row)
    return out


def to_rows(pix: Cells, overlay: Sequence[str] | None = None,
            overlay_color: str = "\x1b[38;5;215m") -> List[str]:
    """Cells to ANSI rows. `overlay` is a grid of characters drawn on top."""
    rows: List[str] = []
    for y, row in enumerate(pix):
        parts: List[str] = []
        line = overlay[y] if overlay is not None and y < len(overlay) else ""
        for x, cell in enumerate(row):
            ch = line[x] if x < len(line) and line[x] != " " else ""
            if ch:
                parts.append(f"{overlay_color}{ch}")
                continue
            (tr, tg, tb), (br, bg, bb) = cell
            parts.append(f"\x1b[38;2;{tr};{tg};{tb}m\x1b[48;2;{br};{bg};{bb}m▀")
        rows.append("".join(parts) + RESET)
    return rows


# ------------------------------------------------------------------ scenes

def root() -> pathlib.Path:
    return pathlib.Path(storage.data_dir()) / "real"


def frames(state: str) -> List[pathlib.Path]:
    d = root() / state
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("*.png") if p.stat().st_size > 4096)


def available(state: str) -> bool:
    return bool(frames(state))


def counts() -> Dict[str, int]:
    return {s: len(frames(s)) for s in ("walk", "daydream", "dream", "doomscroll")}


def frame(state: str, cols: int, rows: int, seconds: float) -> Optional[Cells]:
    """The picture for `state` at `seconds`, dissolving on its own schedule."""
    paths = frames(state)
    if not paths:
        return None
    period = HOLD_S + FADE_S
    n = len(paths)
    slot = seconds / period
    index = int(slot) % n
    phase = (slot - int(slot)) * period

    drift = 0.5 + 0.5 * math.sin(seconds / DRIFT_S * 6.28318)
    now = cells(paths[index], cols, rows, drift)

    if phase > HOLD_S:
        t = (phase - HOLD_S) / FADE_S
        nxt = cells(paths[(index + 1) % n], cols, rows, drift)
        return blend(now, nxt, t)

    prev_key = _LAST.get("state")
    prev = _LAST.get("cells")
    at = _LAST.get("at")
    if prev_key and prev_key != state and prev is not None and at is not None:
        # a state change: dissolve out of whatever was on screen
        t = min(1.0, (seconds - float(at)) / FADE_S)
        if t < 1.0:
            return blend(prev, now, t)  # type: ignore[arg-type]
    return now


def remember(state: str, shot: Optional[Cells], seconds: float) -> None:
    if shot is None:
        return
    if _LAST.get("state") != state:
        _LAST["state"] = state
        _LAST["cells"] = shot
        _LAST["at"] = seconds


def still(state: str, cols: int, rows: int) -> Optional[Image.Image]:
    """The raw pixels, for a preview or a chat snapshot."""
    paths = frames(state)
    if not paths:
        return None
    return _crop(load(paths[0]), cols, rows).resize((cols, rows * 2), _FILTER)
