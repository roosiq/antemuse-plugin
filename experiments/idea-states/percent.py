"""Percent-change view: paired, per model, in plain language.

For every block (model × brief × seed) take the state cell minus the straight
cell, divide by the straight cell, and average over blocks. That keeps the
comparison inside the same model, brief and seed, so the percent is not carrying
a difference in task difficulty.

Reads every results-*.json in the folder, including the logprob runs.
"""
from __future__ import annotations

import glob
import json
import re
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent

SHORT = {"deepseek/deepseek-v4.1-flash-1017": "deepseek-v4.1",
         "qwen/qwen3.8-max-prime": "qwen3.8-max",
         "minimax/minimax-m3.1-flash": "minimax-m3.1",
         "moonshotai/kimi-k3.1-pro": "kimi-k3.1",
         "openai/gpt-6.1-terra": "gpt-6.1-terra"}

METRICS = [("n_parsed", "ideas", 1),
           ("distinctiveness", "different ideas", 0),
           ("in_ppl", "unusual wording", 0),
           ("in_ttr", "word variety", 1)]


def load() -> dict:
    out: dict = {}
    for path in glob.glob(str(HERE / "results-*.json")):
        try:
            d = json.loads(Path(path).read_text())
        except json.JSONDecodeError:
            continue
        cells = d.get("cells") or (d.get("stats") or {}).get("cells") or []
        model = d.get("model") or (cells[0]["model"] if cells else None)
        if not model:
            continue
        out.setdefault(model, []).extend(cells)
    return out


def blocks(cells: list[dict]) -> dict:
    out: dict = {}
    for c in cells:
        if c.get("n_parsed", 0) == 0:
            continue
        out.setdefault((c["task"], c["seed"]), {})[c["condition"]] = c
    return out


def pct(bl: dict, cond: str, metric: str) -> tuple[float, int] | None:
    vals = []
    for _k, v in bl.items():
        base, cell = v.get("N"), v.get(cond)
        if not base or not cell:
            continue
        b, s = base.get(metric), cell.get(metric)
        if b and s is not None and b != 0:
            vals.append((s - b) / b * 100)
    if not vals:
        return None
    # idea counts are near-constant inside a cell, so a mean carries the overrun
    # that a median would round away; every other measure uses the median
    centre = st.mean(vals) if metric == "n_parsed" else st.median(vals)
    return centre, len(vals)


def render(data: dict) -> str:
    lines = ["# What changes after a state, in percent", "",
             "Each number compares the list to the same model's plain list for the same brief, "
             "same seed. Positive means more. A dash means that model produced nothing usable "
             "for that condition.", ""]
    for model, cells in sorted(data.items()):
        bl = blocks(cells)
        if not bl:
            continue
        lines += [f"## {SHORT.get(model, model)}", "",
                  "| after a | ideas | different ideas | unusual wording | word variety |",
                  "|---|---|---|---|---|"]
        for cond in ("walk", "daydream", "doomscroll"):
            cellsrow = []
            for metric, _label, nd in METRICS:
                got = pct(bl, cond, metric)
                if got is None:
                    cellsrow.append("—")
                else:
                    m, n = got
                    cellsrow.append(f"{m:+.0f}%" if nd == 0 else f"{m:+.{nd}f}%")
            lines.append(f"| {cond} | " + " | ".join(cellsrow) + " |")
        lines.append("")
    lines += ["Reading it: more unusual wording with less word variety means the model reached "
              "for less ordinary words while using a narrower set of them. \"Different ideas\" is "
              "the only column that says the list went somewhere new. None of them say the ideas "
              "are better.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    text = render(load())
    (HERE / "percent.md").write_text(text)
    print(text)
