"""One table with every result.

Rows: model × condition (no state, walk, daydream, doomscroll). Columns: the four
measures this experiment has, plus the count and the distance from the plain list.

  ideas written     plain count, and change against the same model's plain list
  distinct concepts share of ideas written that are distinct concepts, two lists pooled
  different ideas   change in distance from the plain list, same brief and seed
  perplexity        change in how surprising the list is to a small fixed language model
  word variety      change in the share of distinct words
  distance          average best embedding match against the plain list, lower = further

No model judges another model anywhere in here.

Usage: python master.py
"""
from __future__ import annotations

import statistics as st

import concepts
import overlap as ov
import percent

CONDITIONS = (("N", "no state"), ("walk", "walk"), ("daydream", "daydream"),
              ("doomscroll", "doomscroll"))


def distance_to_plain(model: str, condition: str, cells: dict, task: str = "food-waste-city") -> float | None:
    seeds = concepts.straight_lists(model, task, cells, k=4)
    if len(seeds) < 2:
        return None
    plain = ov.bo.embed(seeds[0])
    if condition == "N":
        # the no-state figure is plain list against plain list, averaged over every pair
        emb = [ov.bo.embed(s) for s in seeds]
        pairs = [ov.mean_nn(emb[i], emb[j]) for i in range(len(emb)) for j in range(i + 1, len(emb))]
        return st.mean(pairs) if pairs else None
    vals = []
    for s in (11, 12):
        cell = cells.get((model, task, s, condition))
        if cell and len(cell["ideas"]) >= 10:
            vals.append(ov.mean_nn(ov.bo.embed(cell["ideas"]), plain))
    return st.mean(vals) if vals else None


def run() -> str:
    cells = ov.load_cells()
    for (m, task, seed, cond), cell in cells.items():
        cell.setdefault("model", m)
        cell.setdefault("task", task)
        cell.setdefault("seed", seed)
        cell.setdefault("condition", cond)
    models = sorted({m for m, _t, _s, _c in cells if m in ov.SHORT})
    bl = percent.blocks(list(cells.values()))
    lines = ["# Every result in one table", "",
             "Rows are model × condition. Changes are against that model's own plain list for the "
             "same brief and seed; 'different ideas', 'perplexity' and 'word variety' are median "
             "percent changes, 'distance' is an absolute score where lower means further away.", "",
             "| model | condition | ideas written | distinct concepts | different ideas | perplexity | word variety | distance |",
             "|---|---|---|---|---|---|---|---|"]

    for model in models:
        for cond, label in CONDITIONS:
            cs = [c for c in cells.values() if c["model"] == model and c["condition"] == cond
                  and c.get("n_parsed")]
            if not cs:
                lines.append(f"| {ov.SHORT[model]} | {label} | no list | — | — | — | — | — |")
                continue
            ideas = st.mean(c["n_parsed"] for c in cs)
            # distinct concepts, two lists pooled
            pools = concepts.straight_lists(model, "food-waste-city", cells) if cond == "N" else \
                [cells[(model, "food-waste-city", s, cond)]["ideas"] for s in (11, 12)
                 if (model, "food-waste-city", s, cond) in cells]
            if len(pools) >= 2:
                distinct, total = concepts.counts(pools)
                dc = f"{distinct / total * 100:.0f}%"
            else:
                dc = "—"
            if cond == "N":
                ideas_cell, dif, ppl, ttr = f"{ideas:.0f}", "0", "0", "0"
            else:
                m = percent.blocks([c for c in cells.values() if c["model"] == model])
                row = []
                for metric in ("n_parsed", "distinctiveness", "in_ppl", "in_ttr"):
                    got = percent.pct(m, cond, metric)
                    row.append(f"{got[0]:+.0f}%" if got else "—")
                ideas_cell = f"{ideas:.0f} ({row[0]})"
                dif, ppl, ttr = row[1], row[2], row[3]
            dist = distance_to_plain(model, cond, cells)
            lines.append(f"| {ov.SHORT[model]} | {label} | {ideas_cell} | {dc} | {dif} | {ppl} | "
                         f"{ttr} | {'—' if dist is None else f'{dist:.3f}'} |")

    lines += ["", "`distance` on the no-state row is one plain list against another plain list — the "
               "model's own spread. `distinct concepts` needs two lists, so Terra's state rows and "
               "Qwen's walk row have none.", ""]
    lines += ["## Cross-model agreement", "",
              "Same brief and seed, six lists compared with each other (`overlap.md`):", "",
              "| condition | ideas that match another model's | average best match | distinct in the pooled set |",
              "|---|---|---|---|"]
    for cond, label in CONDITIONS:
        emb = {}
        for model in models:
            cell = cells.get((model, "food-waste-city", 11, cond))
            if cell and len(cell["ideas"]) >= 10:
                emb[model] = ov.bo.embed(cell["ideas"])
        names = list(emb)
        if len(names) < 2:
            continue
        twins = [(ov.shared_share(emb[a], emb[b], 0.80) + ov.shared_share(emb[b], emb[a], 0.80)) / 2
                 for i, a in enumerate(names) for b in names[i + 1:]]
        nns = [ov.mean_nn(emb[a], emb[b]) for i, a in enumerate(names) for b in names[i + 1:]]
        allideas = [ide for m in names for ide in cells[(m, "food-waste-city", 11, cond)]["ideas"]]
        unique = ov.pool_unique(allideas, 0.80)
        lines.append(f"| {label} | {st.mean(twins) * 100:.0f}% | {st.mean(nns):.2f} | "
                     f"{unique} of {len(allideas)} ({unique / len(allideas) * 100:.0f}%) |")
    lines += ["", "Food waste brief, seed 11, the models that produced a list for that condition.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    text = run()
    (concepts.HERE / "master.md").write_text(text)
    print(text)
