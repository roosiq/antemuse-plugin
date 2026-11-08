"""Feasibility probe: the walk scene rasterised straight to terminal pixels, no PNG bank.

Evidence for specs/changes/scene3d-renderer/spec.md. Run it and look:

    python3 tools/scene3d_probe.py

Not wired into runtime. It is the measurement, not the implementation.

Same camera and primitives as tools/scene.html's walk(), projected in Python,
z-buffered, then packed 2x4 into braille cells.
"""
from __future__ import annotations

import math

W, H = 80, 24          # cells; braille gives 160x96 addressable dots


def cam_basis(eye, target, up=(0.0, 1.0, 0.0)):
    f = [target[i] - eye[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in f))
    f = [v / n for v in f]
    r = [f[1] * up[2] - f[2] * up[1], f[2] * up[0] - f[0] * up[2], f[0] * up[1] - f[1] * up[0]]
    n = math.sqrt(sum(v * v for v in r))
    r = [v / n for v in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    return f, r, u


class Frame:
    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.w, self.h = cols * 2, rows * 4
        self.z = [1e9] * (self.w * self.h)
        self.v = [0.0] * (self.w * self.h)

    def put(self, x, y, depth, value):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = y * self.w + x
            if depth < self.z[i]:
                self.z[i] = depth
                self.v[i] = max(self.v[i], value) if depth >= self.z[i] - 1e-6 else value

    def braille(self):
        dots = ((0, 0, 1), (0, 1, 2), (0, 2, 4), (1, 0, 8), (1, 1, 16), (1, 2, 32), (0, 3, 64), (1, 3, 128))
        out = []
        for r in range(self.rows):
            line = []
            for c in range(self.cols):
                bits = 0
                for dx, dy, bit in dots:
                    v = self.v[(r * 4 + dy) * self.w + (c * 2 + dx)]
                    if v > 0.18:
                        bits |= bit
                line.append(chr(0x2800 + bits) if bits else " ")
            out.append("".join(line).rstrip())
        return out


def render(eye=(0.0, 1.5, 6.5), target=(0.0, 0.6, -8.0), fov=40.0, cols=W, rows=H):
    fr = Frame(cols, rows)
    f, right, up = cam_basis(eye, target)
    focal = (fr.w / 2) / math.tan(math.radians(fov) / 2)

    def project(p, intensity):
        d = [p[i] - eye[i] for i in range(3)]
        depth = sum(d[i] * f[i] for i in range(3))
        if depth <= 0.2:
            return
        xc = sum(d[i] * right[i] for i in range(3))
        yc = sum(d[i] * up[i] for i in range(3))
        sx = int(fr.w / 2 + focal * xc / depth)
        sy = int(fr.h / 2 - focal * yc / depth)
        fog = max(0.0, min(1.0, 1.0 - (depth - 8.0) / 26.0))
        if fog <= 0.02:
            return
        fr.put(sx, sy, depth, intensity * fog)

    # the point trail: what the card actually shows today
    for i in range(90):
        project((math.sin(i * 0.55) * 0.55, 0.0, -i * 0.55), 1.0)

    # the floor grid, the plane the walk stands on
    for k in range(-30, 31, 2):
        for t in range(0, 120):
            project((k, 0.0, -t * 0.5), 0.30)
            project((t * 0.5 - 30, 0.0, k), 0.30)

    # the torus the walk is aimed at
    for a in range(240):
        ang = a / 240 * math.tau
        project((math.cos(ang) * 3.2, 1.5 + math.sin(ang) * 3.2, -20.0), 0.9)

    # the luminous path
    for t in range(0, 140):
        z = -t * 0.25
        for x in (-1.5, 1.5):
            project((x, 0.01, z), 0.6)

    return fr.braille()


if __name__ == "__main__":
    for line in render():
        print(line)
