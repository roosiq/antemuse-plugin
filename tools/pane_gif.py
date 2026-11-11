#!/usr/bin/env python3
"""Bake the four state strips into animated GIFs, frame by frame.

The pane animates server-side (frame_index from the clock), but that is invisible
until the gateway reloads. This renders the same frames the pane would ask for and
writes them as GIFs at the per-state rate, so the motion can be judged now.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from core import surfaces  # noqa: E402

from PIL import Image

OUT = Path("/tmp/panes/gif")
STATES = ("walk", "daydream", "doomscroll", "dream")
RATE_MS = {"walk": 3000, "daydream": 2400, "doomscroll": 1100, "dream": 4000}
W, H = 420, 448
COLS, ROWS, FRAMES = 116, 74, 8

PAGE = """<!doctype html><meta charset=utf-8>
<style>
 html,body{{margin:0;background:#000}}
 #p{{position:relative;width:{w}px;height:{h}px;overflow:hidden;
     background:radial-gradient(ellipse at 50% 38%, #0d1219 0%, #05070a 62%, #000 100%)}}
 pre{{position:absolute;inset:0;margin:0;padding:0;line-height:1;letter-spacing:0;
      white-space:pre;overflow:hidden;color:#cfd6dd;
      font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
      text-shadow:0 0 6px rgba(120,200,255,.18)}}
</style>
<div id=p><pre></pre></div>
<script>
const text = {text};
const pre = document.querySelector('pre'), p = document.getElementById('p');
pre.textContent = text;
const lines = text.split('\\n'), cols = Math.max(...lines.map(l => l.length));
const fs = Math.min(p.clientWidth / (cols * 0.6), p.clientHeight / lines.length);
pre.style.fontSize = fs.toFixed(2) + 'px';
</script>"""


def render(state: str, index: int, dest: Path) -> None:
    rows = surfaces.art(COLS, ROWS, scene=state, fit="cover", pane=True,
                        dither=True, index=index)
    html = OUT / "page.html"
    html.write_text(PAGE.format(w=W, h=H, text=json.dumps("\n".join(rows))))
    subprocess.run([
        "chromium-browser", "--headless=new", "--no-sandbox", "--hide-scrollbars",
        f"--window-size={W},{H}", "--virtual-time-budget=3000",
        f"--screenshot={dest}", f"file://{html}",
    ], check=True, capture_output=True, timeout=120)
    if not dest.exists() or dest.stat().st_size < 1000:
        raise SystemExit(f"{state} frame {index}: no screenshot written")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for state in STATES:
        frames = []
        for i in range(FRAMES):
            png = OUT / f"{state}_{i}.png"
            render(state, i, png)
            frames.append(Image.open(png).convert("P", palette=Image.Palette.ADAPTIVE, colors=32))
        gif = OUT / f"{state}.gif"
        # three times life speed: the honest ordering of the rates, at a pace a
        # short loop can be judged at
        step = max(60, RATE_MS[state] // 3)
        frames[0].save(gif, save_all=True, append_images=frames[1:], loop=0,
                       duration=step, optimize=True)
        print(f"{state}: {len(frames)} frames @ {step}ms -> {gif} ({gif.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
