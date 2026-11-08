#!/usr/bin/env python3
"""Generate the abstract asset pack through the Meshy CLI.

Style contract, from the owner: geometric, futuristic, abstract, cyberpunk — but
*not* analogous to the current world (no furniture, no devices, no people, no
architecture that implies a life), and built from classical mathematics. So the
subjects are solids, surfaces, knots and lattices, and the only light is neon.

    python3 gen_pack.py submit     # fire every task, append to ledger
    python3 gen_pack.py wait       # poll, download, append results
    python3 gen_pack.py status     # balance + ledger tally

The ledger is append-only JSONL: one line per submitted task, one per download.
Re-running submit is safe to skip; task ids are the record.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/home/ryan/antemuse-plugin")
OUT = ROOT / "data/meshy/pack"
LEDGER = OUT / "ledger.jsonl"
CLI = ["npm", "exec", "--yes", "--package=meshy-cli@0.4.3", "--", "meshy"]

STYLE = (", geometric abstract futuristic cyberpunk, classical mathematics form, polished chrome "
         "and dark glass, neon rim light, isolated on pure black, no text, no letters, no logos")

# (state, name, prompt, polycount)
MESHES = [
    ("walk", "pilgrim_star", "a faceted stellated octahedron construct, sharp geometric planes, chrome and black glass, faint neon seams", 6000),
    ("walk", "gateway_torus", "a thin perfect torus ring standing upright like a gateway, polished chrome, neon rim", 8000),
    ("walk", "lattice_plane", "a square lattice plane of glowing orthogonal grid lines, dark reflective surface, geometric", 9000),
    ("walk", "monolith_slab", "a tall slender rectangular monolith, matte black, neon seams along every edge", 4000),
    ("walk", "arch_frames", "nested receding square arch frames, neon edges, no walls, pure geometry", 6000),
    ("walk", "spiral_ribbon", "a logarithmic golden spiral ribbon rising into the air, chrome, geometric", 8000),
    ("daydream", "dodecahedron", "a perfect regular dodecahedron, brushed titanium faces, glowing edges", 4000),
    ("daydream", "icosahedron", "a perfect regular icosahedron, dark glass with an inner neon core", 4000),
    ("daydream", "gyroid_cube", "a gyroid minimal surface contained inside a cube, chrome, precise geometry", 12000),
    ("daydream", "mobius_ribbon", "a mobius strip ribbon, matte white ceramic, single neon edge", 9000),
    ("daydream", "torus_knot", "a torus knot, polished chrome, tight geometric weave", 12000),
    ("daydream", "banded_sphere", "a sphere made of separated latitude bands floating apart, chrome and neon", 8000),
    ("doomscroll", "engraved_slab", "a thin rectangular slab with abstract engraved geometric grooves, dark basalt, no markings that read as language", 3000),
    ("doomscroll", "glyph_panel", "a capsule-shaped panel with an abstract glowing geometric line pattern, no letters, no symbols that read", 3000),
    ("doomscroll", "prism_bar", "a long triangular prism bar, dark chrome with a neon core", 3000),
    ("doomscroll", "segment_ring", "a ring of floating rectangular segments, chrome, neon gaps", 4000),
    ("doomscroll", "plate_stack", "a stack of translucent rectangular plates, edge-lit, geometric", 3000),
    ("dream", "tesseract_frame", "a tesseract wireframe sculpture built from chrome tubes", 12000),
    ("dream", "trefoil_solid", "a solid trefoil knot, polished chrome, classical mathematical form", 12000),
    ("dream", "impossible_triangle", "an impossible triangle frame in brushed steel, penrose geometry", 6000),
    ("dream", "klein_form", "a klein bottle form, smooth self-intersecting surface, chrome", 12000),
    ("dream", "square_torus", "a torus with a square cross-section woven through itself, chrome", 10000),
    ("dream", "fractal_tetra", "a recursively subdivided tetrahedron cluster, three levels, chrome", 12000),
    ("dream", "geodesic_fragment", "a geodesic dome fragment with glowing joints, chrome struts", 10000),
    ("dream", "hopf_rings", "nested interlinked rings forming a hopf fibration, chrome, geometry only", 12000),
    ("dream", "hypercube_grid", "a projected 4D hypercube frame of nested cubes, brushed steel", 10000),
    ("dream", "chladni_plate", "a chladni plate pattern raised in chrome ridges on a black plate", 8000),
    ("dream", "wave_rods", "a grid of vertical rods at varying heights forming a smooth wave surface", 9000),
    ("scene", "great_circle_sphere", "a great-circle wireframe sphere made of neon tubes", 10000),
    ("scene", "double_helix", "a double helix of square-section bars, chrome, geometric", 10000),
    ("scene", "platonic_cluster", "a cluster of interpenetrating platonic solids, chrome, neon edges", 12000),
    ("scene", "concentric_rings", "a field of concentric rings receding into darkness, neon edges", 6000),
    # second wave: the forms that read best at ramp resolution — silhouette first
    ("walk", "sierpinski_tetra", "a sierpinski tetrahedron at three levels, chrome struts, pure geometry", 12000),
    ("walk", "square_arch_series", "a series of square frames scaling geometrically into the distance, neon edges", 8000),
    ("daydream", "borromean_rings", "three interlocking borromean rings, chrome, no other objects", 10000),
    ("daydream", "hyperboloid", "a ruled hyperboloid of one sheet, thin chrome lines, geometric", 9000),
    ("doomscroll", "tessellated_block", "a block of repeating geometric cells with neon seams, abstract", 5000),
    ("scene", "fractal_spiral_flat", "a flat golden spiral of geometric segments on a dark disc, neon edge", 6000),
]

# --- third wave: forms built to read at eight glyphs, for the compositions that do
# not read yet. A face-on wall beats a corridor when the subject must fill a pane, and
# a tall waisted solid beats a faceted ball as the opposite of a mass.
MESHES += [
    ("doomscroll", "slab_wall", "a wall of stacked rectangular slabs with deep even gaps between them, face on, flat planes, neon lines in the seams", 9000),
    ("doomscroll", "plate_stack_face", "three large plates layered front to back seen face on, each with a geometric engraved border, deep shadow between them", 8000),
    ("doomscroll", "engraved_panel_large", "one large rectangular panel with a dense engraved geometric pattern of concentric squares and radial lines, flat and face on", 6000),
    ("daydream", "hyperboloid_tall", "a tall waisted hyperboloid of one sheet, thin ruled lines, chrome, geometric and empty in the middle", 8000),
    ("daydream", "banded_sphere", "a sphere banded by concentric horizontal rings with gaps between the bands, chrome, geometric", 7000),
    ("walk", "square_arch_monolith", "a single square arch cut from one block, sharp inner edges, matte black with neon lining", 5000),
]

IMAGES = [
    ("walk", "lattice_horizon", "an endless orthogonal neon lattice horizon over black, geometric, cyberpunk, no objects, no sky detail", "16:9"),
    ("daydream", "platonic_field", "a field of faint wireframe platonic solids floating in deep indigo, geometric, no text", "1:1"),
    ("doomscroll", "slab_stream", "abstract dark rectangular slabs drifting on pure black, high contrast, amber neon edges, no letters, no faces", "16:9"),
    ("dream", "curve_etching", "classical mathematics curves etched in chrome on black, spirals and families of lines, no numerals, no letters", "1:1"),
    ("dream", "topology_field", "abstract topology of interlinked loops in chrome on black, geometric, no text", "1:1"),
    ("scene", "ring_spectrum", "concentric neon rings on black, spectral gradient, pure geometry, no text", "1:1"),
    ("walk", "lattice_deep", "a deep receding lattice tunnel of square frames, neon edges, black void", "1:1"),
    ("scene", "solid_field", "interpenetrating wireframe solids in chrome on black, geometric, no text", "1:1"),
]

# Refined after preview: the four that carry the most screen area.
HEROES = ["pilgrim_star", "tesseract_frame", "trefoil_solid", "gyroid_cube"]


def ledger(entry: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    entry = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), **entry}
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def run(args: list[str], timeout: int = 300) -> dict:
    env = dict(os.environ)
    env.pop("MESHY_API_KEY", None)          # the CLI's own OAuth profile is the authority
    cmd = CLI + args + ["--output-schema", "v1", "--format", "json", "--no-update-check"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    raw = proc.stdout
    start = raw.find("{")
    if start < 0:
        raise RuntimeError(f"{shlex.join(args[:3])}: no JSON\n{raw[-400:]}\n{proc.stderr[-400:]}")
    return json.loads(raw[start:])


def submit() -> None:
    for state, name, prompt, polys in MESHES:
        result = run(["text-to-3d", "create", "--mode", "preview",
                      "--model-type", "smart-topology", "--target-polycount", str(polys),
                      "--prompt", prompt + STYLE, "--target-formats", "glb", "--async"])
        task = (result.get("result") or {}).get("task_id")
        ledger({"kind": "mesh", "state": state, "name": name, "task_id": task,
                "prompt": prompt + STYLE, "polycount": polys, "credits_est": 5,
                "error": result.get("error")})
        print(f"mesh  {state}/{name}: {task}", flush=True)
    for state, name, prompt, ratio in IMAGES:
        result = run(["text-to-image", "create", "--ai-model", "nano-banana-pro",
                      "--aspect-ratio", ratio, "--prompt", prompt, "--async"])
        task = (result.get("result") or {}).get("task_id")
        ledger({"kind": "image", "state": state, "name": name, "task_id": task,
                "prompt": prompt, "aspect": ratio, "credits_est": 9,
                "error": result.get("error")})
        print(f"image {state}/{name}: {task}", flush=True)


def entries() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]


def wait() -> None:
    done = {e.get("task_id") for e in entries() if e.get("downloaded")}
    for entry in entries():
        task = entry.get("task_id")
        if not task or task in done:
            continue
        resource = "text-to-3d" if entry["kind"] == "mesh" else "text-to-image"
        try:
            res = run([resource, "wait", task, "--timeout", "600"], timeout=660)
        except Exception as exc:                     # a dead task must not stop the pack
            ledger({"kind": "wait-failed", "name": entry["name"], "task_id": task, "error": str(exc)})
            print(f"!!    {entry['name']}: {exc}", flush=True)
            continue
        result = res.get("result") or {}
        status = (result.get("task") or {}).get("status")
        if status != "SUCCEEDED":
            ledger({"kind": "not-succeeded", "name": entry["name"], "task_id": task, "status": status})
            print(f"!!    {entry['name']}: {status}", flush=True)
            continue
        dest = OUT / entry["state"] / f"{entry['name']}.{'glb' if entry['kind'] == 'mesh' else 'png'}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dl = ["download", "--resource", resource, "--task-id", task, "--output", str(dest)]
        if entry["kind"] == "mesh":
            dl += ["--model-format", "glb"]
        try:
            run(dl, timeout=300)
        except Exception as exc:
            ledger({"kind": "download-failed", "name": entry["name"], "task_id": task, "error": str(exc)})
            print(f"!!    {entry['name']}: download {exc}", flush=True)
            continue
        size = dest.stat().st_size if dest.exists() else 0
        ledger({"kind": "downloaded", "name": entry["name"], "state": entry["state"],
                "task_id": task, "path": str(dest.relative_to(ROOT)), "bytes": size,
                "downloaded": True, "status": status})
        print(f"ok    {entry['state']}/{entry['name']}  {size//1024} KB", flush=True)


def refine() -> None:
    """Refine the four hero meshes: real textures on the forms that fill the screen."""
    by_name = {e["name"]: e for e in entries() if e.get("task_id") and e["kind"] == "mesh"}
    for name in HEROES:
        entry = by_name.get(name)
        if not entry:
            print(f"!!  {name}: no preview task", flush=True)
            continue
        dest = OUT / entry["state"] / f"{name}_refined.glb"
        if dest.exists():
            print(f"..  {name}: already refined", flush=True)
            continue
        result = run(["text-to-3d", "create", "--mode", "refine",
                      "--preview-task-id", entry["task_id"], "--enable-pbr", "true", "--async"])
        task = (result.get("result") or {}).get("task_id")
        ledger({"kind": "refine", "state": entry["state"], "name": name + "_refined",
                "task_id": task, "from": entry["task_id"], "credits_est": 10,
                "error": result.get("error")})
        print(("fill refine " if task else "CAP  refine ") + f"{name}: {task}", flush=True)
        if not task:
            return


def grab() -> None:
    """Download every task that already succeeded, skipping files on disk.

    Cheaper than one `wait` per task: `list` answers status for the whole account,
    then only the finished ones are fetched.
    """
    for entry in entries():
        task = entry.get("task_id")
        if not task:
            continue
        # "refine" is a 3D task too: a refined mesh is a GLB, not a picture.
        is_mesh = entry["kind"] in ("mesh", "refine")
        ext = "glb" if is_mesh else "png"
        dest = OUT / entry["state"] / f"{entry['name']}.{ext}"
        if dest.exists() and dest.stat().st_size > 0:
            ledger({"kind": "downloaded", "name": entry["name"], "state": entry["state"],
                    "task_id": task, "path": str(dest.relative_to(ROOT)),
                    "bytes": dest.stat().st_size, "downloaded": True, "status": "SUCCEEDED"})
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        resource = "text-to-3d" if is_mesh else "text-to-image"
        dl = ["download", "--resource", resource, "--task-id", task, "--output", str(dest)]
        if is_mesh:
            dl += ["--model-format", "glb"]
        try:
            run(dl, timeout=300)
        except Exception as exc:
            ledger({"kind": "download-failed", "name": entry["name"], "task_id": task, "error": str(exc)})
            print(f"!!  {entry['name']}: {exc}", flush=True)
            continue
        size = dest.stat().st_size if dest.exists() else 0
        ledger({"kind": "downloaded", "name": entry["name"], "state": entry["state"],
                "task_id": task, "path": str(dest.relative_to(ROOT)), "bytes": size,
                "downloaded": True, "status": "SUCCEEDED"})
        print(f"ok  {entry['state']}/{entry['name']}  {size//1024} KB", flush=True)


def fill() -> None:
    """Submit only what is still missing a task id — Meshy caps pending tasks.

    The cap is around twenty; submitting the whole pack at once earns a 429 on the
    tail. So the pack is drained in waves: wait, download, then fill the gaps.
    """
    rows = entries()
    have = {e["name"] for e in rows if e.get("task_id")}
    mesh_prompts = {name: (state, prompt, polys) for state, name, prompt, polys in MESHES}
    image_prompts = {name: (state, prompt, ratio) for state, name, prompt, ratio in IMAGES}
    missing = [(m, image_prompts.get(m)) for m in mesh_prompts if m not in have]
    for name, _ in missing:
        state, prompt, polys = mesh_prompts[name]
        result = run(["text-to-3d", "create", "--mode", "preview",
                      "--model-type", "smart-topology", "--target-polycount", str(polys),
                      "--prompt", prompt + STYLE, "--target-formats", "glb", "--async"])
        task = (result.get("result") or {}).get("task_id")
        error = result.get("error")
        ledger({"kind": "mesh", "state": state, "name": name, "task_id": task,
                "prompt": prompt + STYLE, "polycount": polys, "credits_est": 5, "error": error})
        print(("fill mesh  " if task else "CAP  mesh  ") + f"{state}/{name}: {task}", flush=True)
        if not task:
            return                       # still capped: let the caller drain and retry
    for name, (state, prompt, ratio) in image_prompts.items():
        if name in have:
            continue
        result = run(["text-to-image", "create", "--ai-model", "nano-banana-pro",
                      "--aspect-ratio", ratio, "--prompt", prompt, "--async"])
        task = (result.get("result") or {}).get("task_id")
        ledger({"kind": "image", "state": state, "name": name, "task_id": task,
                "prompt": prompt, "aspect": ratio, "credits_est": 9, "error": result.get("error")})
        print(("fill image " if task else "CAP  image ") + f"{state}/{name}: {task}", flush=True)
        if not task:
            return


def status() -> None:
    bal = run(["balance"])
    print("balance:", json.dumps(bal.get("result") or bal))
    rows = entries()
    kinds: dict[str, int] = {}
    for e in rows:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print("ledger:", kinds)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"submit": submit, "wait": wait, "fill": fill, "grab": grab, "refine": refine,
     "status": status}[what]()
