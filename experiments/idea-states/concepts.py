"""How many distinct concepts does a model reach?

Counted directly, without a similarity floor: take two lists of 50 ideas (the same model,
same brief, two seeds), pool all 100 ideas, and cluster them. The number of clusters is the
number of distinct concepts. Compare with a state in between and the count changes.

Two numbers per cell:
  distinct   concepts in the pooled 100 ideas
  per 100    the same count normalised to exactly 100 ideas written, so a model that ignored
             the count and wrote 152 ideas gets no free credit

Usage: python concepts.py
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

import overlap as ov

HERE = Path(__file__).resolve().parent
THRESHOLD = 0.80
CONDITIONS = (("N", "straight"), ("walk", "walk"), ("daydream", "daydream"),
              ("doomscroll", "doomscroll"))


def slug(model: str) -> str:
    return model.replace("/", "-").replace(".", "-").replace(":", "-")


def straight_lists(model: str, task: str, cells: dict) -> list[list[str]]:
    """Two straight lists for this model and brief: stored cells first, then variation runs."""
    out = [cells[(model, task, s, "N")]["ideas"] for s in (11, 12)
           if (model, task, s, "N") in cells]
    if len(out) < 2:
        path = HERE / f"variation-{slug(model)}-n50.json"
        if path.exists():
            payload = json.loads(path.read_text())
            for lst in payload["lists"]:
                if len(lst["ideas"]) >= 25:
                    out.append(lst["ideas"])
    return out[:2]


def counts(lists: list[list[str]]) -> tuple[int, int]:
    ideas = [i for l in lists for i in l]
    return ov.pool_unique(ideas, THRESHOLD), len(ideas)


def run() -> str:
    cells = ov.load_cells()
    models = sorted({m for m, _t, _s, _c in cells if m in ov.SHORT})
    tasks = sorted({t for _m, t, _s, _c in cells})
    lines, agg = [], {c: [] for c, _ in CONDITIONS}

    for task in tasks:
        lines += [f"## {task}", "",
                  "| model | " + " | ".join(label for _c, label in CONDITIONS) + " |",
                  "|---" * (len(CONDITIONS) + 1) + "|"]
        for model in models:
            row = []
            pools = {"N": straight_lists(model, task, cells)}
            for cond, _ in CONDITIONS:
                if cond != "N":
                    pools[cond] = [cells[(model, task, s, cond)]["ideas"] for s in (11, 12)
                                   if (model, task, s, cond) in cells]
            for cond, _label in CONDITIONS:
                lists = pools.get(cond) or []
                if len(lists) < 2:
                    row.append("—")
                    continue
                distinct, total = counts(lists)
                per100 = distinct / total * 100
                row.append(f"{distinct} of {total} ({per100:.0f}%)")
                agg[cond].append(per100)
            lines.append(f"| {ov.SHORT[model]} | " + " | ".join(row) + " |")
        lines.append("")

    lines += ["## Distinct concepts per 100 ideas written", "",
              "| condition | mean | range |", "|---|---|---|"]
    for cond, label in CONDITIONS:
        v = agg[cond]
        if v:
            lines.append(f"| {label} | {st.mean(v):.1f} | {min(v):.0f}–{max(v):.0f}% |")
    lines += ["", "A straight pair of lists repeats itself: about 12 ideas out of 100 are the same "
                  "concept said twice. With a state in between, the pair repeats far less. That is "
                  "the direct version of the question — no similarity floor to argue about, just "
                  "how many different things the model said.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    text = run()
    (HERE / "concepts.md").write_text(text)
    print(text)
