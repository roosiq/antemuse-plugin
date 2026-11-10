"""How much do different models produce the same ideas?

For one brief, one seed and one condition, every model wrote its own list of 50.
This asks whether those lists contain the same ideas.

Overlap is measured with the same embedding model used everywhere else: two ideas
count as the same when their cosine similarity is at least THRESHOLD. For each
model's list we report the share of its ideas that have a near-twin somewhere in
the other model's list, then average both directions.

Two baselines make the number readable:
  * inside one list — share of a model's own ideas that duplicate another idea in
    the same list, so you can see what a shared idea looks like at this threshold
  * unique pool — cluster every idea from every model at this threshold and count
    how many distinct ideas the whole set contains

Usage: python overlap.py [--threshold 0.80] [--seed 11]
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]

_spec = importlib.util.spec_from_file_location(
    "before_after", PLUGIN / "experiments" / "before-after" / "run.py")
bo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bo)

SHORT = {"deepseek/deepseek-v4.1-flash-1017": "DeepSeek v4.1",
         "qwen/qwen3.8-max-prime": "Qwen3.8 Max",
         "minimax/minimax-m3.1-flash": "MiniMax M3.1",
         "openai/gpt-6.1-terra": "GPT-6.1 Terra",
         "openai/gpt-6.1-sol": "GPT-6.1 Sol",
         "anthropic/claude-opus-5.5": "Opus 5.5",
         "moonshotai/kimi-k3.1-pro": "Kimi K3.1"}


def load_cells() -> dict:
    cells: dict = {}
    for path in glob.glob(str(HERE / "results-*.json")):
        try:
            d = json.loads(Path(path).read_text())
        except json.JSONDecodeError:
            continue
        for c in d.get("cells") or []:
            if c.get("n_parsed", 0) >= 10:
                cells[(c.get("model") or d.get("model"), c["task"], c["seed"], c["condition"])] = c
    return cells


def shared_share(a, b, thr: float) -> float:
    """Share of list a's ideas that have a near-twin in list b."""
    import numpy as np
    sim = a @ b.T
    return float((sim.max(axis=1) >= thr).mean())


def self_dupes(a, thr: float) -> float:
    import numpy as np
    sim = a @ a.T
    n = sim.shape[0]
    off = sim[~np.eye(n, dtype=bool)]
    # per idea: does it match some other idea in the same list
    return float(((sim - np.eye(n) * 2).max(axis=1) >= thr).mean())


def mean_nn(a, b) -> float:
    """Threshold-free: the average best match for each idea of a inside b."""
    return float((a @ b.T).max(axis=1).mean())


def pool_unique(texts: list[str], thr: float) -> int:
    import numpy as np
    if not texts:
        return 0
    e = bo.embed(texts)
    sim = e @ e.T
    n = len(texts)
    seen = [False] * n
    groups = 0
    for i in range(n):
        if seen[i]:
            continue
        groups += 1
        for j in range(i, n):
            if not seen[j] and sim[i, j] >= thr:
                seen[j] = True
    return groups


def sweep(cells: dict, models: list[str], tasks: list[str], seed: int) -> list[str]:
    """The overlap number moves a lot with the threshold, so show it moving."""
    out = ["## How the threshold changes the answer", "",
           "Share of ideas that match something in another model's list, no state, seed "
           f"{seed}.", "",
           "| brief | avg best match | 0.50 | 0.60 | 0.70 | 0.80 |", "|---|---|---|---|---|---|"]
    for task in tasks:
        group = {m: cells[(m, task, seed, "N")] for m in models if (m, task, seed, "N") in cells}
        if len(group) < 2:
            continue
        emb = {m: bo.embed(c["ideas"]) for m, c in group.items()}
        names = list(emb)
        nn = [mean_nn(emb[a], emb[b]) for i, a in enumerate(names) for b in names[i + 1:]]
        cols = []
        for thr in (0.5, 0.6, 0.7, 0.8):
            ps = [(shared_share(emb[a], emb[b], thr) + shared_share(emb[b], emb[a], thr)) / 2
                  for i, a in enumerate(names) for b in names[i + 1:]]
            cols.append(f"{st.mean(ps) * 100:.0f}%")
        out.append(f"| {task} | {st.mean(nn):.2f} | " + " | ".join(cols) + " |")
    out += ["", "0.80 counts only near-copies; 0.60 counts ideas that are the same move in "
                "different words. Read the direction, not the level.", ""]
    return out


def run(thr: float, seed: int) -> str:
    cells = load_cells()
    models = sorted({m for m, _t, _s, _c in cells if m in SHORT})
    tasks = sorted({t for _m, t, _s, _c in cells})
    lines = ["# Cross-model overlap of the idea lists", "",
             f"Two ideas count as the same when their embedding similarity is at least {thr:.2f}. "
             f"Measured on seed {seed}.", ""]

    for task in tasks:
        for cond in ("N", "walk", "daydream", "doomscroll"):
            group = {m: cells[(m, task, seed, cond)] for m in models if (m, task, seed, cond) in cells}
            if len(group) < 2:
                continue
            emb = {m: bo.embed(c["ideas"]) for m, c in group.items()}
            names = list(group)
            lines += [f"## {task} · {cond if cond != 'N' else 'no state'} · seed {seed}", "",
                      "Share of a model's ideas that also appear in another model's list:", "",
                      "| | " + " | ".join(SHORT[n] for n in names) + " |",
                      "|---" * (len(names) + 1) + "|"]
            for a in names:
                row = []
                for b in names:
                    if a == b:
                        row.append("—")
                    else:
                        s = (shared_share(emb[a], emb[b], thr) + shared_share(emb[b], emb[a], thr)) / 2
                        row.append(f"{s * 100:.0f}%")
                lines.append(f"| **{SHORT[a]}** | " + " | ".join(row) + " |")

            nn = [mean_nn(emb[a], emb[b]) for i, a in enumerate(names) for b in names[i + 1:]]
            pairs_sym = [(shared_share(emb[a], emb[b], thr) + shared_share(emb[b], emb[a], thr)) / 2
                         for i, a in enumerate(names) for b in names[i + 1:]]
            within = [self_dupes(emb[m], thr) for m in names]
            allideas = [i for m in names for i in group[m]["ideas"]]
            unique = pool_unique(allideas, thr)
            lines += ["",
                      f"- overlap between different models: **{st.mean(pairs_sym) * 100:.0f}%** "
                      f"(range {min(pairs_sym) * 100:.0f}–{max(pairs_sym) * 100:.0f}%)",
                      f"- average best match between different models: **{st.mean(nn):.2f}** similarity",
                      f"- overlap inside one model's own list: {st.mean(within) * 100:.0f}%",
                      f"- distinct ideas in the pooled {len(allideas)}: **{unique}** "
                      f"({unique / len(allideas) * 100:.0f}% unique)", ""]
    lines += sweep(cells, models, tasks, seed)
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.80)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()
    text = run(a.threshold, a.seed)
    (HERE / "overlap.md").write_text(text)
    print(text)
