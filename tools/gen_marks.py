"""Draw the Antemuse state marks from their construction geometry.

One silhouette, four interiors. The outline is a chamfered square — the turn.
Its interior is ordered differently per state, because a state is a bounded
change to how the agent behaves, not a place it goes.

Everything is derived from constants here, so the plates can be re-cut rather
than re-drawn:

    S       plate size
    B       mark box (silhouette)
    C       chamfer, exactly B/4 (a 45 degree cut, never a radius)
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
C = B / 4                    # chamfer
PHI = (1 + 5 ** 0.5) / 2
R2 = 2 ** 0.5
X0 = (S - B) / 2             # mark origin
Y0 = (S - B) / 2

VOID = "#070a0b"             # anodised near-black, cool
STRUCT = "#9aa6ab"           # titanium: structure, never fills
EDGE = "#2a3236"             # panel edge
AMBER = "#f2b25a"            # the emitter: the state itself
ARC = "#6fe0c8"              # the path: hairline only

HAIR = 1.5                   # hairline weight
RULE = 3.0                   # rule weight
MARK = 6.0                   # the one heavy stroke per plate


def chamfer(x: float, y: float, side: float, c: float) -> str:
    """A square with its four corners cut at 45 degrees."""
    return (f"M{x + c},{y} L{x + side - c},{y} L{x + side},{y + c} "
            f"L{x + side},{y + side - c} L{x + side - c},{y + side} "
            f"L{x + c},{y + side} L{x},{y + side - c} L{x},{y + c} Z")


def head(extra: str = "") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" '
            f'viewBox="0 0 {S} {S}">{extra}')


def plate(inner: str, ground: bool = True) -> str:
    bg = (f'<rect width="{S}" height="{S}" fill="{VOID}"/>' if ground else "")
    return head(f"<defs><clipPath id=\"box\">"
                f"<path d=\"{chamfer(X0, Y0, B, C)}\"/></clipPath></defs>"
                ) + bg + inner + "</svg>"


def construction(ops: str) -> str:
    """The proof lines: they are drawn, not hidden. Faint, never decorative."""
    return (f'<g clip-path="url(#box)" opacity="0.13" stroke="{ARC}" '
            f'stroke-width="{HAIR * 0.7}" fill="none">{ops}</g>')


def outline(colour: str = STRUCT, width: float = HAIR * 1.6) -> str:
    return (f'<path d="{chamfer(X0, Y0, B, C)}" fill="none" stroke="{colour}" '
            f'stroke-width="{width}"/>')


# ------------------------------------------------------------------ interiors

def walk() -> str:
    """One monotone path, climbing the phi grid. A walk takes the shortest way."""
    lvl = [0.62, 0.44, 0.44, 0.26, 0.26, 0.10]
    xs = [X0 + B * f for f in (0.16, 0.30, 0.44, 0.58, 0.72, 0.86)]
    pts = [(x, Y0 + B * y) for x, y in zip(xs, lvl)]
    d = " ".join(f"{'M' if i == 0 else 'L'}{x:.2f},{y:.2f}"
                 for i, (x, y) in enumerate(pts))
    nodes = "".join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{ARC}" opacity="0.55"/>'
        for x, y in pts[1:-1])
    end = f'<circle cx="{pts[-1][0]:.2f}" cy="{pts[-1][1]:.2f}" r="9" fill="none" ' \
          f'stroke="{AMBER}" stroke-width="{RULE}"/>'
    con = construction(
        f'<path d="M{X0},{Y0 + B / PHI:.2f} H{X0 + B}"/>'
        f'<path d="M{X0 + B * 0.618:.2f},{Y0} V{Y0 + B}"/>')
    return plate(con + outline() +
                 f'<path d="{d}" fill="none" stroke="{ARC}" stroke-width="{MARK}" '
                 f'stroke-linejoin="miter"/>' + nodes + end)


def daydream() -> str:
    """Two phi-nested outlines, offset and drifting. No destination."""
    d = 26
    inner = chamfer(X0 + B / PHI, Y0 + B / PHI, B / PHI ** 2, C / PHI)
    con = construction(
        f'<path d="M{X0},{Y0 + B * 0.5:.2f} H{X0 + B}"/>'
        f'<path d="M{X0 + B * 0.5:.2f},{Y0} V{Y0 + B}"/>'
        f'<circle cx="{X0 + B / 2}" cy="{Y0 + B / 2}" r="{B / 2 * R2:.2f}"/>')
    drift = "".join(
        f'<path d="M{X0 + B * 0.10 + d * i:.2f},{Y0 + B * 0.78 + 9 * i:.2f} '
        f'h{B * 0.16 - 10 * i:.2f}"/>' for i in range(4))
    return plate(
        con + outline() +
        f'<path d="{inner}" fill="none" stroke="{ARC}" stroke-width="{HAIR * 2}" '
        f'opacity="0.75" transform="translate({d},{d})"/>'
        f'<g stroke="{STRUCT}" stroke-width="{HAIR}" opacity="0.5">{drift}</g>' +
        f'<circle cx="{X0 + B / 2 + d:.2f}" cy="{Y0 + B / 2 + d:.2f}" r="5" '
        f'fill="{AMBER}"/>')


def dream() -> str:
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
    con = construction(
        f'<circle cx="{cx}" cy="{cy}" r="{B / PHI:.2f}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{B / PHI ** 2:.2f}"/>')
    return plate(con + outline() +
                 f'<g clip-path="url(#box)" stroke="{ARC}" fill="none">'
                 + "".join(lines) + "</g>" +
                 f'<circle cx="{cx}" cy="{cy}" r="{B / 14:.2f}" fill="{VOID}" '
                 f'stroke="{AMBER}" stroke-width="{RULE}"/>')


def doomscroll() -> str:
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
    con = construction(
        f'<path d="M{X0 + B * 0.15:.2f},{Y0} V{Y0 + B}"/>'
        f'<path d="M{X0 + B * 0.85:.2f},{Y0} V{Y0 + B}"/>')
    return plate(con + outline() + "".join(out))


MARKS = {"walk": walk, "daydream": daydream, "dream": dream, "doomscroll": doomscroll}


def main() -> None:
    out = pathlib.Path(__file__).resolve().parent.parent / "docs" / "brand" / "marks"
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in MARKS.items():
        (out / f"{name}.svg").write_text(fn(), encoding="utf-8")
        print(out / f"{name}.svg")
    # Lattice sheet: the four interiors side by side, for reading at a glance.
    cell = 256
    sheet = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{cell * 4}" '
             f'height="{cell}" viewBox="0 0 {S * 4} {S}">'
             f'<rect width="{S * 4}" height="{S}" fill="{VOID}"/>']
    for i, name in enumerate(MARKS):
        body = fn().split(">", 1)[1].rsplit("</svg>", 1)[0]
        sheet.append(f'<g transform="translate({S * i},0)">{body}</g>')
    sheet.append("</svg>")
    (out / "sheet.svg").write_text("".join(sheet), encoding="utf-8")
    print(out / "sheet.svg")


if __name__ == "__main__":
    main()
