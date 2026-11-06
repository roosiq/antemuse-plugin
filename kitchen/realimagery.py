"""Photographs in the terminal: two real pixels per cell, drifting, dissolving.

The scenes are rendered once by the local SD server (`tools/gen_frames.py`) and
kept as PNGs under `<data>/real/<state>/`. This module turns them into ANSI.

Each cell is `▀`: foreground is the top pixel, background the bottom pixel, so a
110x30 terminal shows a 110x60 pixel photograph. Detail that fine is invisible at
100% zoom, but it is exactly what makes a dark frame read as a *place* rather
than a colour field.

Two motions keep a still frame alive:

* a slow crop drift (the frame breathes left and right over ~20 s), and
* a Bayer dissolve between successive frames of the same state.

A state change dissolves too, and it does it from the frame that was on screen,
so the picture never cuts.
"""
from __future__ import annotations

import pathlib
from typing import List, Optional, Sequence, Tuple

from PIL import Image, ImageOps

from . import store

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

_IMAGES: dict = {}
_CELLS: dict = {}
_LAST: dict = {"key": None, "cells": None}


def root() -> pathlib.Path:
    return pathlib.Path(store.data_dir()) / "real"


def frames(state: str) -> List[pathlib.Path]:
    d = root() / state
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("*.png") if p.stat().st_size > 4096)


def available(state: str) -> bool:
    return bool(frames(state))


def counts() -> dict:
    return {s: len(frames(s)) for s in ("walk", "daydream", "dream", "doomscroll")}


def _image(path: pathlib.Path) -> Image.Image:
    key = str(path)
    im = _IMAGES.get(key)
    if im is None:
        # vignette the edges very slightly: it hides the crop seam and reads as lens
        im = Image.open(path).convert("RGB")
        # terminals crush shadow detail and contain very little light, so lift
        # the range hard and give the colour a little more push than the file has
        im = ImageOps.autocontrast(im, cutoff=1.0)
        lut = [min(255, int(255 * (v / 255) ** 0.70)) for v in range(256)]
        im = im.point(lut * 3)
        im = ImageOps.colorize(im.convert("L"), black="#0b0a09", white="#fff6e8") if False else im
        _IMAGES[key] = im
    return im


def cells_at(path: pathlib.Path, cols: int, rows: int, drift: float) -> Cells:
    """Crop, drift, downsample to cols x rows*2 pixels, return (top, bottom) cells."""
    key = (str(path), cols, rows, round(drift, 3))
    hit = _CELLS.get(key)
    if hit is not None:
        return hit

    im = _image(path)
    iw, ih = im.size
    target = (cols / max(1, rows)) * 2.0
    ratio = iw / ih
    if ratio > target:
        new_w = max(1, int(ih * target))
        left = (iw - new_w) // 2
        im = im.crop((left, 0, left + new_w, ih))
    elif ratio < target:
        new_h = max(1, int(iw / target))
        top = (ih - new_h) // 2
        im = im.crop((0, top, iw, top + new_h))

    # drift: slide the crop window inside the frame so the picture moves a little
    iw, ih = im.size
    span = int(iw * DRIFT)
    if span > 0:
        shift = int(span * drift)
        keep = iw - span
        im = im.crop((max(0, shift), 0, max(1, shift + keep), ih))

    im = im.resize((cols, rows * 2), _FILTER)
    flat = list(im.getdata())
    out: Cells = []
    for y in range(rows):
        top = y * 2 * cols
        bot = top + cols
        out.append([(flat[top + x], flat[bot + x]) for x in range(cols)])
    if len(_CELLS) > 24:
        _CELLS.clear()
    _CELLS[key] = out
    return out


def blend(a: Cells, b: Cells, t: float) -> Cells:
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

    drift = 0.5 + 0.5 * _sin(seconds / DRIFT_S * 6.28318)
    now = cells_at(paths[index], cols, rows, drift)

    if phase > HOLD_S:
        t = (phase - HOLD_S) / FADE_S
        nxt = cells_at(paths[(index + 1) % n], cols, rows, drift)
        return blend(now, nxt, t)

    prev_key = _LAST.get("state")
    prev = _LAST.get("cells")
    if prev_key and prev_key != state and prev is not None and _LAST.get("at") is not None:
        # a state change: dissolve out of whatever was on screen
        t = min(1.0, (seconds - _LAST["at"]) / FADE_S)
        if t < 1.0:
            return blend(prev, now, t)
    return now


def remember(state: str, cells: Optional[Cells], seconds: float) -> None:
    if cells is None:
        return
    if _LAST.get("state") != state:
        _LAST["state"] = state
        _LAST["cells"] = cells
        _LAST["at"] = seconds


def _sin(x: float) -> float:
    import math
    return math.sin(x)


def to_rows(pix: Cells) -> List[str]:
    rows: List[str] = []
    for row in pix:
        parts: List[str] = []
        for (tr, tg, tb), (br, bg, bb) in row:
            parts.append(f"\x1b[38;2;{tr};{tg};{tb}m\x1b[48;2;{br};{bg};{bb}m▀")
        rows.append("".join(parts) + RESET)
    return rows


def still(state: str, cols: int, rows: int) -> Optional[Image.Image]:
    """The raw pixels, for a preview or a chat snapshot."""
    paths = frames(state)
    if not paths:
        return None
    return _image(paths[0]).resize((cols, rows * 2), _FILTER)
