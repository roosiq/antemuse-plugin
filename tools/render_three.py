"""Render a three.js scene headlessly and convert the frames to terminal art."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path("/home/ryan/.hermes/cache/scratch/three")
OUT = HERE / "frames"
CHROME = "chromium-browser"
FLAGS = [
    "--headless=new", "--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader", "--hide-scrollbars",
]


def shoot(frame: int, size=(240, 140), budget=8000) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"f{frame:03d}.png"
    subprocess.run(
        [CHROME, *FLAGS, f"--window-size={size[0]},{size[1]}",
         f"--virtual-time-budget={budget}", f"--screenshot={png}",
         f"http://127.0.0.1:8795/scene.html#{frame}"],
        check=True, capture_output=True, timeout=120,
    )
    return png


def to_cells(png: Path, cols: int = 96, rows: int = 26):
    im = Image.open(png).convert("RGB")
    w, h = im.size
    px = im.load()
    cw, ch = w / cols, (h / rows) / 2
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            top = px[min(w - 1, int((c + 0.5) * cw)), min(h - 1, int((r + 0.25) * ch * 2))]
            bot = px[min(w - 1, int((c + 0.5) * cw)), min(h - 1, int((r + 0.75) * ch * 2))]
            row.append((top, bot))
        grid.append(row)
    return grid


def _lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def to_ansi(grid, floor: float = 26.0) -> str:
    """Upper-half blocks: one cell carries two vertical pixels. Dark cells go blank."""
    lines = []
    for row in grid:
        out, cur_fg, cur_bg = [], None, None
        for top, bot in row:
            if _lum(top) < floor and _lum(bot) < floor:
                if cur_fg is not None or cur_bg is not None:
                    out.append("\x1b[0m")
                    cur_fg = cur_bg = None
                out.append(" ")
                continue
            if top != cur_fg:
                out.append("\x1b[38;2;%d;%d;%dm" % top)
                cur_fg = top
            if bot != cur_bg:
                out.append("\x1b[48;2;%d;%d;%dm" % bot)
                cur_bg = bot
            out.append("▀")
        out.append("\x1b[0m")
        lines.append("".join(out))
    return "\n".join(lines)


def main(frames: int = 12) -> None:
    t0 = time.time()
    ansi = []
    for i in range(frames):
        png = shoot(i)
        ansi.append(to_ansi(to_cells(png)))
    took = time.time() - t0
    data = {"frames": ansi, "w": 96, "h": 26, "render_seconds": round(took, 2),
            "per_frame": round(took / frames, 2)}
    path = Path("/home/ryan/.hermes/plugin-data/antemuse-states/three_frames.json")
    path.write_text(json.dumps(data))
    print(f"rendered {frames} frames in {took:.1f}s ({took/frames:.2f}s each) -> {path}")
    print(f"payload {path.stat().st_size/1024:.0f} KB")
    preview(to_cells(OUT / "f006.png"), Path("/home/ryan/.hermes/cache/scratch/three/preview.png"))
    print("preview written")


def preview(grid, path: Path, cell=(10, 20)) -> None:
    """Draw the terminal frame back out as an image, so a human can see what the CLI shows."""
    cw, ch = cell
    rows, cols = len(grid), len(grid[0])
    im = Image.new("RGB", (cols * cw, rows * ch), (14, 12, 11))
    d = ImageDraw.Draw(im)
    for r, row in enumerate(grid):
        for c, (top, bot) in enumerate(row):
            d.rectangle([c * cw, r * ch, (c + 1) * cw, r * ch + ch // 2], fill=top)
            d.rectangle([c * cw, r * ch + ch // 2, (c + 1) * cw, (r + 1) * ch], fill=bot)
    im.save(path)


if __name__ == "__main__":
    main()
