"""Does a state move the list more than simply asking again?

The only comparison that answers that question keeps the model fixed and changes one
thing at a time:

    re-ask    straight list (seed i) vs straight list (seed j), same model, same brief
    state     state list (seed i) vs that same seed's straight list

Both are scored the same way: for each idea in one list, the best embedding match in
the other, averaged. If the state figure sits below every re-ask figure, the state did
something asking twice does not do.

Usage: python floor.py [--task food-waste-city]
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path

import overlap as ov

HERE = Path(__file__).resolve().parent


def straight_lists(model: str, task: str, cells: dict) -> dict:
    seeds: dict = {}
    for (m, t, s, cond), cell in cells.items():
        if m == model and t == task and cond == "N":
            seeds[s] = cell["ideas"]
    slug = model.replace("/", "-").replace(".", "-").replace(":", "-")
    for path in HERE.glob(f"variation-{slug}-n*.json"):
        payload = json.loads(path.read_text())
        n = payload["count"]
        for lst in payload["lists"]:
            if len(lst["ideas"]) >= n // 2:
                seeds.setdefault(lst["seed"], lst["ideas"])
    return seeds


def run(task: str) -> str:
    cells = ov.load_cells()
    models = sorted({m for m, _t, _s, _c in cells if m in ov.SHORT})
    rows, lines = [], []

    for model in models:
        seeds = straight_lists(model, task, cells)
        keys = sorted(seeds)
        if len(keys) < 2:
            continue
        emb = {s: ov.bo.embed(seeds[s]) for s in keys}
        reask = [ov.mean_nn(emb[a], emb[b])
                 for i, a in enumerate(keys) for b in keys[i + 1:]]
        row = {"model": ov.SHORT[model], "reask": st.mean(reask),
               "reask_min": min(reask), "reask_max": max(reask), "states": {}}
        for cond in ("walk", "daydream", "doomscroll"):
            vals = []
            for s in keys:
                cell = cells.get((model, task, s, cond))
                if cell and len(cell["ideas"]) >= 10:
                    vals.append(ov.mean_nn(ov.bo.embed(cell["ideas"]), emb[s]))
            row["states"][cond] = st.mean(vals) if vals else None
        rows.append(row)

    lines += ["# With a state vs without, against the no-state baseline", "",
              f"Brief: {task}. Same model, same brief, four conditions. **No state** = one plain "
              "list scored against another plain list from the same model — what the model does "
              "when nothing is done to it. The three state columns score the state's list against "
              "the plain list from the same seed. Score is the average best embedding match: "
              "higher = more of the same ideas, lower = further away.", "",
              "| model | no state (two lists) | walk | daydream | doomscroll |", "|---|---|---|---|---|"]

    def fmt(v):
        return "—" if v is None else f"{v:.3f}"

    for r in rows:
        cells_txt = []
        for cond in ("walk", "daydream", "doomscroll"):
            v = r["states"][cond]
            mark = ""
            if v is not None:
                mark = " **below**" if v < r["reask_min"] else ""
            cells_txt.append(fmt(v) + mark)
        lines.append(f"| {r['model']} | {r['reask']:.3f} (floor {r['reask_min']:.3f}) | "
                     + " | ".join(cells_txt) + " |")

    lines += ["", "**below** = under the lowest no-state value for that model, i.e. further from "
                  "its own plain list than two plain lists ever are from each other.", ""]

    def verdict(cond: str) -> str:
        checked = [r for r in rows if r["states"][cond] is not None]
        hits = [r for r in checked if r["states"][cond] < r["reask_min"]]
        return f"{len(hits)} of {len(checked)}"

    lines += ["## Verdict", "",
              f"- daydream clears the floor on **{verdict('daydream')}** models",
              f"- walk clears it on **{verdict('walk')}**",
              f"- doomscroll clears it on **{verdict('doomscroll')}**", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="food-waste-city")
    a = ap.parse_args()
    text = run(a.task)
    (HERE / "floor.md").write_text(text)
    print(text)
