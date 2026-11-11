#!/usr/bin/env python3
"""Project every WordNet synset once, and keep the projection instead of the vectors.

    <venv>/bin/python tools/project_wordnet.py

An embedding is only ever used for three things here: a 2D position, a 3D position, and "which
concepts are near this one". All three are computable once, offline, for the whole synset set —
117,659 synsets, a few minutes of CPU — after which nothing needs the vectors at runtime and
nothing needs to store 90 MB of float16 to answer a question with five numbers and three indices.

The projections are principal components of the same centred matrix, so the 2D view is exactly the
3D view seen down the third axis. Deterministic: same input, same numbers, no seed, no UMAP.

Artifacts (written to ~/.cache/antemuse/):

  wordnet.proj.json   labels, meta, and the 384x3 basis — so a concept that is in the ledger's own
                      embeddings file but not in WordNet can still be placed by projecting it
  wordnet.proj.f16    count x 5: x2, y2, x3, y3, z3 per label, little-endian float16
  wordnet.nbr.int32   count x 3: the three nearest labels by cosine, as row indices

Total is a few megabytes, read with `struct`, no numpy at runtime.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_OUT = Path.home() / ".cache" / "antemuse"
BATCH = 256
MAX_TOKENS = 96
NEIGHBOURS = 3
CHUNK = 512


def synsets() -> list:
    from nltk.corpus import wordnet as wn
    return list(wn.all_synsets())


def text_for(syn) -> str:
    label = syn.lemmas()[0].name().replace("_", " ")
    lemmas = ", ".join(lem.name().replace("_", " ") for lem in syn.lemmas())
    return f"{label}: {syn.definition()} ({lemmas})"


def embed(texts: list, model_name: str) -> np.ndarray:
    import torch
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()

    out = []
    with torch.no_grad():
        for start in range(0, len(texts), BATCH):
            batch = tok(texts[start:start + BATCH], padding=True, truncation=True,
                        max_length=MAX_TOKENS, return_tensors="pt")
            hidden = model(**batch).last_hidden_state[:, 0]
            out.append(torch.nn.functional.normalize(hidden, dim=-1).cpu().numpy())
            if start and start % (BATCH * 40) == 0:
                print(f"  embedded {start}/{len(texts)}", flush=True)
    return np.vstack(out)


def principal(vectors: np.ndarray, dims: int = 3) -> np.ndarray:
    """The projection basis: eigenvectors of the covariance, ordered by variance."""
    centred = vectors - vectors.mean(axis=0, keepdims=True)
    cov = np.cov(centred, rowvar=False)
    values, vectors_ = np.linalg.eigh(cov)
    order = np.argsort(values)[::-1]
    return np.ascontiguousarray(vectors_[:, order[:dims]].astype(np.float32))


def neighbours(vectors: np.ndarray, k: int) -> np.ndarray:
    """Three nearest labels per label, by cosine, computed in row chunks."""
    n = vectors.shape[0]
    out = np.zeros((n, k), dtype=np.int32)
    v = vectors.astype(np.float32)
    for start in range(0, n, CHUNK):
        block = v[start:start + CHUNK]
        sims = block @ v.T
        # the concept itself is its own nearest — drop it before taking k
        for i in range(block.shape[0]):
            row = sims[i]
            row[start + i] = -2.0
        idx = np.argpartition(-sims, k, axis=1)[:, :k]
        out[start:start + block.shape[0]] = idx.astype(np.int32)
        if start and start % (CHUNK * 10) == 0:
            print(f"  neighbours {start}/{n}", flush=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    syns = synsets()
    labels = [s.lemmas()[0].name().replace("_", " ") for s in syns]
    texts = [text_for(s) for s in syns]
    print(f"{len(syns)} synsets · texts in {time.time() - t0:.1f}s", flush=True)

    t1 = time.time()
    scratch = out_dir / "_wordnet_vectors.npy"
    if scratch.exists():
        vectors = np.load(scratch)
        print(f"reused cached vectors · {vectors.shape}", flush=True)
    else:
        vectors = embed(texts, args.model)
        np.save(scratch, vectors)
        print(f"embedded · {vectors.shape} in {time.time() - t1:.1f}s · "
              f"cached at {scratch.name}", flush=True)
    del texts

    t2 = time.time()
    basis = principal(vectors, 3)
    coords3 = (vectors - vectors.mean(axis=0, keepdims=True)) @ basis
    coords = np.hstack([coords3[:, :2], coords3])          # 2D is the 3D seen down the third axis
    kept = float(coords3.var(axis=0).sum() / vectors.var(axis=0).sum())
    print(f"projected · {time.time() - t2:.1f}s · variance kept {kept:.2f}", flush=True)

    t3 = time.time()
    nbr = neighbours(vectors, NEIGHBOURS)
    print(f"neighbours · {time.time() - t3:.1f}s", flush=True)
    del vectors

    matrix = out_dir / "wordnet.proj.f16"
    nbr_path = out_dir / "wordnet.nbr.int32"
    index = out_dir / "wordnet.proj.json"

    np.ascontiguousarray(coords.astype("<f2")).tofile(matrix)
    np.ascontiguousarray(nbr.astype("<i4")).tofile(nbr_path)
    index.write_text(json.dumps({
        "model": args.model,
        "count": int(coords.shape[0]),
        "fields": ["x2", "y2", "x3", "y3", "z3"],
        "dtype": "float16",
        "neighbours": NEIGHBOURS,
        "basis": [[round(float(x), 6) for x in row] for row in basis.tolist()],
        "labels": labels,
    }))
    print(f"wrote {matrix.name} {matrix.stat().st_size / 1e6:.2f} MB · "
          f"{nbr_path.name} {nbr_path.stat().st_size / 1e6:.2f} MB · "
          f"{index.name} {index.stat().st_size / 1e6:.2f} MB")
    print(f"total {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
