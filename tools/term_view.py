"""Look at a plate the way the plugin shows a state: `▀` cells, truecolor.

The cell model comes from `core/photographs.py` — the same code that turns a
PNG into what `/states` draws — so this is the terminal's view of the image, not
a second renderer that happens to look similar.

Three outputs per image:

    <name>.txt    the literal characters, no escapes (what a text surface gets)
    <name>.html   the cells as coloured spans, one glyph per cell
    <name>.png    that html, screenshotted at 2x — the terminal's look, as pixels

Run:  python3 tools/term_view.py docs/brand/marks/walk.png 96 40
"""
from __future__ import annotations

import html
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from core import photographs, surfaces  # noqa: E402  the real renderers

CELL = "▀"          # foreground is the top pixel, background the bottom pixel
FONT_PX = 16
LINE = 1.0


def cells_for(path: pathlib.Path, cols: int, rows: int):
    return photographs.cells(path, cols, rows)


def plain(cells) -> str:
    """Characters only. On a surface with no colour this is the whole picture."""
    return "\n".join(CELL * len(row) for row in cells)


def spans(cells) -> str:
    out = []
    for row in cells:
        line = []
        for top, bottom in row:
            line.append(f'<span style="color:rgb{top};background:rgb{bottom}">'
                        f'{CELL}</span>')
        out.append("".join(line))
    return "\n".join(out)


def page(body: str, cols: int) -> str:
    return (
        "<!doctype html><meta charset=utf-8>"
        f"<style>html,body{{margin:0;background:#0e0c0b}}"
        f"pre{{margin:0;padding:0;font:{FONT_PX}px/{LINE} 'DejaVu Sans Mono',monospace;"
        f"white-space:pre;letter-spacing:0}}</style>"
        f"<pre>{body}</pre>")


def paint(cells, png_path: pathlib.Path, scale: int = 8) -> None:
    """Draw the cells as pixels: one cell is one top pixel over one bottom pixel.

    No font, no layout, no rasteriser — this is the cell model itself, which is
    what the terminal is actually showing.
    """
    from PIL import Image
    w, h = len(cells[0]), len(cells)
    im = Image.new("RGB", (w * scale, h * 2 * scale // 2 * 2), (14, 12, 11))
    im = Image.new("RGB", (w, h * 2), (14, 12, 11))
    px = im.load()
    for y, row in enumerate(cells):
        for x, (top, bottom) in enumerate(row):
            px[x, y * 2] = top
            px[x, y * 2 + 1] = bottom
    im.resize((w * scale, h * 2 * scale), Image.NEAREST).save(png_path)


def shot(html_path: pathlib.Path, png_path: pathlib.Path, cols: int, rows: int) -> None:
    w = int(cols * FONT_PX * 0.602) + 2      # DejaVu Mono advance is 0.602 em
    h = int(rows * FONT_PX * LINE) + 2
    subprocess.run([
        "chromium-browser", "--headless=new", "--no-sandbox", "--hide-scrollbars",
        "--force-device-scale-factor=2", f"--window-size={w},{h}",
        f"--screenshot={png_path}", html_path.as_uri(),
    ], check=True, capture_output=True)


def ramp(path: pathlib.Path, cols: int, rows: int) -> list[str]:
    """The desktop pane's own rendering: luminance ramp, no colour, no escapes.

    Rather than reimplement the ramp, stage the file where `surfaces.art` looks
    for frames and call it. Anything else would drift from what the pane draws.
    """
    import shutil
    import tempfile

    from PIL import Image, ImageFilter, ImageOps

    # Grade for the ramp before the ramp sees it. A plate lit for truecolor has a
    # histogram that lands almost entirely in the bottom fifth of the ramp, where
    # every cell becomes the same dot; crushing the floor and lifting the highlights
    # is what makes the frame, the field, and the cut separate again.
    im = Image.open(path).convert("L")
    im = ImageOps.autocontrast(im, cutoff=(2, 2))
    im = im.point(lambda v: 0 if v < 70 else min(255, int((v - 70) * 255 / 185)))
    im = im.filter(ImageFilter.GaussianBlur(1.1))

    root = pathlib.Path(tempfile.mkdtemp(prefix="termview-"))
    scene = "plate"
    (root / scene).mkdir()
    im.save(root / scene / "0001.png")
    original = surfaces._frames_dir
    surfaces._frames_dir = lambda pane=False: root          # noqa: ARG005
    try:
        return surfaces.art(cols=cols, rows=rows, scene=scene, pane=True,
                            fit="cover", floor=0.06, gamma=0.85)
    finally:
        surfaces._frames_dir = original
        shutil.rmtree(root, ignore_errors=True)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    path = pathlib.Path(sys.argv[1]).resolve()
    cols = int(sys.argv[2]) if len(sys.argv) > 2 else 96
    rows = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    if "--ramp" in sys.argv:
        lines = ramp(path, cols, rows)
        print("\n".join(lines))
        return
    cells = cells_for(path, cols, rows)
    stamp = f"{path.stem}-{cols}x{rows}"
    txt = path.with_name(f"{stamp}.txt")
    page_path = path.with_name(f"{stamp}.html")
    png = path.with_name(f"{stamp}.png")
    txt.write_text(plain(cells), encoding="utf-8")
    page_path.write_text(page(spans(cells), cols), encoding="utf-8")
    paint(cells, png, scale=int(sys.argv[4]) if len(sys.argv) > 4 else 8)
    print(f"{txt}\n{page_path}\n{png}")


if __name__ == "__main__":
    main()
