#!/usr/bin/env python3
"""Render the catalog stills from the shipped product surfaces.

    python3 tools/make_screenshots.py            # writes docs/screenshots/*.png
    python3 tools/make_screenshots.py --check    # exit 1 if any still is stale

The catalog shows five agent states and one separate, person-driven mode:

- ``banner.png``            1200x600, the catalog ``image:``
- ``pane-walk.png``         captured desktop-pane frame; this script verifies it
                            exists but cannot recreate the host-owned GL surface
- ``cockpit.png``           captured 1600x900 Chromium cockpit harness frame;
                            this script verifies it exists but cannot recreate canvas + DOM
- ``return-account.png``    the six-hop walk account ``/return`` prints
- ``blocked-tool.png``      a walk entered with its supported ``block`` option,
                            with the refusal taken from ``engine.policy``

Rendered stills use the live engine in a temporary data home.  ``--check`` never
rewrites a tracked image: it renders in memory and compares bytes, so a successful
check proves the committed generated assets are fresh.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
FONT = "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Regular.ttf"
GROUND = (14, 12, 11)
INK = (242, 234, 225)
DIM = (150, 142, 134)
AMBER = (242, 178, 90)

sys.path.insert(0, str(ROOT))


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, size)


def _panel(lines: list[tuple[str, tuple[int, int, int]]], size=(1280, 720),
           font_size=20, pad=48) -> Image.Image:
    im = Image.new("RGB", size, GROUND)
    d = ImageDraw.Draw(im)
    font = _font(font_size)
    y = pad
    for text, color in lines:
        d.text((pad, y), text, font=font, fill=color)
        y += int(font_size * 1.55)
    return im


def _engine_home() -> tempfile.TemporaryDirectory:
    home = tempfile.TemporaryDirectory(prefix="antemuse-shots-")
    os.environ["ANTEMUSE_STATES_HOME"] = home.name
    return home


def banner() -> Image.Image:
    im = Image.new("RGB", (1200, 600), GROUND)
    d = ImageDraw.Draw(im)
    d.text((72, 96), "antemuse", font=_font(96), fill=INK)
    d.line((76, 214, 1124, 214), fill=AMBER, width=3)
    d.text((72, 250), "five bounded states for the agent; an explore cockpit for you.", font=_font(34), fill=INK)
    d.text((72, 306), "walk · six hops · daydream · doomscroll · dream · unstuck", font=_font(28), fill=DIM)
    d.text((72, 350), "each dose ends in an account · you fly /explore yourself", font=_font(28), fill=DIM)
    d.text((72, 500), "Hermes plugin · MIT · github.com/roosiq/antemuse-plugin",
           font=_font(20), fill=DIM)
    return im


def _fill(im: Image.Image, size=(1280, 720)) -> Image.Image:
    """Crop to the lit region, then cover the frame — the scene is mostly ground."""
    rgb = im.convert("RGB")
    px = rgb.load()
    w, h = rgb.size
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if r + g + b > 90:
                xs.append(x); ys.append(y)
    if xs:
        pad = 12
        box = (max(0, min(xs) - pad), max(0, min(ys) - pad),
               min(w, max(xs) + pad), min(h, max(ys) + pad))
        rgb = rgb.crop(box)
    scale = max(size[0] / rgb.width, size[1] / rgb.height)
    rgb = rgb.resize((max(1, int(rgb.width * scale)), max(1, int(rgb.height * scale))),
                     Image.LANCZOS)
    left = (rgb.width - size[0]) // 2
    top = (rgb.height - size[1]) // 2
    return rgb.crop((left, top, left + size[0], top + size[1]))


def return_account() -> Image.Image:
    from core import engine
    engine.enter("walk")
    line = engine.status().splitlines()[0]
    account = engine.stop()
    body, *rest = account.splitlines()
    return _panel([
        (line, AMBER),
        ("", INK),
        ("$ /return", DIM),
        (body, INK),
        *[(r, DIM) for r in rest],
    ])


def blocked_tool() -> Image.Image:
    from core import engine
    engine.enter("walk", block=True)
    verdict = engine.policy("read_file") or {}
    return _panel([
        ('state(action="enter", name="walk", block=true)', DIM),
        (engine.status().splitlines()[0], AMBER),
        ("", INK),
        ("the agent calls: read_file(README.md)", INK),
        (verdict.get("message", "the call was refused"), AMBER),
    ])


def _png_bytes(im: Image.Image) -> bytes:
    import io

    data = io.BytesIO()
    im.save(data, format="PNG", optimize=True)
    return data.getvalue()


def render_all() -> dict[str, bytes]:
    with _engine_home():
        return {
            "banner.png": _png_bytes(banner()),
            "return-account.png": _png_bytes(return_account()),
            "blocked-tool.png": _png_bytes(blocked_tool()),
        }


def write_all(produced: dict[str, bytes]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in produced.items():
        (OUT / name).write_bytes(data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    produced = render_all()
    expected = {name: hashlib.sha256(data).hexdigest() for name, data in produced.items()}
    actual = {
        name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
        for name in expected
        if (OUT / name).is_file()
    }
    stale = [name for name in expected if actual.get(name) != expected[name]]
    captured = ("pane-walk.png", "cockpit.png")
    missing_captured = [name for name in captured if not (OUT / name).is_file()]
    if args.check:
        if stale or missing_captured:
            details = []
            if stale:
                details.append(f"generated stills stale: {', '.join(stale)}")
            if missing_captured:
                details.append(f"captured stills missing: {', '.join(missing_captured)}")
            print("; ".join(details), file=sys.stderr)
            return 1
        print("generated stills match live surfaces; captured pane-walk.png and cockpit.png are present")
        return 0
    write_all(produced)
    for name, data in produced.items():
        print(f"{name:22s} {len(data)/1024:7.1f} KB  {Image.open(OUT/name).size}")
    print("pane-walk.png           captured desktop pane (not regenerated here)")
    print("cockpit.png             captured Chromium cockpit harness (not regenerated here)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
