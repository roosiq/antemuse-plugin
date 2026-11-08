#!/usr/bin/env python3
"""Write the pack manifest from the ledger and from facts measured on disk.

Nothing is inferred: a file that is not on disk is reported as missing rather than
described, and the credit total is the sum of what the ledger says each task cost.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import sys


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def glb_triangles(path: pathlib.Path) -> int:
    """Count triangles in a GLB without a glTF library: JSON chunk, then accessors."""
    data = path.read_bytes()
    magic, _version, _length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67:
        raise ValueError(f"{path.name}: not a GLB")
    offset, doc = 12, None
    while offset < len(data):
        length, ctype = struct.unpack_from("<II", data, offset)
        if ctype == 0x4E4F534A:
            doc = json.loads(data[offset + 8: offset + 8 + length].decode("utf-8"))
        offset += 8 + length + ((4 - length % 4) % 4)
    if not doc:
        raise ValueError(f"{path.name}: no JSON chunk")
    total = 0
    for mesh in doc.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4:
                continue
            key = "indices" if "indices" in prim else None
            if key:
                total += doc["accessors"][prim["indices"]]["count"] // 3
            else:
                total += doc["accessors"][prim["attributes"]["POSITION"]]["count"] // 3
    return total


ROOT = pathlib.Path("/home/ryan/antemuse-plugin")
PACK = ROOT / "data/meshy/pack"


def measure(path: pathlib.Path) -> dict:
    if path.suffix == ".glb":
        return {"sha256": sha256(path), "bytes": path.stat().st_size,
                "triangles": glb_triangles(path)}
    from PIL import Image
    with Image.open(path) as im:
        return {"sha256": sha256(path), "bytes": path.stat().st_size,
                "size_px": [im.width, im.height]}


def main() -> None:
    rows = [json.loads(line) for line in (PACK / "ledger.jsonl").read_text().splitlines() if line.strip()]
    seen: dict[str, dict] = {}
    credits = 0
    for row in rows:
        if row.get("kind") not in ("mesh", "image", "refine"):
            continue
        name = row["name"]
        if name in seen:
            continue
        seen[name] = row
        credits += int(row.get("credits_est") or 0)

    assets, missing = [], []
    for name, row in sorted(seen.items()):
        is_mesh = row["kind"] in ("mesh", "refine")
        path = PACK / row["state"] / f"{name}.{'glb' if is_mesh else 'png'}"
        if not path.exists():
            missing.append(name)
            continue
        record = {
            "name": name,
            "state": row["state"],
            "file": str(path.relative_to(ROOT)),
            "kind": row["kind"],
            "prompt": row.get("prompt", ""),
            "task_id": row.get("task_id"),
            "credits": row.get("credits_est"),
            "route": ("text-to-3d refine" if row["kind"] == "refine"
                      else "text-to-3d preview (smart-topology)" if is_mesh
                      else "text-to-image (nano-banana-pro)"),
        }
        if row["kind"] == "refine":
            record["from"] = row.get("from")
        record.update(measure(path))
        assets.append(record)

    manifest = {
        "pack": "abstract-geometry",
        "provider": "meshy",
        "generated": "2026-11-08",
        "style": ("geometric, futuristic, abstract, cyberpunk; classical mathematics forms only; "
                  "no furniture, no devices, no people, no letters"),
        "licence": "Meshy output, generated on a paid Meshy plan for this project",
        "credits_spent": credits,
        "counts": {
            "meshes": sum(1 for a in assets if a["kind"] == "mesh"),
            "refined": sum(1 for a in assets if a["kind"] == "refine"),
            "images": sum(1 for a in assets if a["kind"] == "image"),
        },
        "missing": missing,
        "assets": assets,
    }
    (PACK / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(assets)} assets, {credits} credits, {len(missing)} missing -> {PACK/'manifest.json'}")
    if missing:
        print("missing:", ", ".join(missing))


if __name__ == "__main__":
    main()
