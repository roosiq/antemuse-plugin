#!/usr/bin/env python3
"""Render the demo's caption and title cards, and print the ffmpeg overlay chain.

Deterministic: same beats.json in, same PNGs out. Text lives here, not in an
ffmpeg filter string, so quoting, wrapping and the brand palette are testable.

Usage:
    python3 tools/demo/overlays.py render          # writes tools/demo/out/*.png
    python3 tools/demo/overlays.py filter          # prints the -filter_complex chain
    python3 tools/demo/overlays.py render filter   # both

Brand palette and voice come from docs/brand.md: ground #0e0c0b, amber #f2b25a,
teal #4fa89c; sentence case, no exclamation marks, third person about the agent.
"""
from __future__ import annotations

import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
BEATS = HERE / "beats.json"

W, H = 1280, 720
GROUND = (14, 12, 11)
AMBER = (242, 178, 90)
TEAL = (79, 168, 156)
PAPER = (247, 243, 238)
DIM = (150, 142, 133)

MONO = "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Regular.ttf"
MONO_BOLD = "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Bold.ttf"

CAPTION_SIZE = 34
CAPTION_MAX_W = 1100


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def wrap(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for w in words:
        trial = f"{line} {w}".strip()
        if draw.textlength(trial, font=f) <= max_w:
            line = trial
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def caption(text: str) -> Image.Image:
    """Lower-third band: amber rule, warm ground, one or two lines."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(MONO, CAPTION_SIZE)
    lines = wrap(d, text, f, CAPTION_MAX_W)
    lh = int(CAPTION_SIZE * 1.35)
    band_h = lh * len(lines) + 44
    top = H - band_h - 36
    d.rectangle([0, top, W, top + band_h], fill=(*GROUND, 232))
    d.rectangle([0, top, W, top + 3], fill=(*AMBER, 255))
    y = top + 22
    for line in lines:
        d.text((64, y), line, font=f, fill=(*PAPER, 255))
        y += lh
    return img


def title(kicker: str, head: str, sub: str) -> Image.Image:
    img = Image.new("RGBA", (W, H), (*GROUND, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 10, H], fill=(*AMBER, 255))
    d.text((96, 150), kicker.upper(), font=font(MONO, 24), fill=(*TEAL, 255))
    d.text((96, 208), head, font=font(MONO_BOLD, 72), fill=(*PAPER, 255))
    d.line([96, 320, 96 + 260, 320], fill=(*AMBER, 255), width=3)
    y = 360
    for line in wrap(d, sub, font(MONO, 30), 980):
        d.text((96, y), line, font=font(MONO, 30), fill=(*DIM, 255))
        y += 44
    return img


def render() -> list[dict]:
    OUT.mkdir(parents=True, exist_ok=True)
    beats = json.loads(BEATS.read_text())
    written = []
    for i, b in enumerate(beats):
        kind = b.get("kind", "caption")
        if kind == "caption":
            im = caption(b["text"])
        else:
            im = title(b["kicker"], b["head"], b["sub"])
        path = OUT / f"beat_{i:02d}.png"
        im.save(path)
        written.append({**b, "index": i, "path": str(path)})
    return written


def chain(items: list[dict]) -> tuple[str, str]:
    """overlay each card over its window; captions also fade in over 0.25s."""
    parts, last = [], "0:v"
    for n, b in enumerate(items):
        start, end = b["start"], b["end"]
        out = f"v{n + 1}"
        fade = "" if b.get("kind") != "caption" else ":format=auto"
        parts.append(
            f"[{last}][{n + 1}:v]overlay=0:0:enable='between(t,{start},{end})'{fade}[{out}]"
        )
        last = out
    return ";".join(parts), last


def main(argv: list[str]) -> int:
    items = render() if "render" in argv or not argv else [
        {**b, "index": i, "path": str(OUT / f"beat_{i:02d}.png")}
        for i, b in enumerate(json.loads(BEATS.read_text()))
    ]
    if "filter" in argv or not argv:
        graph, last = chain(items)
        print(graph)
        print(f"# final label: [{last}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
