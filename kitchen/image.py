"""Real images in the terminal: two pixels per cell, full colour, and dissolves.

A cell is `▀`: the top half is the foreground colour, the bottom half the
background. That gives a 110x30 terminal an image of 110x60 pixels in truecolor,
which is enough to see a scene rather than infer it from characters.

Everything here is pure: pixels in, rows out. The transition is an ordered
dither (Bayer 8x8), so a scene change dissolves instead of cutting.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple

from PIL import Image, ImageOps

Cell = Tuple[int, int, int]
Cells = List[List[Cell]]

RESET = "\x1b[0m"

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

_CACHE: dict = {}


def cells(png: Path, cols: int, rows: int) -> Cells:
    """Downsample one image to `cols` x `rows*2` pixels, cropped to cell aspect."""
    key = (str(png), cols, rows)
    if key in _CACHE:
        return _CACHE[key]
    im = Image.open(png).convert("RGB")
    iw, ih = im.size
    target = (cols / max(1, rows)) * 2.0          # a cell is twice as tall as wide
    ratio = iw / ih
    if ratio > target:
        new_w = max(1, int(ih * target))
        left = (iw - new_w) // 2
        im = im.crop((left, 0, left + new_w, ih))
    elif ratio < target:
        new_h = max(1, int(iw / target))
        top = (ih - new_h) // 2
        im = im.crop((0, top, iw, top + new_h))
    # terminals crush dark detail: lift the range before downsampling
    im = ImageOps.autocontrast(im, cutoff=0.5)
    im = im.point(lambda v: min(255, int(255 * (v / 255) ** 0.82)))
    im = im.resize((cols, rows * 2), Image.LANCZOS)
    px = im.load()
    out: Cells = [[px[x, y * 2] for x in range(cols)] for y in range(rows)]
    _CACHE[key] = out
    return out


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
        for x, pixel in enumerate(brow):
            before = arow[x] if x < len(arow) else pixel
            row.append(pixel if BAYER8[y % 8][x % 8] / 64.0 < t else before)
        out.append(row)
    return out


def to_rows(pix: Cells, overlay: Sequence[str] | None = None,
            overlay_color: str = "\x1b[38;5;215m") -> List[str]:
    """Cells to ANSI rows. `overlay` is a grid of characters drawn on top."""
    rows: List[str] = []
    for y, row in enumerate(pix):
        parts: List[str] = []
        last = ""
        line = overlay[y] if overlay is not None and y < len(overlay) else ""
        for x, (r, g, b) in enumerate(row):
            ch = line[x] if x < len(line) and line[x] != " " else ""
            if ch:
                parts.append(f"{overlay_color}{ch}")
                last = ""
                continue
            code = f"\x1b[38;2;{r};{g};{b}m\x1b[48;2;{r};{g};{b}m"
            parts.append(code + "▀")
            last = code
        rows.append("".join(parts) + RESET)
    return rows
