"""Two projections of one room state.

  render_png(frame, path) - a poster a human or a vision model can read
  render_text(frame)      - a dense record a language model can read

Both are pure functions of Frame, so the numbers cannot drift between them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SERIF = "/usr/share/fonts/google-noto-vf/NotoSerif[wght].ttf"
SANS = "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf"

BG = (14, 12, 11)
INK = (242, 234, 225)
MUTED = (138, 128, 121)
FAINT = (54, 48, 44)
AMBER = (232, 163, 61)
TEAL = (111, 179, 168)

W, H = 1200, 1500
M = 96

DIST_RINGS = {"near": 1, "lateral": 2, "far": 3}
RING_BASE, RING_STEP = 14, 7


@dataclass
class Spark:
    n: int
    phase: str
    score: int
    distance: str
    title: str


@dataclass
class Frame:
    room: str
    arc: int
    phase: str
    seed: str
    sparks: List[Spark] = field(default_factory=list)
    keepers: List[Dict] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(s.score for s in self.sparks)

    @property
    def cap(self) -> int:
        return max(100, len(self.sparks) * 100)

    @property
    def best(self) -> Spark | None:
        return max(self.sparks, key=lambda s: s.score) if self.sparks else None


def _font(path: str, size: int, weight: str = "Regular"):
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def _text(d, xy, s, font, fill, anchor="la", spacing=0):
    if spacing:
        x, y = xy
        for ch in s:
            d.text((x, y), ch, font=font, fill=fill, anchor=anchor)
            x += d.textlength(ch, font=font) + spacing
        return x
    d.text(xy, s, font=font, fill=fill, anchor=anchor)
    return xy[0] + d.textlength(s, font=font)


def _wrap(d, s, font, width):
    lines, cur = [], ""
    for w in s.split():
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=font) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _catmull(points, samples=24):
    if len(points) < 3:
        return points
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(len(pts) - 3):
        p0, p1, p2, p3 = pts[i : i + 4]
        for s in range(samples):
            t = s / samples
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    return out


def render_png(frame: Frame, path: str) -> str:
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([-300, -100, W + 300, H * 0.85], fill=26)
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    img = Image.composite(Image.new("RGB", (W, H), (34, 28, 24)), img, glow)
    d = ImageDraw.Draw(img)

    sans_xs = _font(SANS, 19)
    sans_s = _font(SANS, 21)
    serif_xl = _font(SERIF, 168, "Bold")
    serif_l = _font(SERIF, 44)
    serif_m = _font(SERIF, 30)

    _text(d, (M, M), "ANTEMUSE", _font(SANS, 20, "SemiBold"), INK, spacing=7)
    d.text((W - M, M + 2), f"ROOM {frame.room.upper()}  ·  ARC {frame.arc}  ·  PHASE {frame.phase.upper()}",
           font=sans_xs, fill=MUTED, anchor="ra")
    d.line([M, M + 44, W - M, M + 44], fill=FAINT, width=1)

    d.text((M - 6, M + 82), str(frame.total), font=serif_xl, fill=INK, anchor="la")
    tw = d.textlength(str(frame.total), font=serif_xl)
    d.text((M + tw + 4, M + 196), f"/ {frame.cap}", font=_font(SERIF, 46), fill=MUTED, anchor="la")
    d.text((M, M + 268), f"{len(frame.sparks)} sparks  ·  arc {frame.arc}  ·  one phase per tick",
           font=sans_s, fill=MUTED, anchor="la")

    best = frame.best
    if best:
        d.text((W - M, M + 108), "BEST", font=_font(SANS, 17, "SemiBold"), fill=MUTED, anchor="ra")
        d.text((W - M, M + 132), str(best.score), font=_font(SERIF, 64), fill=AMBER, anchor="ra")
        d.text((W - M, M + 210), f"r{best.n} {best.phase}", font=sans_s, fill=MUTED, anchor="ra")

    left, right_x = M + 42, W - M - 10
    top, bottom = 640, 1080
    n = len(frame.sparks)
    xs = [left + i * (right_x - left) / (n - 1) for i in range(n)] if n > 1 else [(left + right_x) / 2]
    ys = [bottom - (s.score / 100) * (bottom - top) for s in frame.sparks]

    for v in (25, 50, 75, 100):
        y = bottom - (v / 100) * (bottom - top)
        for x in range(left, right_x, 12):
            d.line([x, y, x + 4, y], fill=FAINT, width=1)
        d.text((left - 18, y), str(v), font=_font(SANS, 18), fill=(96, 88, 82), anchor="rm")

    if n > 1:
        curve = _catmull(list(zip(xs, ys)))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).line(curve, fill=AMBER + (90,), width=13, joint="curve")
        layer = layer.filter(ImageFilter.GaussianBlur(9))
        img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
        d = ImageDraw.Draw(img)
        d.line(curve, fill=AMBER, width=4, joint="curve")

    for s, x, y in zip(frame.sparks, xs, ys):
        rings = DIST_RINGS.get(s.distance, 1)
        for k in range(rings):
            ring = RING_BASE + k * RING_STEP
            d.ellipse([x - ring, y - ring, x + ring, y + ring],
                      outline=(132, 120, 108) if k == 0 else (96, 86, 78), width=2 if k == 0 else 1)
        rad = 6 + (s.score / 100) * 5
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=INK)
        label = str(s.score)
        lf = _font(SANS, 27, "SemiBold")
        lw = d.textlength(label, font=lf)
        lx0, ly0 = x - lw / 2 - 9, y - 62
        d.rounded_rectangle([lx0, ly0, lx0 + lw + 18, ly0 + 36], radius=6, fill=BG)
        d.text((x, y - 44), label, font=lf, fill=INK, anchor="ms")
        d.text((x, y + 46), f"r{s.n}", font=_font(SANS, 19, "SemiBold"), fill=MUTED, anchor="ms")
        d.text((x, y + 72), s.phase.upper(), font=_font(SANS, 19, "SemiBold"), fill=TEAL, anchor="ms")

    d.line([M, 1160, W - M, 1160], fill=FAINT, width=1)
    _text(d, (M + 42, 1196), "SEED", _font(SANS, 17, "SemiBold"), MUTED, spacing=4)
    for i, line in enumerate(_wrap(d, frame.seed, serif_m, W - 2 * M - 200)[:2]):
        d.text((M + 42, 1228 + i * 40), line, font=serif_m, fill=(196, 186, 176), anchor="la")

    if frame.sparks:
        last = frame.sparks[-1]
        _text(d, (M + 42, 1328), "LAST SPARK", _font(SANS, 17, "SemiBold"), MUTED, spacing=4)
        for i, line in enumerate(_wrap(d, last.title, serif_l, W - 2 * M)[:2]):
            d.text((M + 42, 1360 + i * 54), line, font=serif_l, fill=INK, anchor="la")

    lx = W - M - 250
    ly = 1196
    d.text((lx, ly), "RINGS = DISTANCE", font=_font(SANS, 15, "SemiBold"), fill=(100, 92, 86), spacing=2)
    for i, (label, rings) in enumerate((("near", 1), ("lateral", 2), ("far", 3))):
        cy = ly + 34 + i * 34
        cx = lx + 14
        for k in range(rings):
            rad = 6 + k * 4
            d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad],
                      outline=(132, 120, 108) if k == 0 else (96, 86, 78), width=1)
        d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=INK)
        d.text((lx + 44, cy), label, font=_font(SANS, 17), fill=MUTED, anchor="lm")

    d.text((M, H - 62), "state phases change the seed · move phases take a spark",
           font=_font(SANS, 18), fill=(96, 88, 82))

    img.save(path, format="PNG")
    return path


def render_text(frame: Frame) -> str:
    lines = [
        f"room {frame.room} | arc {frame.arc} | phase {frame.phase} | {len(frame.sparks)} sparks | {frame.total}/{frame.cap}",
        f"seed: {frame.seed}",
    ]
    for k in frame.keepers:
        lines.append(f"arc{k['arc']} keep: {k['title']} ({k['score']})")
    for s in frame.sparks:
        lines.append(f"r{s.n} {s.phase} {s.score} {s.distance} :: {s.title}")
    if frame.sparks:
        lines.append("shape: " + " -> ".join(str(s.score) for s in frame.sparks))
    return "\n".join(lines)
