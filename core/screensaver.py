"""Screensaver plates: Mystify ribbons, drawn straight into the ASCII ramp.

This is the one renderer for the ambient scenes. The pane, the CLI and the
brand proofs all call `frame()`, so there is no second implementation to drift.

The idiom is the Windows screensaver family — black field, a handful of bright
vector strands, hard reflections off the walls, four-fold symmetry, no material
and no lighting. That is a *terminal* language, not a photograph one: there is
nothing to grade, so the picture is drawn in the grid rather than sampled from a
PNG.

A point bounces in a normalised box; the strand through the bouncing points is
mirrored about the centre three times, which is exactly what Mystify did. Each
state changes the parameters, not the language.

Run:  python3 tools/screensaver.py walk 3
      python3 tools/screensaver.py walk 3 --strip     (three frames side by side)
"""
from __future__ import annotations

import pathlib
import sys

RAMP = " .:-=+*#"          # the pane's own ramp, core/surfaces.py
W, H = 64, 26              # cells; a cell is about twice as tall as it is wide


class Strand:
    """One bouncing point, plus its trail of previous positions."""

    def __init__(self, trail: int, x: float, y: float, vx: float, vy: float):
        self.trail = trail
        self.pts = [(x, y, vx, vy) for _ in range(trail)]

    def step(self, t: float, speed: float = 1.0) -> None:
        x, y, vx, vy = self.pts[0]
        x += vx * speed
        y += vy * speed
        if x < 0 or x > 1:
            vx = -vx
            x = min(max(x, 0.0), 1.0)
        if y < 0 or y > 1:
            vy = -vy
            y = min(max(y, 0.0), 1.0)
        self.pts.insert(0, (x, y, vx, vy))
        self.pts.pop()


def _line(grid, a, b, value: tuple[bool, float]) -> None:
    (x0, y0), (x1, y1) = a, b
    n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        cx, cy = int(x * (W - 1)), int(y * (H - 1))
        if 0 <= cx < W and 0 <= cy < H:
            # One cell, never two: a screensaver strand is a hairline, and a
            # two-cell stroke turns four mirrored copies into a smear.
            grid[cy][cx] = max(grid[cy][cx], value[1])


def _mirror(p, k: int):
    """The four-fold symmetry: rotate the point about the centre k times."""
    x, y = p
    for _ in range(k):
        x, y = y, 1 - x
    return x, y


def scene(state: str, frames: int = 3, w: int | None = None,
          h: int | None = None):
    """Parameters per state. Same language, different behaviour."""
    spec = {
        # trail, points, speed, symmetry, edge weight, fill weight
        "walk":      dict(trail=22, speed=0.030, sym=2, edge=1.0, fill=0.0, quantise=False),
        "daydream":  dict(trail=26, speed=0.022, sym=2, edge=1.0, fill=0.0, quantise=False),
        "dream":     dict(trail=30, speed=0.026, sym=2, edge=1.0, fill=0.12, quantise=False),
        "doomscroll":dict(trail=18, speed=0.036, sym=4, edge=1.0, fill=0.0, quantise=False),
        # The two ambient scenes. A pane must never be empty: when the agent is
        # between states it still exists, so it still moves.
        "idle":      dict(trail=30, speed=0.012, sym=2, edge=1.0, fill=0.0, quantise=False),
        "work":      dict(trail=17, speed=0.046, sym=4, edge=1.0, fill=0.0, quantise=False),
    }[state]
    global W, H
    if w and h:
        W, H = w, h
        # The parameters were tuned on a 64-column strip. On a real pane the same
        # fraction of the box is far fewer cells, so the ribbon has to be longer
        # in absolute terms to occupy the surface the way a screensaver does.
        spec = dict(spec, trail=int(spec["trail"] * max(1.0, W / 64)),
                    strands=max(2, round(W / 40)))
    rng = [0.31, 0.67, 0.42]
    # velocities are directions; `speed` is how far along them one step travels
    dirs = [(0.72, 0.69), (-0.66, -0.75), (0.58, -0.81), (-0.79, 0.61)]
    strands = [Strand(spec["trail"],
                      0.18 + 0.21 * i, 0.22 + 0.17 * i,
                      dirs[i % len(dirs)][0], dirs[i % len(dirs)][1])
               for i in range(spec.get("strands", 2))]
    # Pre-roll so the trail is already extended: a fresh strand is a dot.
    for _ in range(spec["trail"] * 3):
        for s in strands:
            s.step(0, spec["speed"])
    out = []
    for f in range(frames):
        for _ in range(1):
            for s in strands:
                s.step(f, spec["speed"])
        grid = [[0.0] * W for _ in range(H)]
        for s in strands:
            pts = [(p[0], p[1]) for p in s.pts[:spec["trail"]]]
            for k in range(spec["sym"]):
                ring = [_mirror(p, k) for p in pts]
                for i in range(len(ring) - 1):
                    _line(grid, ring[i], ring[i + 1], (True, spec["edge"]))
                if spec["fill"] > 0:
                    for i in range(len(ring) - 1):
                        mx = (ring[i][0] + ring[i + 1][0]) / 2
                        my = (ring[i][1] + ring[i + 1][1]) / 2
                        cx, cy = int(mx * (W - 1)), int(my * (H - 1))
                        if 0 <= cx < W and 0 <= cy < H:
                            grid[cy][cx] = max(grid[cy][cx], spec["fill"])
        levels = len(RAMP) - 1
        rows = []
        for r in range(H):
            line = ""
            for c in range(W):
                v = grid[r][c]
                idx = int(round(v * levels))
                if spec["quantise"] and v < 0.5:
                    idx = 1 if v > 0 else 0
                line += RAMP[min(levels, max(0, idx))]
            rows.append(line.rstrip())
        out.append(rows)
    return out


def frame(state: str, w: int, h: int, now: float | None = None) -> list[str]:
    """One frame of `state` at `w`x`h` cells, phased by the clock.

    Time enters only as a phase, so the picture advances on its own without any
    caller holding a loop — two surfaces asking a second apart see the same drift.
    """
    import time as _time
    t = _time.time() if now is None else now
    phase = int(t * 2) % 4
    rows = scene(state, phase + 1, w, h)[phase]
    return [r.ljust(w) for r in rows]


def main() -> None:
    global W, H
    size = next((a for a in sys.argv[1:] if "x" in a and a[0].isdigit()), None)
    if size:
        W, H = (int(v) for v in size.split("x"))
        sys.argv.remove(size)
    state = sys.argv[1] if len(sys.argv) > 1 else "walk"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    frames = scene(state, n)
    if "--strip" in sys.argv:
        for r in range(len(frames[0])):
            print("   ".join(f[r].ljust(W) for f in frames))
    else:
        for i, f in enumerate(frames):
            print(f"-- {state} frame {i}")
            print("\n".join(f))
            print()


def save(state: str, frames: int) -> pathlib.Path:
    """One file per state: the strip, plus each frame on its own."""
    out = pathlib.Path(__file__).resolve().parent.parent / "docs" / "brand" / "screensaver"
    out.mkdir(parents=True, exist_ok=True)
    strip = scene(state, frames)
    path = out / f"{state}-{W}x{H}.txt"
    path.write_text("\n".join("   ".join(f[r].ljust(W) for f in strip)
                              for r in range(H)), encoding="utf-8")
    return path


if __name__ == "__main__":
    if "--save" in sys.argv:
        import pathlib as _p
        for st in ("walk", "daydream", "dream", "doomscroll"):
            print(save(st, 3))
    else:
        main()
