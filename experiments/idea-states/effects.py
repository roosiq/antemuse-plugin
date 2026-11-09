"""Effect sizes for the idea-states design.

Everything here is a paired difference inside one (model, brief, seed) block:
the state cell minus the straight cell of the same block. Blocks missing either
side are dropped, so n is reported next to every estimate.

Reported per metric and condition: mean delta, sd, dz (mean/sd), a 95% interval
from the t distribution, and an exact sign-flip permutation p (all 2^n sign
assignments, so no distributional assumption).
"""
from __future__ import annotations

import itertools
import math
import statistics as st
from typing import Iterable

METRICS = [("n_parsed", "ideas delivered"),
           ("distinctiveness", "distinctiveness (distance from other conditions)"),
           ("mean_pairwise", "diversity (mean pairwise distance)"),
           ("in_ppl", "perplexity (Qwen3-0.6B, lower = more predictable)"),
           ("in_surprisal", "surprisal per token (nats)"),
           ("in_ttr", "type-token ratio"),
           ("in_mtld", "MTLD lexical diversity"),
           ("in_distinct2", "distinct bigrams"),
           ("in_hapax", "hapax share"),
           ("in_compression", "compression ratio"),
           ("in_self_overlap", "self bigram overlap"),
           ("self_nll", "self NLL/token from own logprobs")]


def _t975(df: int) -> float:
    # two-sided 95% critical value; table for the small df this design produces
    table = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
             8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160,
             14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093,
             20: 2.086, 24: 2.064, 30: 2.042, 40: 2.021, 60: 2.000}
    if df in table:
        return table[df]
    return 1.96 if df > 60 else table[min(table, key=lambda k: abs(k - df))]


def _signflip_p(diffs: list[float]) -> float | None:
    n = len(diffs)
    if n == 0 or n > 16:
        return None
    observed = abs(sum(diffs) / n)
    hits = total = 0
    for signs in itertools.product((1, -1), repeat=n):
        total += 1
        if abs(sum(d * s for d, s in zip(diffs, signs)) / n) >= observed - 1e-12:
            hits += 1
    return round(hits / total, 4)


def blocks(cells: Iterable[dict], default_model: str = "") -> dict:
    out: dict = {}
    for c in cells:
        if c.get("n_parsed", 0) == 0:
            continue
        out.setdefault((c.get("model") or default_model, c["task"], c["seed"]), {})[c["condition"]] = c
    return out


def paired(blocks_: dict, metric: str, cond: str, model: str | None = None) -> list[float]:
    diffs = []
    for (m, _t, _s), v in blocks_.items():
        if model and m != model:
            continue
        base, cell = v.get("N"), v.get(cond)
        if base and cell and base.get(metric) is not None and cell.get(metric) is not None:
            diffs.append(cell[metric] - base[metric])
    return diffs


def summarise(diffs: list[float]) -> dict:
    n = len(diffs)
    if n == 0:
        return {"n": 0, "mean": 0.0, "sd": 0.0, "se": 0.0, "dz": 0.0, "ci": (0.0, 0.0), "p": None}
    mean = sum(diffs) / n
    sd = st.stdev(diffs) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n else 0.0
    crit = _t975(max(n - 1, 1))
    return {"n": n, "mean": round(mean, 3), "sd": round(sd, 3), "se": round(se, 3),
            "dz": round(mean / sd, 2) if sd else 0.0,
            "ci": (round(mean - crit * se, 3), round(mean + crit * se, 3)),
            "p": _signflip_p(diffs)}


def render(payload: dict) -> str:
    cells = payload["stats"]["cells"]
    bl = blocks(cells, payload.get("model", ""))
    models = sorted({m for m, _t, _s in bl})
    lines = ["# Idea states — the arithmetic", "",
             f"Blocks: {len(bl)} (model × brief × seed with a usable straight cell). "
             "Every number below is the paired difference state − straight inside a block.", ""]

    for cond in ("walk", "daydream", "doomscroll"):
        lines += [f"## {cond}", "",
                  "| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |",
                  "|---|---|---|---|---|---|---|"]
        for metric, label in METRICS:
            s = summarise(paired(bl, metric, cond))
            if not s["n"]:
                lines.append(f"| {label} | 0 | — | — | — | — | — |")
                continue
            ci = f"[{s['ci'][0]:+.3f}, {s['ci'][1]:+.3f}]"
            p = "—" if s["p"] is None else f"{s['p']:.3f}"
            lines.append(f"| {label} | {s['n']} | {s['mean']:+.3f} | {s['sd']:.3f} | "
                         f"{s['dz']:+.2f} | {ci} | {p} |")
        lines.append("")

    lines += ["## Per model", "",
              "| model | condition | Δ distinctiveness | Δ perplexity | Δ ideas | n |",
              "|---|---|---|---|---|---|"]
    for m in models:
        for cond in ("walk", "daydream", "doomscroll"):
            a, b, c = (summarise(paired(bl, "distinctiveness", cond, m)),
                       summarise(paired(bl, "in_ppl", cond, m)),
                       summarise(paired(bl, "n_parsed", cond, m)))
            if not a["n"]:
                lines.append(f"| {m} | {cond} | — | — | — | 0 |")
                continue
            lines.append(f"| {m} | {cond} | {a['mean']:+.3f} | {b['mean']:+.1f} | "
                         f"{c['mean']:+.1f} | {a['n']} |")
    lines.append("")

    sd = summarise(paired(bl, "distinctiveness", "doomscroll")).get("sd") or 0.06
    lines += ["## What n would settle it", "",
              f"At the observed sd ({sd:.3f}) on distinctiveness, a 95% interval of ±0.02 needs "
              f"n ≈ {(1.96 * sd / 0.02) ** 2:.0f} blocks per condition. "
              f"Blocks here: {len(bl)}.", ""]
    return "\n".join(lines)
