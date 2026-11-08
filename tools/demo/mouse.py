#!/usr/bin/env python3
"""Move the pointer the way a hand does, then optionally click.

Straight `xdotool mousemove` jumps; a demo reads better with an eased path, a
slight overshoot and a settle. Everything here is a real X pointer event, so
ffmpeg's x11grab captures it and screenkey's `-M` shows the button press.

Usage:
    python3 tools/demo/mouse.py move 900 260 --seconds 0.7
    python3 tools/demo/mouse.py click 700 380 --seconds 0.5
"""
from __future__ import annotations

import argparse
import random
import subprocess
import sys
import time

STEPS = 28


def _pos() -> tuple[int, int]:
    out = subprocess.run(["xdotool", "getmouselocation", "--shell"],
                         capture_output=True, text=True, check=True).stdout
    vals = dict(line.split("=", 1) for line in out.strip().splitlines() if "=" in line)
    return int(vals["X"]), int(vals["Y"])


def _move(x: int, y: int) -> None:
    subprocess.run(["xdotool", "mousemove", str(x), str(y)], check=True)


def glide(x: int, y: int, seconds: float = 0.7, seed: int = 3) -> None:
    rng = random.Random(seed)
    sx, sy = _pos()
    for i in range(1, STEPS + 1):
        t = i / STEPS
        # ease-in-out, then a 2 px overshoot that settles
        e = 3 * t * t - 2 * t * t * t
        nx = sx + (x - sx) * e + rng.uniform(-1.5, 1.5)
        ny = sy + (y - sy) * e + rng.uniform(-1.5, 1.5)
        if i == STEPS - 1:
            nx, ny = x + 2, y + 1
        if i == STEPS:
            nx, ny = x, y
        _move(int(nx), int(ny))
        time.sleep(seconds / STEPS)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["move", "click"])
    p.add_argument("x", type=int)
    p.add_argument("y", type=int)
    p.add_argument("--seconds", type=float, default=0.7)
    p.add_argument("--seed", type=int, default=3)
    a = p.parse_args(argv)
    glide(a.x, a.y, a.seconds, a.seed)
    if a.action == "click":
        time.sleep(0.08)
        subprocess.run(["xdotool", "click", "1"], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
