#!/usr/bin/env python3
"""Draw the concept ledger: concepts, the sessions they were met in, the files they touch.

    python3 tools/graph_export.py                 # writes json + svg + png
    python3 tools/graph_export.py --limit 120     # a smaller, readable picture
    python3 tools/graph_export.py --open          # print the paths only

No model, no network. The layout is a deterministic spring: the same ledger always draws the
same picture, so two exports can be compared instead of described.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "experiments" / "graph"

COLOURS = {
    "concept": (216, 160, 91),     # amber: the things the plugin serves
    "session": (86, 148, 159),     # teal: where they were met
    "file": (150, 150, 158),       # grey: the artifacts they were attached to
    "project": (196, 92, 76),      # red: which repository a file belongs to
}
RADIUS = {"concept": 5.0, "session": 7.0, "file": 3.5, "project": 9.0}


def layout(nodes: list, edges: list, width: int = 1400, height: int = 900,
           iterations: int = 0, seed: int = 7) -> dict:
    """Concentric rings, not a spring.

    A spring layout on a hub-and-spoke graph is a hairball with an empty middle: the hubs
    repel everything outward and the centre goes black. The structure here is already known —
    concepts in the middle, the files they touch around them, the projects those files belong
    to, and the sessions the concepts were met in on the outside — so it is drawn as that.

    Concepts are placed on a phyllotaxis spiral (golden angle), which spaces any number of
    points evenly without overlap. The layout is deterministic: same ledger, same picture.
    """
    import math as _m
    if not nodes:
        return {}
    deg = degrees(nodes, edges)
    cx, cy = width / 2, height / 2
    radius = min(width, height) * 0.46
    pos = {}
    groups = {}
    for n in nodes:
        groups.setdefault(n["kind"], []).append(n)

    golden = _m.pi * (3 - _m.sqrt(5))
    concepts = sorted(groups.get("concept", []), key=lambda n: (-deg.get(n["id"], 0), n["label"]))
    for i, n in enumerate(concepts):
        r = radius * 0.46 * _m.sqrt((i + 0.5) / max(1, len(concepts)))
        theta = i * golden
        pos[n["id"]] = [cx + _m.cos(theta) * r, cy + _m.sin(theta) * r]

    for kind, ring in (("project", 0.62), ("file", 0.80), ("session", 1.0)):
        members = sorted(groups.get(kind, []), key=lambda n: n["label"])
        for i, n in enumerate(members):
            theta = 2 * _m.pi * i / max(1, len(members)) - _m.pi / 2
            pos[n["id"]] = [cx + _m.cos(theta) * radius * ring,
                            cy + _m.sin(theta) * radius * ring]
    return pos


def degrees(nodes: list, edges: list) -> dict:
    deg = {n["id"]: 0 for n in nodes}
    for e in edges:
        if e["source"] in deg:
            deg[e["source"]] += 1
        if e["target"] in deg:
            deg[e["target"]] += 1
    return deg


def captions(nodes: list, edges: list, top: int = 34) -> list:
    """Label the nodes that carry the structure: the well-connected concepts, every session,
    every project. Files are unlabelled — there are many and their names are long."""
    deg = degrees(nodes, edges)
    picked = [n for n in nodes if n["kind"] in ("session", "project")]
    concepts = sorted((n for n in nodes if n["kind"] == "concept"),
                      key=lambda n: deg[n["id"]], reverse=True)
    picked += concepts[:top]
    return [(n["id"], n["label"][:24], deg[n["id"]]) for n in picked]


def draw_png(nodes: list, edges: list, pos: dict, path: Path,
             width: int = 1400, height: int = 900) -> None:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (width, height), (8, 8, 10))
    draw = ImageDraw.Draw(img, "RGBA")
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 12)
        small = ImageFont.truetype("DejaVuSans.ttf", 11)
    except Exception:
        font = small = ImageFont.load_default()
    for e in edges:
        a, b = pos.get(e["source"]), pos.get(e["target"])
        if not a or not b:
            continue
        draw.line([tuple(a), tuple(b)], fill=(120, 120, 130, 46), width=1)
    order = sorted(nodes, key=lambda n: RADIUS.get(n["kind"], 4))
    for node in order:
        x, y = pos[node["id"]]
        r = RADIUS.get(node["kind"], 4)
        colour = COLOURS.get(node["kind"], (200, 200, 200))
        draw.ellipse([x - r, y - r, x + r, y + r], fill=colour + (235,),
                     outline=(0, 0, 0, 255))
    cx, cy = width / 2, height / 2
    for nid, label, _deg in captions(nodes, edges):
        x, y = pos[nid]
        dx = x - cx
        w = draw.textlength(label, font=font)
        tx = x + 10 if dx >= 0 else x - 10 - w
        draw.text((tx, y - 6), label, fill=(226, 226, 232, 225), font=font)
    kinds = {}
    for node in nodes:
        kinds[node["kind"]] = kinds.get(node["kind"], 0) + 1
    legend = "  ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
    draw.text((20, 18), "concept ledger", fill=(238, 238, 244, 255), font=font)
    draw.text((20, 36), f"{legend}   ·   {len(edges)} edges", fill=(150, 150, 158, 255), font=small)
    img.save(path)


def draw_svg(nodes: list, edges: list, pos: dict, path: Path,
             width: int = 1400, height: int = 900) -> None:
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}">',
             f'<rect width="{width}" height="{height}" fill="#08080a"/>']
    for e in edges:
        a, b = pos.get(e["source"]), pos.get(e["target"])
        if not a or not b:
            continue
        parts.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                     f'stroke="#787882" stroke-opacity="0.22" stroke-width="1"/>')
    for node in nodes:
        x, y = pos[node["id"]]
        r = RADIUS.get(node["kind"], 4)
        c = COLOURS.get(node["kind"], (200, 200, 200))
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" '
                     f'fill="rgb({c[0]},{c[1]},{c[2]})"/>')
    cx, cy = width / 2, height / 2
    for nid, label, _deg in captions(nodes, edges):
        x, y = pos[nid]
        escaped = (label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        anchor = "start" if x >= cx else "end"
        dx = 10 if x >= cx else -10
        parts.append(f'<text x="{x + dx:.1f}" y="{y + 4:.1f}" fill="#e2e2e8" '
                     f'text-anchor="{anchor}" font-family="DejaVu Sans, sans-serif" '
                     f'font-size="11">{escaped}</text>')
    kinds = {}
    for node in nodes:
        kinds[node["kind"]] = kinds.get(node["kind"], 0) + 1
    legend = "  ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
    parts.append(f'<text x="20" y="24" fill="#eeeef4" font-family="DejaVu Sans, sans-serif" '
                 f'font-size="13">concept ledger</text>')
    parts.append(f'<text x="20" y="42" fill="#96969e" font-family="DejaVu Sans, sans-serif" '
                 f'font-size="11">{legend}  ·  {len(edges)} edges</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=400)
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args(argv)

    from core import graph as graph_mod
    data = graph_mod.snapshot(limit=args.limit)
    summary = graph_mod.summary(data)
    if not data["nodes"]:
        print("no graph · the ledger is empty (run a state, or scan past sessions)")
        return 1

    dest = Path(args.out)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "concept-graph.json").write_text(json.dumps(
        {"summary": summary, **data}, indent=2, sort_keys=True) + "\n")

    pos = layout(data["nodes"], data["edges"])
    draw_png(data["nodes"], data["edges"], pos, dest / "concept-graph.png")
    draw_svg(data["nodes"], data["edges"], pos, dest / "concept-graph.svg")

    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"\n{dest / 'concept-graph.png'}\n{dest / 'concept-graph.svg'}\n{dest / 'concept-graph.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
