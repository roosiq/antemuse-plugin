#!/usr/bin/env python3
"""Embed the ledger's concepts once, so the graph can be projected by meaning.

    /home/ryan/ontology-embedding-experiment/.venv/bin/python tools/graph_embed.py
    ... --model BAAI/bge-small-en-v1.5 --out experiments/graph/embeddings.json

This is the only tool in the repo that needs torch, so it is run with whatever interpreter has
it — the plugin itself never imports this. Vectors are written as unit-length float lists, keyed
by the concept's own label, and reused until the ledger grows past what they cover.

Why a separate step: the picture has to be reproducible and the plugin has to stay dependency
free. An embeddings file is a data artefact, not a new dependency.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
OUT = ROOT / "experiments" / "graph" / "embeddings.json"


def ledger_labels(limit: int = 800) -> list:
    from core import history
    rows = history._query("""SELECT label FROM concepts WHERE kind != 'file'
                             ORDER BY times DESC, last_seen DESC LIMIT ?""", (limit,))
    seen, out = set(), []
    for (label,) in rows:
        low = (label or "").strip()
        if low and low.lower() not in seen:
            seen.add(low.lower())
            out.append(low)
    return out


def embed(labels: list, model_name: str) -> dict:
    import torch
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()

    vectors = {}
    batch = 32
    with torch.no_grad():
        for i in range(0, len(labels), batch):
            chunk = labels[i:i + batch]
            encoded = tokenizer(chunk, padding=True, truncation=True, max_length=64,
                                return_tensors="pt")
            hidden = model(**encoded).last_hidden_state
            mask = encoded["attention_mask"].unsqueeze(-1).float()
            pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
            pooled = torch.nn.functional.normalize(pooled, dim=-1)
            for label, vec in zip(chunk, pooled):
                vectors[label] = [round(float(x), 4) for x in vec]
    return vectors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--limit", type=int, default=800)
    args = parser.parse_args(argv)

    labels = ledger_labels(args.limit)
    if not labels:
        print("no concepts in the ledger — nothing to embed")
        return 1
    started = time.time()
    vectors = embed(labels, args.model)
    payload = {
        "model": args.model,
        "dim": len(next(iter(vectors.values()))),
        "built_at": int(time.time()),
        "vectors": vectors,
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload) + "\n")
    print(f"{len(vectors)} concepts · dim {payload['dim']} · {time.time() - started:.1f}s")
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
