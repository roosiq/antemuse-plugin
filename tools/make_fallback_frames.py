#!/usr/bin/env python3
"""Make the small fallback frame bank committed with the plugin.

A fresh install has no `<data>/three_frames/`, so `surfaces.card` used to return a
blank rectangle until someone ran the bake. These four PNGs are one frame per state,
downscaled to 400x105 (the card never samples more than 56x12 cells), so a new
install shows a picture immediately. They are a fallback only: a real bake in the
plugin data dir always wins.

    python3 tools/make_fallback_frames.py [--source ~/.hermes/plugin-data/antemuse/three_frames]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "frames"
STATES = ("walk", "daydream", "doomscroll", "dream")
SIZE = (400, 105)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(Path.home() / ".hermes/plugin-data/antemuse/three_frames"))
    args = ap.parse_args()
    src = Path(args.source)
    OUT.mkdir(parents=True, exist_ok=True)
    for state in STATES:
        frames = sorted((src / state).glob("*.png"))
        if not frames:
            print(f"missing source frames for {state}", file=__import__("sys").stderr)
            return 1
        im = Image.open(frames[0]).convert("RGB").resize(SIZE, Image.LANCZOS)
        path = OUT / f"{state}.png"
        im.save(path, optimize=True)
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size/1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
