"""Render the per-state scenes headlessly and cache the frames for the terminal.

    python3 tools/render_three.py            # all five states, 8 frames each

Requires a local static server on 127.0.0.1:40813 rooted at ~/antemuse-plugin:

    python3 -m http.server 8795 --bind 127.0.0.1
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path.home() / ".hermes/plugin-data/antemuse/three_frames"
#: The pane is not a chat card: it is roughly square, so it gets its own bake at
#: square dimensions. Cropping a 3.8:1 frame into a portrait box would throw away
#: three quarters of the composition.
OUT_PANE = Path.home() / ".hermes/plugin-data/antemuse/three_frames_pane"
CHROME = "chromium-browser"
FLAGS = [
    "--headless=new", "--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader", "--hide-scrollbars", "--window-size=1600,420",
    "--virtual-time-budget=8000",
]
STATES = ["walk", "daydream", "dissociate", "dream", "doomscroll"]
FRAMES = 8


def shoot(scene: str, frame: int, dest: Path, size: str = "1600,420") -> None:
    url = f"http://127.0.0.1:40813/tools/scene.html?scene={scene}&f={frame}&n={FRAMES}"
    flags = [f"--window-size={size}" if f.startswith("--window-size") else f for f in FLAGS]
    subprocess.run(
        [CHROME, *flags, f"--screenshot={dest}", url],
        check=True, capture_output=True, timeout=120,
    )


def main(argv=None, frames=FRAMES) -> None:
    """``--square`` bakes the pane set; bare state names bake the chat-card set."""
    argv = list(argv or [])
    square = "--square" in argv
    states = [a for a in argv if not a.startswith("--")] or STATES
    out = OUT_PANE if square else OUT
    size = "1100,1100" if square else "1600,420"
    t0 = time.time()
    total = 0
    for s in states:
        d = out / s
        d.mkdir(parents=True, exist_ok=True)
        for f in range(frames):
            shoot(s, f, d / f"f{f:03d}.png", size=size)
            total += 1
        print(f"{s}: {frames} frames at {size}")
    took = time.time() - t0
    print(f"{total} frames in {took:.1f}s ({took/total:.2f}s each) -> {out}")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
