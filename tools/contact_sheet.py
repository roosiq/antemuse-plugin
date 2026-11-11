#!/usr/bin/env python3
"""Render every mesh in the pack as an ASCII thumbnail, four to a line.

Why ASCII and not a picture: the product shows ramps, so the only question that
matters is whether a form is legible after it has been reduced to eight glyphs.
A form that needs a photograph to read is the wrong form.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/meshy/pack"
TMP = Path("/tmp/contact")
RAMP = " .:-=+*#"
COLS, ROWS = 30, 12


def shoot(mesh: Path, dest: Path) -> bool:
    url = f"http://127.0.0.1:40813/tools/contact.html?mesh={mesh.relative_to(ROOT).as_posix()}&w=360&h=200"
    proc = subprocess.run([
        "chromium-browser", "--headless=new", "--no-sandbox", "--use-gl=angle",
        "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--hide-scrollbars",
        "--window-size=360,200", "--virtual-time-budget=6000", f"--screenshot={dest}", url,
    ], capture_output=True, text=True, timeout=120)
    return dest.exists() and dest.stat().st_size > 0


def thumb(png: Path) -> list[str]:
    im = Image.open(png).convert("L")
    # a glyph cell is 0.6 as wide as tall, so sample at that ratio
    im = im.resize((COLS, ROWS), Image.Resampling.LANCZOS)
    px = list(im.tobytes())
    lo, hi = min(px), max(px)
    out = []
    for r in range(ROWS):
        line = ""
        for c in range(COLS):
            v = px[r * COLS + c]
            t = 0.0 if hi == lo else (v - lo) / (hi - lo)
            line += RAMP[min(len(RAMP) - 1, int(t * len(RAMP)))]
        out.append(line)
    return out


def main() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    meshes = sorted(PACK.rglob("*.glb"))
    if len(sys.argv) > 1:
        meshes = [m for m in meshes if any(a in m.name for a in sys.argv[1:])]
    tiles = []
    for mesh in meshes:
        dest = TMP / (mesh.stem + ".png")
        if not shoot(mesh, dest):
            tiles.append((mesh.stem, ["  (render failed)"]))
            continue
        tiles.append((mesh.stem, thumb(dest)))
    width = COLS + 4
    for i in range(0, len(tiles), 4):
        row = tiles[i:i + 4]
        print("  ".join(f"{name[:width]:^{width}}" for name, _ in row))
        for r in range(ROWS):
            print("  ".join(f"{lines[r]:<{width}}" for _, lines in row))
        print()


if __name__ == "__main__":
    main()
