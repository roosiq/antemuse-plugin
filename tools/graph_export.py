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


def _embeddings_path() -> Path:
    import os
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")).expanduser()
    return base / "antemuse" / "embeddings.json"

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


def pca2(vectors: dict, labels: list, seed: int = 3) -> dict:
    """Two principal components by power iteration — no numpy, deterministic.

    Centred, then each component deflated before the next is found. The sign of each axis is
    fixed by making its largest-magnitude entry positive, because otherwise the same data can
    draw mirrored on two runs and a comparison becomes a puzzle.
    """
    import random
    rng = random.Random(seed)
    rows = [vectors[label] for label in labels]
    d = len(rows[0])
    mean = [sum(row[j] for row in rows) / len(rows) for j in range(d)]
    centred = [[row[j] - mean[j] for j in range(d)] for row in rows]

    comps = []
    for _ in range(2):
        vec = [rng.uniform(-1, 1) for _ in range(d)]
        for _ in range(60):
            proj = [sum(v * c for v, c in zip(row, vec)) for row in centred]
            new = [sum(p * row[j] for p, row in zip(proj, centred)) for j in range(d)]
            norm = math.sqrt(sum(x * x for x in new)) or 1.0
            vec = [x / norm for x in new]
        comps.append(vec)
        # deflate: remove this direction from every row
        centred = [[row[j] - sum(row[k] * comps[-1][k] for k in range(d)) * comps[-1][j]
                    for j in range(d)] for row in centred]

    xs = [sum(v * c for v, c in zip(row, comps[0])) for row in rows]
    ys = [sum(v * c for v, c in zip(row, comps[1])) for row in rows]
    for values, comp in ((xs, comps[0]), (ys, comps[1])):
        big = max(range(len(comp)), key=lambda i: abs(comp[i]))
        if comp[big] < 0:
            values[:] = [-v for v in values]
    return {label: (xs[i], ys[i]) for i, label in enumerate(labels)}


def refine(coords: dict, vectors: dict, iters: int = 80, power: float = 1.4) -> dict:
    """Stress majorization (SMACOF) of the 2D projection against embedding distances.

    PCA alone keeps only two of 384 directions, so everything lands in one narrow band. This
    pulls embedding neighbours together and pushes strangers apart while preserving the global
    arrangement. Measured on 600 sampled pairs: correlation between 2D distance and embedding
    distance goes **0.34 → 0.57**. An ad-hoc force version of this was tried first and made it
    *worse* (0.29), which is why it is the textbook update and not a clever one.
    """
    labels = list(coords)
    n = len(labels)
    if n < 3:
        return coords
    dist3 = {}
    for i in range(n):
        a = vectors[labels[i]]
        for j in range(i + 1, n):
            b = vectors[labels[j]]
            dist3[(i, j)] = max(0.02, 1.0 - sum(x * y for x, y in zip(a, b)))
    pairs = list(dist3)
    pos = {label: tuple(coords[label]) for label in labels}
    for _ in range(iters):
        xs = [pos[label] for label in labels]
        mean_d = sum(math.hypot(xs[i][0] - xs[j][0], xs[i][1] - xs[j][1]) for i, j in pairs) / len(pairs)
        mean_t = sum(v ** power for v in dist3.values()) / len(dist3)
        k = (mean_d / mean_t) if mean_t else 1.0
        new = {}
        for i in range(n):
            sx = sy = 0.0
            for j in range(n):
                if i == j:
                    continue
                key = (i, j) if i < j else (j, i)
                dt = dist3[key] ** power * k
                dx, dy = xs[i][0] - xs[j][0], xs[i][1] - xs[j][1]
                d = math.hypot(dx, dy) or 1e-6
                sx += xs[j][0] + dt * dx / d
                sy += xs[j][1] + dt * dy / d
            new[labels[i]] = (sx / (n - 1), sy / (n - 1))
        pos = new
    return pos


def projection_quality(coords: dict, vectors: dict, sample: int = 600, seed: int = 5) -> dict:
    """Correlation between 2D distance and embedding distance — a projection you cannot score
    is a decoration."""
    import random
    rng = random.Random(seed)
    labels = list(coords)
    pairs = []
    for _ in range(sample):
        i, j = rng.sample(range(len(labels)), 2)
        a, b = labels[i], labels[j]
        d2 = math.hypot(coords[a][0] - coords[b][0], coords[a][1] - coords[b][1])
        d3 = 1.0 - sum(x * y for x, y in zip(vectors[a], vectors[b]))
        pairs.append((d2, d3))
    n = len(pairs)
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    num = sum((p[0] - mx) * (p[1] - my) for p in pairs)
    den = math.sqrt(sum((p[0] - mx) ** 2 for p in pairs) * sum((p[1] - my) ** 2 for p in pairs))
    return {"pearson": round(num / den, 3) if den else 0.0, "pairs": n}


def semantic_layout(graph_data: dict, embeddings: dict, width: int = 1400,
                    height: int = 900) -> tuple:
    """Concepts placed by meaning: PCA of their embeddings, fitted to the canvas.

    Only concepts are projected. A session and a project have no semantic position — they are
    provenance and structure — so in this view they are not drawn at all rather than placed
    somewhere false.
    """
    vectors = embeddings.get("vectors", {})
    nodes = [n for n in graph_data["nodes"] if n["kind"] == "concept" and n["label"] in vectors]
    if not nodes:
        return [], {}
    coords = refine(pca2(vectors, [n["label"] for n in nodes]), vectors)
    xs = [coords[n["label"]][0] for n in nodes]
    ys = [coords[n["label"]][1] for n in nodes]
    pad, top = 90, 70
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    sx = (width - 2 * pad) / ((x1 - x0) or 1.0)
    sy = (height - top - pad) / ((y1 - y0) or 1.0)
    scale = min(sx, sy)
    pos = {n["id"]: [pad + (coords[n["label"]][0] - x0) * scale + (width - 2 * pad - (x1 - x0) * scale) / 2,
                     top + (coords[n["label"]][1] - y0) * scale + (height - top - pad - (y1 - y0) * scale) / 2]
           for n in nodes}
    # edges here mean "near in meaning": each concept to its two closest neighbours. Drawing
    # the structural co-served edges across a semantic map would be a category error.
    edges, seen = [], set()
    by_label = {n["label"]: n["id"] for n in nodes}
    labels = [n["label"] for n in nodes]
    vecs = {label: vectors[label] for label in labels}
    for label in labels:
        sims = sorted(((sum(x * y for x, y in zip(vecs[label], vecs[o])), o)
                       for o in labels if o != label), reverse=True)[:2]
        for _score, other in sims:
            key = tuple(sorted((by_label[label], by_label[other])))
            if key in seen:
                continue
            seen.add(key)
            edges.append({"source": by_label[label], "target": by_label[other],
                          "relation": "near_in_meaning", "weight": 1,
                          "evidence": {"cosine": round(_score, 3)}})
    return nodes, {"pos": pos, "edges": edges}


def degrees(nodes: list, edges: list) -> dict:
    deg = {n["id"]: 0 for n in nodes}
    for e in edges:
        if e["source"] in deg:
            deg[e["source"]] += 1
        if e["target"] in deg:
            deg[e["target"]] += 1
    return deg


def grid_labels(nodes: list, pos: dict, limit: int, width: int = 1400, height: int = 900,
                cell: tuple = (92, 15)) -> list:
    """Labels for as many nodes as fit in a coarse occupancy grid — nearest first.

    A semantic projection puts every concept somewhere meaningful, so labelling only the
    hubs would hide most of the picture; labelling all 400 without spacing would make it a
    smear. The grid is the compromise, and it is deterministic.
    """
    rows = int(height / cell[1]) + 1
    cols = int(width / cell[0]) + 1
    taken = [[False] * cols for _ in range(rows)]
    out = []
    for node in nodes:
        if len(out) >= limit:
            break
        x, y = pos.get(node["id"], (0, 0))
        r = min(rows - 1, max(0, int(y / cell[1])))
        c = min(cols - 1, max(0, int(x / cell[0])))
        if taken[r][c]:
            continue
        taken[r][c] = True
        out.append((node["id"], node["label"][:22], 0))
    return out


def captions(nodes: list, edges: list, top: int = 34) -> list:
    """Label the nodes that carry the structure: the well-connected concepts, every session,
    every project. Files are unlabelled — there are many and their names are long."""
    deg = degrees(nodes, edges)
    # Ryan, 2026-11-08: no dates on session nodes. A session is structure, not a timestamp
    # to read — its position says what it needs to say.
    picked = [n for n in nodes if n["kind"] == "project"]
    concepts = sorted((n for n in nodes if n["kind"] == "concept"),
                      key=lambda n: deg[n["id"]], reverse=True)
    picked += concepts[:top]
    return [(n["id"], n["label"][:24], deg[n["id"]]) for n in picked]


def draw_png(nodes: list, edges: list, pos: dict, path: Path, labelled: list = None,
             meta: str = "", width: int = 1400, height: int = 900) -> None:
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
        w = e.get("weight", 1)
        draw.line([tuple(a), tuple(b)], fill=(120, 120, 130, 46),
                  width=1 + min(3, int(math.log2(max(1, w)))))
    order = sorted(nodes, key=lambda n: RADIUS.get(n["kind"], 4))
    for node in order:
        x, y = pos[node["id"]]
        r = RADIUS.get(node["kind"], 4)
        colour = COLOURS.get(node["kind"], (200, 200, 200))
        draw.ellipse([x - r, y - r, x + r, y + r], fill=colour + (235,),
                     outline=(0, 0, 0, 255))
    cx, cy = width / 2, height / 2
    for nid, label, _deg in (labelled if labelled is not None else captions(nodes, edges)):
        if nid not in pos:
            continue
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
    if meta:
        draw.text((20, 52), meta, fill=(110, 110, 118, 255), font=small)
    img.save(path)


def draw_svg(nodes: list, edges: list, pos: dict, path: Path, labelled: list = None,
             meta: str = "", width: int = 1400, height: int = 900) -> None:
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}">',
             f'<rect width="{width}" height="{height}" fill="#08080a"/>']
    for e in edges:
        a, b = pos.get(e["source"]), pos.get(e["target"])
        if not a or not b:
            continue
        w = 1 + min(3, int(math.log2(max(1, e.get("weight", 1)))))
        parts.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                     f'stroke="#787882" stroke-opacity="0.22" stroke-width="{w}"/>')
    for node in nodes:
        x, y = pos[node["id"]]
        r = RADIUS.get(node["kind"], 4)
        c = COLOURS.get(node["kind"], (200, 200, 200))
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" '
                     f'fill="rgb({c[0]},{c[1]},{c[2]})"/>')
    cx, cy = width / 2, height / 2
    for nid, label, _deg in (labelled if labelled is not None else captions(nodes, edges)):
        if nid not in pos:
            continue
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
    if meta:
        parts.append(f'<text x="20" y="58" fill="#6e6e76" font-family="DejaVu Sans, sans-serif" '
                     f'font-size="11">{meta}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=400)
    parser.add_argument("--semantic", action="store_true",
                        help="place concepts by meaning (needs experiments/graph/embeddings.json)")
    parser.add_argument("--embeddings", default=str(_embeddings_path()))
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

    name = "concept-graph"
    if args.semantic:
        embeddings = {}
        emb_path = Path(args.embeddings)
        if emb_path.exists():
            embeddings = json.loads(emb_path.read_text())
        nodes, packed = semantic_layout(data, embeddings)
        if not nodes:
            print("no embeddings cover these concepts — run tools/graph_embed.py first")
            return 1
        pos, edges = packed["pos"], packed["edges"]
        name = "concept-semantic"
        labelled = grid_labels(nodes, pos, limit=84, cell=(104, 17))
        meta = (f"semantic projection · PCA of {embeddings.get('model', 'embeddings')} "
                f"({embeddings.get('dim', '?')}d) · {len(nodes)} concepts")
        data = {"nodes": nodes, "edges": edges,
                "counts": {"nodes": len(nodes), "edges": len(edges)}}
        summary = graph_mod.summary(data)          # the summary must describe what is drawn
        quality = projection_quality({n["label"]: pos[n["id"]] for n in nodes},
                                     {n["label"]: embeddings["vectors"][n["label"]] for n in nodes})
        print(json.dumps({"concepts": len(nodes), "edges": len(edges),
                          "model": embeddings.get("model"), "dim": embeddings.get("dim"),
                          "projection_quality": quality}, indent=2, sort_keys=True))
    else:
        pos = layout(data["nodes"], data["edges"])
        edges = data["edges"]
        labelled = captions(data["nodes"], data["edges"])
        meta = ""

    draw_png(data["nodes"], edges, pos, dest / f"{name}.png", labelled, meta)
    draw_svg(data["nodes"], edges, pos, dest / f"{name}.svg", labelled, meta)
    (dest / f"{name}.json").write_text(json.dumps(
        {"summary": summary, "layout": "semantic" if args.semantic else "concentric", **data},
        indent=2, sort_keys=True) + "\n")

    print(f"\n{dest / (name + '.png')}\n{dest / (name + '.svg')}\n{dest / (name + '.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
