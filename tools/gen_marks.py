"""Draw the Antemuse state marks from their construction geometry.

One silhouette, four interiors. The outline never changes; only its interior
ordering does, because a state is a bounded change to how the agent behaves, not
a place it goes.

The plates are modelled as a *part*, not as a drawing:

    plate ground  ->  a body with eight chamfer facets, each lit by one light
                  ->  a recessed panel, darker than the body
                  ->  grooves cut into the panel, each with a lit lip
                  ->  one amber aperture, the only lit thing in the frame

Numbers, so the plates are re-cut rather than traced:

    S    plate size            B    silhouette box
    C1   long chamfer, two opposite corners (B/2.8)
    C2   short chamfer, the other two (B/9)
    K    bezel inset           PHI  golden section

Run:  python3 tools/gen_marks.py            (writes the SVGs)
      python3 tools/gen_marks.py --png      (also rasterises via chromium)
"""
from __future__ import annotations

import math
import pathlib
import subprocess
import sys

S = 512
B = 384
X0 = Y0 = (S - B) / 2
C1 = B / 2.8
C2 = B / 9
K = 15.0                      # bezel width
PHI = (1 + 5 ** 0.5) / 2

# One light, high and to the left. Every facet value comes from this vector.
LX, LY = -0.50, -0.866

VOID = "#0e0c0b"              # the shipped ground: warm near-black
BEZEL = (38, 45, 49)          # base body value before lighting
BEZEL_LIT = (104, 118, 125)
BEZEL_DARK = (13, 16, 17)
PANEL_TOP = "#181410"
PANEL_BOT = "#050404"
ARC = "#6fe0c8"
AMBER = "#f2b25a"
STRUCT = "#9aa6ab"


# ------------------------------------------------------------------ geometry

def pts(x: float, y: float, s: float, c1: float, c2: float) -> list[tuple[float, float]]:
    """Eight points, clockwise: two opposite corners cut long, two cut short."""
    r, b = x + s, y + s
    return [(x + c1, y), (r - c2, y), (r, y + c2), (r, b - c1),
            (r - c1, b), (x + c2, b), (x, b - c2), (x, y + c1)]


def poly(points: list[tuple[float, float]], close: bool = True) -> str:
    d = " ".join(f"{'M' if i == 0 else 'L'}{x:.2f},{y:.2f}"
                 for i, (x, y) in enumerate(points))
    return d + (" Z" if close else "")


OUT = pts(X0, Y0, B, C1, C2)
# An inset of a polygon with 45 degree cuts pulls its chamfers in by k*(sqrt2-1).
INSET = pts(X0 + K, Y0 + K, B - 2 * K, C1 - K * 0.4142, C2 - K * 0.4142)


def _lerp(a, b, t: float) -> str:
    t = max(0.0, min(1.0, t))
    r, g, bl = (round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return f"#{r:02x}{g:02x}{bl:02x}"


def facets() -> str:
    """The eight chamfer facets, each shaded by its own normal. This is the metal."""
    out = []
    n = len(OUT)
    for i in range(n):
        a, b = OUT[i], OUT[(i + 1) % n]
        a2, b2 = INSET[i], INSET[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = dy / ln, -dx / ln          # outward normal, clockwise winding
        d = nx * LX + ny * LY
        if d >= 0:
            fill = _lerp(BEZEL, BEZEL_LIT, d ** 1.4)
        else:
            fill = _lerp(BEZEL, BEZEL_DARK, (-d) ** 1.2)
        out.append(f'<path d="{poly([a, b, b2, a2])}" fill="{fill}"/>')
    return "".join(out)


def body() -> str:
    """Body, facets, outer specular hairline, and a soft contact shadow."""
    return (
        f'<defs><linearGradient id="panel" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{PANEL_TOP}"/>'
        f'<stop offset="1" stop-color="{PANEL_BOT}"/></linearGradient>'
        f'<filter id="soft" x="-50%" y="-50%" width="200%" height="200%">'
        f'<feGaussianBlur stdDeviation="4"/></filter>'
        f'<linearGradient id="sheen" x1="0" y1="0" x2="0.55" y2="1">'
        f'<stop offset="0" stop-color="#ffffff" stop-opacity="0.20"/>'
        f'<stop offset="0.42" stop-color="#ffffff" stop-opacity="0"/>'
        f'<stop offset="0.72" stop-color="#ffffff" stop-opacity="0.05"/>'
        f'<stop offset="1" stop-color="#ffffff" stop-opacity="0.13"/>'
        f'</linearGradient>'
        f'<filter id="grain" x="0" y="0" width="100%" height="100%">'
        f'<feTurbulence type="fractalNoise" baseFrequency="0.006 0.9" numOctaves="3" '
        f'result="n"/><feColorMatrix in="n" type="saturate" values="0"/>'
        f'</filter></defs>'
        f'<path d="{poly(OUT)}" fill="{_lerp(BEZEL, BEZEL_DARK, 0.3)}"/>'
        + facets() +
        f'<path d="{poly(INSET)}" fill="url(#panel)"/>'
        f'<path d="{poly(INSET)}" fill="none" stroke="#000" stroke-width="10" '
        f'opacity="0.75" filter="url(#soft)"/>'
        f'<path d="{poly(OUT)} {poly(INSET)}" fill="url(#sheen)" '
        f'fill-rule="evenodd"/>'
        f'<path d="{poly(OUT)}" fill="none" stroke="{STRUCT}" stroke-width="1.1" '
        f'opacity="0.55"/>'
        f'<path d="{poly(OUT)}" fill="none" stroke="#ffffff" stroke-width="0.6" '
        f'opacity="0.12"/>'
        f'<g clip-path="url(#frame)">'
        f'<path d="{poly(INSET)}" fill="none" stroke="#000" stroke-width="7" '
        f'opacity="0.55"/>'
        f'<rect width="{S}" height="{S}" filter="url(#grain)" opacity="0.07"/>'
        f'<path d="{poly(OUT)}" fill="none" stroke="#000" stroke-width="1" '
        f'opacity="0.35"/></g>')


def clip(cid: str) -> str:
    return (f'<clipPath id="{cid}"><path d="{poly(INSET)}"/></clipPath>'
            f'<clipPath id="frame"><path d="{poly(OUT)}"/></clipPath>')


# ------------------------------------------------------------------ gestures

def cut(x1: float, y1: float, x2: float, y2: float, width: float,
        lit: float = 1.0) -> str:
    """A cut between two points: shadowed near wall, lit far wall, dark floor.

    A filled band reads as UI. A cut reads as metal, because the light catches
    the far wall of it and the floor of it stays black. The lip always falls on
    the side facing away from the light, whichever way the cut runs.
    """
    ln = math.hypot(x2 - x1, y2 - y1) or 1.0
    nx, ny = (y2 - y1) / ln, -(x2 - x1) / ln      # normal to the cut
    if nx * LX + ny * LY > 0:                     # keep it pointing away from the light
        nx, ny = -nx, -ny
    half = width / 2
    ox, oy = nx * half, ny * half
    return (
        f'<path d="M{x1:.2f},{y1 + oy * 1.6:.2f} L{x2:.2f},{y2 + oy * 1.6:.2f}" '
        f'stroke="#000" stroke-width="{width + 7:.2f}" opacity="0.45" '
        f'filter="url(#soft)"/>'
        f'<path d="M{x1:.2f},{y1:.2f} L{x2:.2f},{y2:.2f}" stroke="#000" '
        f'stroke-width="{width:.2f}" opacity="0.96"/>'
        f'<path d="M{x1:.2f},{y1:.2f} L{x2:.2f},{y2:.2f}" stroke="{ARC}" '
        f'stroke-width="1.0" opacity="{0.10 * lit:.2f}" filter="url(#soft)"/>'
        f'<path d="M{x1 + ox:.2f},{y1 + oy:.2f} L{x2 + ox:.2f},{y2 + oy:.2f}" '
        f'stroke="{ARC}" stroke-width="2.2" opacity="{0.85 * lit:.2f}"/>'
        f'<path d="M{x1 + ox * 0.6:.2f},{y1 + oy * 0.6:.2f} '
        f'L{x2 + ox * 0.6:.2f},{y2 + oy * 0.6:.2f}" stroke="{ARC}" '
        f'stroke-width="0.9" opacity="{0.30 * lit:.2f}"/>')


def _arc(x: float, y: float, r: float, a0: float, a1: float) -> str:
    """A rim arc, in degrees, for the specular and shadow sides of a hole."""
    t0, t1 = math.radians(a0), math.radians(a1)
    p0 = (x + r * math.cos(t0), y + r * math.sin(t0))
    p1 = (x + r * math.cos(t1), y + r * math.sin(t1))
    return (f"M{p0[0]:.2f},{p0[1]:.2f} A{r:.2f},{r:.2f} 0 0 1 "
            f"{p1[0]:.2f},{p1[1]:.2f}")


def aperture(x: float, y: float, r: float, colour: str = AMBER) -> str:
    """A machined hole that is lit from inside: seat, dark mouth, emissive rim."""
    return (
        # the light the hole throws onto the panel around it
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r + 7:.2f}" fill="{colour}" '
        f'opacity="0.14" filter="url(#soft)"/>'
        # the seat it is drilled through
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r + 4.5:.2f}" fill="#0a0908"/>'
        f'<path d="{_arc(x, y, r + 4.5, 188, 268)}" fill="none" stroke="#fff" '
        f'stroke-width="1.1" opacity="0.35" stroke-linecap="round"/>'
        f'<path d="{_arc(x, y, r + 4.5, 8, 88)}" fill="none" stroke="#000" '
        f'stroke-width="2.4" opacity="0.6" stroke-linecap="round"/>'
        # the mouth
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="#030202"/>'
        # the lit rim, brighter where the light is
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="none" '
        f'stroke="{colour}" stroke-width="2.0"/>'
        f'<path d="{_arc(x, y, r, 188, 268)}" fill="none" stroke="#fff" '
        f'stroke-width="1.2" opacity="0.6" stroke-linecap="round"/>'
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r - 3.0:.2f}" fill="none" '
        f'stroke="{colour}" stroke-width="0.8" opacity="0.28"/>')


# ------------------------------------------------------------------ the plates

def walk(cid: str = "box") -> str:
    """One level cut, one riser, one more cut. A step is the whole gesture."""
    y0, y1 = Y0 + B * 0.62, Y0 + B * 0.26
    x0, x1 = X0 + B * 0.13, X0 + B * 0.63
    return (
        f'<g clip-path="url(#{cid})">'
        + cut(x0, y0, x1, y0, 15)
        + cut(x1, y0, x1, y1, 15)
        + cut(x1, y1, X0 + B * 0.86, y1, 15)
        + "</g>"
        + aperture(X0 + B * 0.86, y1, 10))


def daydream(cid: str = "box") -> str:
    """Two cuts crossing at a shallow angle. Drift, and where it happens to meet."""
    cx, cy = X0 + B / PHI ** 2, Y0 + B * 0.60
    far = B * 0.9
    a, b = math.radians(8), math.radians(-7)
    return (
        f'<g clip-path="url(#{cid})">'
        + cut(cx - math.cos(a) * far, cy - math.sin(a) * far,
              cx + math.cos(a) * far, cy + math.sin(a) * far, 10, 0.85)
        + cut(cx - math.cos(b) * far, cy - math.sin(b) * far,
              cx + math.cos(b) * far, cy + math.sin(b) * far, 7, 0.40)
        + "</g>"
        + aperture(cx, cy, 9))


def dream(cid: str = "box") -> str:
    """Three cuts through one point. Recombination."""
    cx, cy = X0 + B / 2, Y0 + B / 2
    far = B * 1.1
    out = [f'<g clip-path="url(#{cid})">']
    for deg in (0, 60, 120):
        t = math.radians(deg)
        dx, dy = math.cos(t) * far, math.sin(t) * far
        out.append(cut(cx - dx, cy - dy, cx + dx, cy + dy, 10, 0.9))
    out.append("</g>")
    out.append(aperture(cx, cy, 10))
    return "".join(out)


def doomscroll(cid: str = "box") -> str:
    """One cut, then the same cut again, lower and shorter. A feed."""
    out = [f'<g clip-path="url(#{cid})">']
    rows = [(0.26, 0.84, 14, 1.00),
            (0.42, 0.74, 11, 0.62),
            (0.55, 0.62, 9, 0.42),
            (0.66, 0.50, 7, 0.28),
            (0.75, 0.38, 5, 0.18)]
    for y, reach, w, lit in rows:
        out.append(cut(X0 + B * 0.18, Y0 + B * y, X0 + B * (0.18 + reach),
                       Y0 + B * y, w, lit))
    out.append("</g>")
    out.append(aperture(X0 + B * 0.18, Y0 + B * 0.26, 9))
    return "".join(out)


PLATES = {"walk": walk, "daydream": daydream, "dream": dream, "doomscroll": doomscroll}


def svg(name: str, body_inner: str, cid: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" '
            f'viewBox="0 0 {S} {S}"><defs>{clip(cid)}</defs>'
            f'<rect width="{S}" height="{S}" fill="{VOID}"/>'
            f'{body()}{body_inner}</svg>')


def sheet() -> str:
    cells = []
    for i, (name, fn) in enumerate(PLATES.items()):
        cid = f"c{i}"
        cells.append(f'<g transform="translate({S * i},0)">'
                     f'{svg(name, fn(cid), cid)[5:-6]}</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{S * 4}" height="{S}" '
            f'viewBox="0 0 {S * 4} {S}">' + "".join(cells) + "</svg>")


def rasterise(svg_path: pathlib.Path, png_path: pathlib.Path,
              w: int = S, h: int = S) -> None:
    """Chromium at 2x, because ImageMagick's SVG rasteriser flattens this."""
    subprocess.run([
        "chromium-browser", "--headless=new", "--no-sandbox", "--hide-scrollbars",
        "--force-device-scale-factor=2", f"--window-size={w},{h}",
        "--default-background-color=00000000", "--virtual-time-budget=2500",
        f"--screenshot={png_path}", svg_path.as_uri(),
    ], check=True, capture_output=True)


def main() -> None:
    out = pathlib.Path(__file__).resolve().parent.parent / "docs" / "brand" / "marks"
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in PLATES.items():
        (out / f"{name}.svg").write_text(svg(name, fn(), "box"), encoding="utf-8")
    (out / "sheet.svg").write_text(sheet(), encoding="utf-8")
    # The chart-language variant is retired; the flat drafts are cleared out.
    for stale in ("cut", "sheet.png"):
        p = out / stale
        if p.is_dir():
            for f in p.iterdir():
                f.unlink()
            p.rmdir()
        elif p.exists():
            p.unlink()
    if "--png" in sys.argv:
        for name in PLATES:
            rasterise(out / f"{name}.svg", out / f"{name}.png")
        rasterise(out / "sheet.svg", out / "sheet.png", S * 4, S)
    print(out)


if __name__ == "__main__":
    main()
