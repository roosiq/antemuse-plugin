#!/usr/bin/env python3
"""Draw the states firing: the concept map with activations lit.

    python3 tools/activation_render.py --session 20261108_091834_aa6c8db0 --frames 10
    python3 tools/activation_render.py --move walk --frames 8 --size 640x400
    python3 tools/activation_render.py --session X --gif

Reads the ledger and the embedding cache; writes PNG frames plus a montage and, with `--gif`, an
animation. No labels are drawn anywhere: the card is a picture, and a picture of a state is not
a list of its words.

Nothing here enters a state or calls a model. It is a view over what the ledger already recorded.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "experiments" / "activation"


def embeddings_path() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")).expanduser()
    return base / "antemuse" / "embeddings.json"


def coords_for(labels: list, embeddings: str = "") -> tuple:
    """Semantic positions for the labels we have vectors for, plus their nearest-neighbour
    edges — the same projection the graph export uses, so the pictures agree."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ge", ROOT / "tools" / "graph_export.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("graph_export.py is not importable")
    ge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ge)

    emb = Path(embeddings) if embeddings else embeddings_path()
    payload = json.loads(emb.read_text()) if emb.exists() else {}
    vectors = payload.get("vectors", {})
    usable = [label for label in labels if label in vectors]
    if not usable:
        return {}, []
    coords = ge.refine(ge.pca2(vectors, usable), {k: vectors[k] for k in usable}, iters=60)
    edges = []
    for label in usable:
        sims = sorted(((sum(x * y for x, y in zip(vectors[label], vectors[o])), o)
                       for o in usable if o != label), reverse=True)[:2]
        for _score, other in sims:
            edges.append((label, other))
    return coords, edges


def fit(coords: dict, width: int, height: int, pad: int = 40) -> dict:
    xs = [c[0] for c in coords.values()]
    ys = [c[1] for c in coords.values()]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    sx = (width - 2 * pad) / ((x1 - x0) or 1.0)
    sy = (height - 2 * pad) / ((y1 - y0) or 1.0)
    scale = min(sx, sy)
    off_x = (width - 2 * pad - (x1 - x0) * scale) / 2
    off_y = (height - 2 * pad - (y1 - y0) * scale) / 2
    return {k: [pad + (v[0] - x0) * scale + off_x, pad + (v[1] - y0) * scale + off_y]
            for k, v in coords.items()}


def draw_frame(pos: dict, edges: list, active: dict, width: int, height: int):
    """One frame: the dim map, the lit concepts, and a trail of what just cooled."""
    from PIL import Image, ImageDraw, ImageFilter
    img = Image.new("RGB", (width, height), (6, 6, 8))
    draw = ImageDraw.Draw(img, "RGBA")

    for a, b in edges:
        if a in pos and b in pos:
            draw.line([tuple(pos[a]), tuple(pos[b])], fill=(90, 90, 100, 26), width=1)

    live = {label: slot for label, slot in active.items() if label in pos}
    for label, p in pos.items():
        if label in live:
            continue
        draw.ellipse([p[0] - 1.4, p[1] - 1.4, p[0] + 1.4, p[1] + 1.4], fill=(120, 120, 130, 90))

    glow = Image.new("RGB", (width, height), (0, 0, 0))
    gdraw = ImageDraw.Draw(glow, "RGBA")
    for label, slot in live.items():
        p = pos[label]
        w = max(0.05, float(slot.get("weight", 0.0)))
        r = 3.0 + 13.0 * w
        gdraw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r],
                      fill=(int(210 * w) + 30, int(150 * w) + 24, int(70 * w) + 10, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=6))
    img = Image.blend(img, Image.composite(glow, img, glow.convert("L")), 0.85)
    draw = ImageDraw.Draw(img, "RGBA")
    for label, slot in live.items():
        p = pos[label]
        w = max(0.05, float(slot.get("weight", 0.0)))
        r = 1.6 + 4.4 * w
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r],
                     fill=(255, int(210 * w) + 40, int(120 * w) + 30, 255))
    return img


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default="", help="session id (defaults to the newest with moves)")
    parser.add_argument("--move", default="", help="restrict to one state, e.g. walk")
    parser.add_argument("--frames", type=int, default=10)
    parser.add_argument("--size", default="720x460")
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--gif", action="store_true")
    parser.add_argument("--embeddings", default=str(embeddings_path()))
    args = parser.parse_args(argv)

    from core import activation, history

    session = args.session
    if not session:
        sql = """SELECT session, COUNT(*) FROM served WHERE 1=1"""
        params = []
        if args.move:
            sql += " AND move = ?"
            params.append(args.move)
        sql += " GROUP BY session ORDER BY COUNT(*) DESC LIMIT 1"
        rows = history._query(sql, tuple(params))
        if not rows:
            print("· no state servings in the ledger — run a state, then look again")
            return 1
        session = rows[0][0]

    frames = activation.sequence(session, args.move or None, steps=args.frames)
    if not frames:
        print(f"· nothing recorded for {history.session_label(session)}"
              f"{' in ' + args.move if args.move else ''}")
        return 1

    labels = sorted({label for f in frames for label in f["activations"]})
    coords, edges = coords_for(labels, args.embeddings)
    if not coords:
        print(f"· {len(labels)} concepts fired, but no vectors cover them — run tools/graph_embed.py")
        return 1

    width, height = (int(x) for x in args.size.lower().split("x"))
    pos = fit(coords, width, height)

    tag = session[:24] if session else (args.move or "all")
    dest = Path(args.out)
    dest.mkdir(parents=True, exist_ok=True)
    images = []
    for i, frame in enumerate(frames):
        img = draw_frame(pos, edges, frame["activations"], width, height)
        path = dest / f"{tag}-{i:02d}.png"
        img.save(path)
        images.append(img)

    # montage: one row, so the sequence reads as a strip
    cols = len(images)
    strip = images[0].resize((width // 2, height // 2))
    montage = Image_new = None
    from PIL import Image
    montage = Image.new("RGB", (cols * (width // 2), height // 2), (6, 6, 8))
    for i, img in enumerate(images):
        montage.paste(img.resize((width // 2, height // 2)), (i * (width // 2), 0))
    montage.save(dest / f"{tag}-strip.png")

    if args.gif:
        images[0].save(dest / f"{tag}.gif", save_all=True,
                       append_images=images[1:], duration=340, loop=0)

    print(json.dumps({"session": history.session_label(session), "move": args.move or "any",
                      **activation.summary(frames),
                      "hottest": activation.hot(frames, 6)}, indent=2))
    print(f"\n{dest / (tag + '-strip.png')}")
    if args.gif:
        print(dest / (tag + ".gif"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
