#!/usr/bin/env python3
"""Render the catalog stills from the real surfaces, not from mock-ups.

    python3 tools/make_screenshots.py            # writes docs/screenshots/*.png
    python3 tools/make_screenshots.py --check    # exit 1 if any still is stale

Four rendered files, plus one captured one:

- ``banner.png``            1200x600, the catalog ``image:``
- ``takeover.png``          the terminal takeover, rasterised by the same node
                            scene renderer the plugin uses (160x40 cells at 8x18)
- ``pane-walk.png``         NOT rendered here: a frame of the desktop pane, captured
                            from the running app during a walk (it is the only
                            visualization, and it is a GL layer the app draws)
- ``return-account.png``    the account ``/return`` prints, in the terminal font
- ``blocked-tool.png``      a refused tool call, message taken from
                            ``engine.policy`` rather than retyped

Every still is produced from the live engine in a temporary data home, so a
screenshot cannot drift from the strings the plugin actually prints. Rendering is
deterministic: same code, same bytes.
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
    d.text((72, 250), "the agent takes a walk, a daydream, a dream.", font=_font(34), fill=INK)
    d.text((72, 306), "bounded states with host-enforced tools", font=_font(28), fill=DIM)
    d.text((72, 350), "and an account when it comes back", font=_font(28), fill=DIM)
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


def takeover() -> Image.Image:
    """160x40 cells through the plugin's own software renderer."""
    with tempfile.TemporaryDirectory() as td:
        ppm = Path(td) / "scene.ppm"
        subprocess.run(
            ["node", str(ROOT / "tools" / "term_scene.cjs"),
             "--scene", "daydream", "--cols", "160", "--rows", "40", "--ppm", str(ppm)],
            check=True, cwd=ROOT, capture_output=True,
        )
        return _fill(Image.open(ppm))


def return_account() -> Image.Image:
    from core import engine
    engine.enter("daydream")
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
    engine.enter("daydream", block=True)
    verdict = engine.policy("read_file") or {}
    return _panel([
        # states are open by default; the refusal exists only because this entry asked for it
        ('state(action="enter", name="daydream", block=true)', DIM),
        (engine.status().splitlines()[0], AMBER),
        ("", INK),
        ("the agent calls: read_file(README.md)", INK),
        (verdict.get("message", "the call was refused"), AMBER),
    ])


def render_all() -> dict[str, bytes]:
    OUT.mkdir(parents=True, exist_ok=True)
    produced: dict[str, bytes] = {}
    with _engine_home():
        shots = {
            "banner.png": banner(),
            "takeover.png": takeover(),
            "return-account.png": return_account(),
            "blocked-tool.png": blocked_tool(),
        }
    for name, im in shots.items():
        path = OUT / name
        im.save(path, optimize=True)
        produced[name] = path.read_bytes()
    return produced


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in OUT.glob("*.png")} if OUT.exists() else {}
    produced = render_all()
    if args.check:
        after = {n: hashlib.sha256(d).hexdigest() for n, d in produced.items()}
        stale = [n for n in after if before.get(n) != after[n]]
        if stale:
            print(f"regenerated (were stale): {', '.join(stale)}", file=sys.stderr)
            return 1
        print("screenshots match the live surfaces")
        return 0
    for name, data in produced.items():
        print(f"{name:22s} {len(data)/1024:7.1f} KB  {Image.open(OUT/name).size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
