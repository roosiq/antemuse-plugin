#!/usr/bin/env python3
"""Render the four states exactly as the pane draws them, and stitch a sheet.

The pane is a picture surface: black ground, dithered ramp, one glyph cell per cell
of the grid. This produces that artefact without needing a live state or the app,
so the pictures can be judged on their own.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
import screensaver  # noqa: E402

from PIL import Image

OUT = Path("/tmp/panes")
STATES = ("walk", "daydream", "doomscroll", "dream")
W, H = 700, 746


def page(text: str, cols: int, rows: int) -> str:
    return f"""<!doctype html><meta charset=utf-8>
<style>
 html,body{{margin:0;background:#000}}
 #p{{position:relative;width:{W}px;height:{H}px;overflow:hidden;
     background:radial-gradient(ellipse at 50% 38%, #0d1219 0%, #05070a 62%, #000 100%)}}
 pre{{position:absolute;inset:0;margin:0;padding:0;line-height:1;letter-spacing:0;
      white-space:pre;overflow:hidden;color:#cfd6dd;
      font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
      text-shadow:0 0 6px rgba(120,200,255,.18)}}
 #hud{{position:absolute;left:12px;bottom:10px;font:11px/1.35 ui-monospace,monospace;
       color:#9aa6b2;opacity:.5;letter-spacing:.02em}}
</style>
<div id=p><pre></pre><div id=hud></div></div>
<script>
const text = {json.dumps(text)};
const pre = document.querySelector('pre'), p = document.getElementById('p');
pre.textContent = text;
const lines = text.split('\\n'), cols = Math.max(...lines.map(l => l.length)), rows = lines.length;
const fs = Math.min(p.clientWidth / (cols * 0.6), p.clientHeight / rows);
pre.style.fontSize = fs.toFixed(2) + 'px';
document.getElementById('hud').textContent = '{W}x{H} · ' + cols + 'x' + rows + ' · ' + fs.toFixed(2) + 'px';
</script>"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    shots = []
    for state in STATES:
        rows = screensaver.scene(state, 1, 116, 74)[0]
        rows = [r.ljust(116) for r in rows]
        cols = max(len(r) for r in rows)
        html = OUT / f"{state}.html"
        html.write_text(page("\n".join(rows), cols, len(rows)))
        png = OUT / f"{state}.png"
        subprocess.run([
            "chromium-browser", "--headless=new", "--no-sandbox", "--hide-scrollbars",
            f"--window-size={W},{H}", "--virtual-time-budget=4000",
            f"--screenshot={png}", f"file://{html}",
        ], check=True, capture_output=True, timeout=120)
        ink = round(100 * sum(1 for r in rows for ch in r if ch not in " .") / (len(rows) * cols))
        print(f"{state}: {cols}x{len(rows)} {ink}% ink")
        shots.append((state, png))

    sheet = Image.new("RGB", (W * 2 + 8, H * 2 + 8), (8, 8, 10))
    for i, (_state, png) in enumerate(shots):
        im = Image.open(png).convert("RGB")
        sheet.paste(im, ((i % 2) * (W + 8), (i // 2) * (H + 8)))
    sheet.save("/tmp/panes/sheet.png")
    print("sheet -> /tmp/panes/sheet.png")


if __name__ == "__main__":
    main()
