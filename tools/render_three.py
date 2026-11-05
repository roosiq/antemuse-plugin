"""Render the per-state scenes headlessly and cache the frames for the terminal.

    python3 tools/render_three.py            # all five states, 8 frames each

Requires a local static server on 127.0.0.1:40813 rooted at ~/antemuse-states:

    python3 -m http.server 8795 --bind 127.0.0.1
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path.home() / ".hermes/plugin-data/antemuse-states/three_frames"
CHROME = "chromium-browser"
FLAGS = [
    "--headless=new", "--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader", "--hide-scrollbars", "--window-size=240,140",
    "--virtual-time-budget=8000",
]
STATES = ["walk", "daydream", "dissociate", "dream", "doomscroll"]
FRAMES = 8


def shoot(scene: str, frame: int, dest: Path) -> None:
    url = f"http://127.0.0.1:40813/tools/scene.html?scene={scene}&f={frame}&n={FRAMES}"
    subprocess.run(
        [CHROME, *FLAGS, f"--screenshot={dest}", url],
        check=True, capture_output=True, timeout=120,
    )


def main(states=None, frames=FRAMES) -> None:
    states = states or STATES
    t0 = time.time()
    total = 0
    for s in states:
        d = OUT / s
        d.mkdir(parents=True, exist_ok=True)
        for f in range(frames):
            shoot(s, f, d / f"f{f:03d}.png")
            total += 1
        print(f"{s}: {frames} frames")
    took = time.time() - t0
    print(f"{total} frames in {took:.1f}s ({took/total:.2f}s each) -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
