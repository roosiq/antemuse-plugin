"""Draw the Antemuse state marks from their construction geometry.

One silhouette, four interiors. The outline is a chamfered square — the turn.
Its interior is ordered differently per state, because a state is a bounded
change to how the agent behaves, not a place it goes.

Everything is derived from constants here, so the plates can be re-cut rather
than re-drawn:

    S       plate size
    B       mark box (silhouette)
    C1, C2  the two chamfers: B/2.8 on opposite corners, B/9 on the others
    BODY    the machined body weight — a bezel, never a frame
    PHI     golden section
    R2      1/sqrt(2) — the diagonal the chamfer runs along

Run:  python3 tools/gen_marks.py
Out:  docs/brand/marks/*.svg
"""
from __future__ import annotations

import math
import pathlib

S = 512
B = 384                      # silhouette box
C1 = B / 2.8                 # the long cut, two opposite corners
C2 = B / 9                   # the short cut, the other two
BODY = 22.0                  # the machined body: a bezel, not a frame
PHI = (1 + 5 ** 0.5) / 2
R2 = 2 ** 0.5
X0 = (S - B) / 2             # mark origin
Y0 = (S - B) / 2

VOID = "#0e0c0b"             # the shipped ground: warm near-black
STRUCT = "#9aa6ab"           # titanium: structure, never fills
EDGE = "#2a3236"             # panel edge
AMBER = "#f2b25a"            # the emitter: the state itself
ARC = "#6fe0c8"              # arc: the path, and the interior light

HAIR = 1.5                   # hairline weight
RULE = 3.0                   # rule weight
MARK = 6.0                   # the one heavy stroke per plate


def chamfer(x: float, y: float, side: float, c1: float | None = None,
            c2: float | None = None) -> str:
    """A square cut at 45 degrees, two corners long and two short.

    Unequal on purpose: equal corners read as a stop sign, and a stop sign is a
    UI container. Long cuts on opposite corners read as a machined blade.
    """
    c1 = C1 if c1 is None else c1
    c2 = C2 if c2 is None else c2
    r = x + side
    b = y + side
    return (f"M{x + c1},{y} L{r - c2},{y} L{r},{y + c2} "
            f"L{r},{b - c1} L{r - c1},{b} L{x + c2},{b} "
            f"L{x},{b - c2} L{x},{y + c1} Z")


def inset(k: float) -> str:
    """The same silhouette pulled in by k, for the edge-light hairline."""
    return chamfer(X0 + k, Y0 + k, B - 2 * k)


def head(extra: str = "") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" '
            f'viewBox="0 0 {S} {S}">{extra}')


def plate(inner: str, cid: str = "box", ground: bool = True) -> str:
    bg = (f'<rect width="{S}" height="{S}" fill="{VOID}"/>' if ground else "")
    return head(f"<defs><clipPath id=\"{cid}\">"
                f"<path d=\"{inset(BODY / 2)}\"/></clipPath></defs>"
                ) + bg + inner + "</svg>"


def construction(ops: str, cid: str = "box") -> str:
    """The proof lines: they are drawn, not hidden. Faint, never decorative."""
    return (f'<g clip-path="url(#{cid})" opacity="0.13" stroke="{ARC}" '
            f'stroke-width="{HAIR * 0.7}" fill="none">{ops}</g>')


def body() -> str:
    """A dark body with one lit edge: the panel the mark is stamped into."""
    return (f'<path d="{chamfer(X0, Y0, B)}" fill="none" stroke="{EDGE}" '
            f'stroke-width="{BODY}" stroke-linejoin="miter"/>'
            f'<path d="{inset(BODY / 2)}" fill="none" stroke="{STRUCT}" '
            f'stroke-width="{HAIR}" opacity="0.45"/>')



def vernier(cid: str) -> str:
    """A measuring scale along the inner floor: an instrument, not an axis.

    Long ticks sit at the golden section of the width; the rest are even. It is
    the one classical-maths cue that reads as machined rather than as a chart.
    """
    y = Y0 + B - BODY / 2 - 14
    x0, w = X0 + BODY / 2 + 10, B - BODY - 20
    ticks = []
    for k in range(21):
        f = k / 20
        h = 12 if any(abs(f - g) < 1e-9 for g in (0.0, 1 / PHI ** 2, 1 / PHI, 1.0)) else 6
        ticks.append(f'<path d="M{x0 + w * f:.2f},{y:.2f} v{-h}"/>')
    return (f'<g clip-path="url(#{cid})" stroke="{ARC}" stroke-width="{HAIR * 0.8}" '
            f'opacity="0.30" fill="none">' + "".join(ticks) + "</g>")


# ------------------------------------------------------------------ interiors

def walk(cid: str = "box") -> str:
    """One monotone path, climbing the phi grid. A walk takes the shortest way."""
    lvl = [0.62, 0.44, 0.44, 0.26, 0.26, 0.10]
    xs = [X0 + B * f for f in (0.19, 0.32, 0.45, 0.58, 0.71, 0.84)]
    pts = [(x, Y0 + B * y) for x, y in zip(xs, lvl)]
    d = " ".join(f"{'M' if i == 0 else 'L'}{x:.2f},{y:.2f}"
                 for i, (x, y) in enumerate(pts))
    nodes = "".join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{ARC}" opacity="0.55"/>'
        for x, y in pts[1:-1])
    end = f'<circle cx="{pts[-1][0]:.2f}" cy="{pts[-1][1]:.2f}" r="9" fill="none" ' \
          f'stroke="{AMBER}" stroke-width="{RULE}"/>'
    con = vernier(cid)
    return plate(con + body() +
                 f'<path d="{d}" fill="none" stroke="{ARC}" stroke-width="{MARK}" '
                 f'stroke-linejoin="miter"/>' + nodes + end)


def daydream(cid: str = "box") -> str:
    """Two lattices out of register. Drift without a destination."""
    step = B / 9
    shift = step / PHI
    dots, ghost = [], []
    for i in range(1, 9):
        for j in range(1, 9):
            x, y = X0 + step * i, Y0 + step * j
            if 0.30 < (i / 10) + 0.11 * math.sin(j * 1.7) < 0.86:
                dots.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.4" '
                            f'fill="{STRUCT}" opacity="0.55"/>')
    for i in range(1, 8):
        for j in range(1, 8):
            x, y = X0 + step * i + shift, Y0 + step * j + shift
            ghost.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.6" '
                         f'fill="{ARC}" opacity="0.8"/>')
    con = vernier(cid)
    return plate(con + body() +
                 f'<g clip-path="url(#{cid})">' + "".join(dots) + "".join(ghost) + "</g>"
                 f'<circle cx="{X0 + B / 2 + shift:.2f}" cy="{Y0 + B / 2 + shift:.2f}" '
                 f'r="12" fill="none" stroke="{AMBER}" stroke-width="{RULE * 1.4}"/>', cid)


def dream(cid: str = "box") -> str:
    """Three revolutions of the same grid at 0/30/60: six-fold, recombined."""
    cx, cy = X0 + B / 2, Y0 + B / 2
    lines = []
    for k in range(3):
        a = 30 * k
        lines.append(f'<g transform="rotate({a} {cx} {cy})" opacity="'
                     f'{0.95 - 0.3 * k}">')
        for i in range(-3, 4):
            o = B / 7 * i
            lines.append(f'<path d="M{cx + o},{cy - B} V{cy + B}" '
                         f'stroke-width="{HAIR if i % 3 else HAIR * 1.4}"/>')
        lines.append("</g>")
    con = vernier(cid) + construction(
        f'<circle cx="{cx}" cy="{cy}" r="{B / PHI:.2f}"/>')
    return plate(con + body() +
                 f'<g clip-path="url(#{cid})" stroke="{ARC}" fill="none">'
                 + "".join(lines) + "</g>" +
                 f'<circle cx="{cx}" cy="{cy}" r="{B / 14:.2f}" fill="{VOID}" '
                 f'stroke="{AMBER}" stroke-width="{RULE}"/>')


def doomscroll(cid: str = "box") -> str:
    """The same tile, forever, compressed toward the floor. A feed."""
    rows, out = 7, []
    for i in range(rows):
        t = i / (rows - 1)
        h = 30 * (1 - t) ** 1.4 + 6
        y = Y0 + B * 0.18 + t * B * 0.70
        w = B * (0.30 + 0.44 * (1 - t))
        x = X0 + B * 0.5 - w / 2
        col = AMBER if i == 0 else ARC
        op = 0.9 - 0.1 * i
        out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" '
                   f'height="{h:.2f}" fill="{col}" opacity="{max(op, 0.18):.2f}"/>')
        if i == 0:
            out.append(f'<rect x="{x - 6:.2f}" y="{y - 6:.2f}" width="{w + 12:.2f}" '
                       f'height="{h + 12:.2f}" fill="none" stroke="{STRUCT}" '
                       f'stroke-width="{HAIR}" opacity="0.4"/>')
    con = vernier(cid)
    return plate(con + body() + "".join(out))



# ------------------------------------------------------- variant B: one cut
# The chart read is a property of diagrams, not of the brand. In variant B the
# interior is a single cut across the body — the same turn, cut differently.

def blade(angle: float, offset: float, thick: float, opacity: float,
          colour: str, cid: str, edge: bool = True) -> str:
    cx, cy = X0 + B / 2, Y0 + B / 2
    w = B * 2.2
    body = (f'<g transform="rotate({angle} {cx} {cy})">'
            f'<rect x="{cx - w / 2:.2f}" y="{cy + offset - thick / 2:.2f}" '
            f'width="{w:.2f}" height="{thick:.2f}" fill="{colour}" '
            f'opacity="{opacity}"/>')
    if edge:
        body += (f'<path d="M{cx - w / 2:.2f},{cy + offset - thick / 2:.2f} '
                 f'h{w:.2f}" stroke="{ARC}" stroke-width="{HAIR * 1.2}" '
                 f'opacity="0.9"/>')
    return body + "</g>"


def cut_walk(cid: str = "box") -> str:
    """One blade, level, with the leading edge lifted. Forward."""
    i = (f'<g clip-path="url(#{cid})">'
         + blade(0, B * 0.10, B * 0.30, 0.42, ARC, cid)
         + blade(-14, -B * 0.12, B * 0.10, 0.18, ARC, cid, edge=False)
         + "</g>"
         + f'<circle cx="{X0 + B * 0.80:.2f}" cy="{Y0 + B * 0.34:.2f}" r="11" '
           f'fill="none" stroke="{AMBER}" stroke-width="{RULE * 1.3}"/>')
    return plate(body() + i, cid)


def cut_daydream(cid: str = "box") -> str:
    """Two blades almost parallel: interference, not direction."""
    i = (f'<g clip-path="url(#{cid})">'
         + blade(9, -B * 0.06, B * 0.12, 0.30, ARC, cid, edge=False)
         + blade(19, B * 0.14, B * 0.12, 0.30, ARC, cid, edge=False)
         + "</g>")
    return plate(body() + vernier(cid) + i, cid)


def cut_dream(cid: str = "box") -> str:
    """Three blades through one point. Recombination."""
    i = (f'<g clip-path="url(#{cid})">'
         + "".join(blade(a, 0, B * 0.07, 0.40, ARC, cid) for a in (0, 60, 120))
         + "</g>")
    return plate(body() + i, cid)


def cut_doomscroll(cid: str = "box") -> str:
    """One blade, repeated, each lower than the last. A feed."""
    parts = [f'<g clip-path="url(#{cid})">']
    for i in range(6):
        t = i / 5
        parts.append(blade(0, B * (-0.30 + 0.16 * i), B * (0.13 - 0.015 * i),
                           0.46 - 0.055 * i, AMBER if i == 0 else ARC, cid))
    parts.append("</g>")
    return plate(body() + "".join(parts), cid)


CUTS = {"walk": cut_walk, "daydream": cut_daydream, "dream": cut_dream,
        "doomscroll": cut_doomscroll}

def sheet(family: dict, name: str) -> str:
    """The four plates side by side, as one file a browser can open."""
    cells = []
    for i, key in enumerate(family):
        cells.append(f'<g transform="translate({S * i},0)">'
                     f'{family[key](cid=f"{name}{i}")}</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{S * 4}" height="{S}" '
            f'viewBox="0 0 {S * 4} {S}">' + "".join(cells) + "</svg>")


MARKS = {"walk": walk, "daydream": daydream, "dream": dream, "doomscroll": doomscroll}


def main() -> None:
    """Write the four plates. The family row is composed from the PNGs, not here."""
    out = pathlib.Path(__file__).resolve().parent.parent / "docs" / "brand" / "marks"
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in MARKS.items():
        (out / f"{name}.svg").write_text(fn(), encoding="utf-8")
    cut = out / "cut"
    cut.mkdir(exist_ok=True)
    for name, fn in CUTS.items():
        (cut / f"{name}.svg").write_text(fn(), encoding="utf-8")
    (out / "sheet.svg").write_text(sheet(MARKS, "a"), encoding="utf-8")
    (cut / "sheet.svg").write_text(sheet(CUTS, "b"), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
