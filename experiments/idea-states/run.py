"""Idea lists, twice: once straight, once with an agent state in the middle.

Each cell asks for 50 ideas. In the state conditions there is a turn in between:

    turn 1  the model is put in a state (walk / daydream / doomscroll) while
            holding the brief, and answers only in that state's own form
    turn 2  the model comes back and produces the 50 ideas

The state directives come from core/states.py, and doomscroll's feed from
core.sources.feed_pick, so this measures the shipped behaviour rather than a
paraphrase of it.

Measured on the list: how many ideas arrive, how far apart they are, how far
they sit from the other conditions' ideas, and a blind judged sample.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
sys.path.insert(0, str(PLUGIN))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bo = _load("before_after", PLUGIN / "experiments" / "before-after" / "run.py")
ib = _load("idea_burst", PLUGIN / "experiments" / "idea-burst" / "run.py")

import effects  # noqa: E402
import intrinsic  # noqa: E402

from core.states import STATES  # noqa: E402
from core import sources  # noqa: E402

CONDITIONS = ["N", "walk", "daydream", "doomscroll"]
LABEL = {"N": "straight", "walk": "walk", "daydream": "daydream", "doomscroll": "doomscroll"}
IDEAS = 50

TASKS = [
    {"id": "food-waste-city",
     "brief": f"List {IDEAS} distinct ideas for reducing food waste in a mid-size city. "
              "Number them 1 to 50. One sentence each."},
    {"id": "one-room-short-film",
     "brief": f"List {IDEAS} distinct ideas for a two-minute short film that can be shot "
              "in a single room with two actors. Number them 1 to 50. One sentence each."},
]

RETURN_PROMPT = """You are back from the state. What you carry out of it:

{state_text}

Now do the work you were holding. List {n} distinct ideas for this brief. Number them 1 to {n}. One sentence each.

{brief}"""


def state_turn(name: str, brief: str, seed: int) -> str:
    spec = STATES[name]
    parts = [spec["directive"], "", f"The brief you are holding: {brief}"]
    if name == "doomscroll":
        items = sources.feed_pick(3)
        if items:
            parts += ["", "The feed gives you:", *[f"- {i}" for i in items]]
    parts += ["", "Answer only in this state's own form, in under 80 words. "
                  "Do not list ideas yet."]
    # reasoning models can spend the whole window thinking and return nothing;
    # give the state turn room rather than silently recording an empty state
    for budget in (1200, 3000, 6000):
        try:
            text = bo._chat(bo.NOUS, bo.MODEL["model"], "\n".join(parts),
                            max_tokens=budget, seed=seed, attempts=1, timeout=180)
        except Exception as exc:  # noqa: BLE001
            print(f"  state turn {name}: {exc} at {budget}", file=sys.stderr)
            continue
        if text.strip():
            return text.strip()
    return ""


def run(model: str, tasks: list[dict], seeds: list[int]) -> dict:
    bo.MODEL.clear()
    bo.MODEL.update({"endpoint": bo.NOUS, "model": model})
    cells = []
    for task in tasks:
        for seed in seeds:
            for cond in CONDITIONS:
                state_text = ""
                try:
                    if cond != "N":
                        state_text = state_turn(cond, task["brief"], seed)
                        if not state_text:
                            raise RuntimeError("state turn produced nothing")
                        prompt = RETURN_PROMPT.format(state_text=state_text, n=IDEAS,
                                                      brief=task["brief"])
                    else:
                        prompt = task["brief"]
                    text = bo._chat(bo.NOUS, model, prompt, max_tokens=6000,
                                    seed=seed, attempts=2, timeout=300)
                    status = "ok" if text.strip() else "empty"
                except Exception as exc:  # noqa: BLE001
                    print(f"  {task['id']}#{seed} {cond}: {exc}", file=sys.stderr)
                    text, status = "", f"error: {type(exc).__name__}"
                ideas = ib.parse_ideas(text)
                truncated = len(ideas) < IDEAS or not text.rstrip().endswith((".", '"', "”"))
                cells.append({"model": model, "task": task["id"], "brief": task["brief"], "seed": seed,
                              "condition": cond, "state_text": state_text, "text": text,
                              "ideas": ideas, "status": status, "truncated": truncated})
                print(f"  {task['id']}#{seed} {cond}: {len(ideas)} ideas ({status})",
                      file=sys.stderr)
    return {"model": model, "seeds": seeds, "cells": cells}


def analyse(payload: dict) -> dict:
    """Deterministic measures only: counts, embedding geometry, text statistics.

    No model judges anything here. Every number is a function of the text and a
    fixed embedding or language model, so it reproduces exactly.
    """
    cells = payload["cells"]
    for cell in cells:
        ideas = cell["ideas"]
        reference = []
        for other in cells:
            if other is not cell and other["task"] == cell["task"]:
                reference.extend(other["ideas"])
        cell["n_parsed"] = len(ideas)
        cell["mean_pairwise"] = ib.mean_pairwise(ideas)
        cell["clusters"] = len(ib.semantic_clusters(ideas)) if len(ideas) > 1 else None
        cell["distinctiveness"] = ib.distinctiveness(ideas, reference)
        cell["mean_words"] = round(sum(len(i.split()) for i in ideas) / len(ideas), 1) if ideas else None
        cell["state_words"] = len(cell["state_text"].split())
        cell.pop("novelty", None)
        cell.pop("usefulness", None)

    agg = {}
    keys = ("n_parsed", "mean_pairwise", "distinctiveness", "state_words", "mean_words",
            "in_ppl", "in_surprisal", "in_ttr", "in_mtld", "in_distinct2", "in_hapax",
            "in_compression", "in_self_overlap", "self_nll")
    for cond in CONDITIONS:
        cc = [c for c in cells if c["condition"] == cond]
        live = [c for c in cc if c["n_parsed"] > 0]

        def avg(k, live=live):
            v = [c[k] for c in live if c.get(k) is not None]
            return round(sum(v) / len(v), 4) if v else None
        agg[cond] = {"cells": len(cc), **{k: avg(k) for k in keys},
                     "failed": sum(1 for c in cc if c["n_parsed"] == 0)}
    return {"cells": cells, "aggregate": agg}


def render(payload: dict, stats: dict) -> str:
    a = stats["aggregate"]
    lines = ["# 50 ideas, straight vs with a state in the middle", "",
             f"Two briefs x {len(payload['seeds'])} seed x {len(CONDITIONS)} conditions, model "
             f"`{payload['model']}`. In the state conditions the model holds the brief, answers a "
             "state turn, then returns to write the list.", "",
             "All columns are deterministic - same text, same number, no judge.", "",
             "| condition | ideas / 50 | different ideas | perplexity | word variety | state answer (words) |",
             "|---|---|---|---|---|---|"]
    for cond in CONDITIONS:
        e = a[cond]
        fail = "" if not e["failed"] else f" ({e['failed']}/{e['cells']} failed)"
        lines.append(f"| {LABEL[cond]} | {e['n_parsed']}{fail} | {e['distinctiveness']} | "
                     f"{e['in_ppl']} | {e['in_ttr']} | {e['state_words']} |")
    lines += ["", "Different ideas: average distance from the ideas the same model wrote for the "
                  "same brief without a state. Perplexity: how surprising the list is to a small "
                  "fixed language model, higher = less ordinary. Word variety: share of distinct "
                  "words. None of these say an idea is good.", ""]
    return "\n".join(lines)


def _read_results(path: Path) -> dict:
    """Read stored cells, tolerating a file that has an earlier document glued on."""
    text = path.read_text()
    decoder = json.JSONDecoder()
    best, i = None, 0
    while i < len(text):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            break
        try:
            obj, i = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            break
        if isinstance(obj, dict) and "cells" in obj:
            if best is None or len(obj["cells"]) >= len(best["cells"]):
                best = obj
    if best is None:
        raise SystemExit(f"{path} holds no readable result document")
    return best


def _write_results(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, indent=1))
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=[11])
    ap.add_argument("--tasks", nargs="*", default=[t["id"] for t in TASKS])
    ap.add_argument("--fresh", action="store_true",
                    help="discard stored cells instead of merging the new seeds into them")
    ap.add_argument("--intrinsic", action="store_true",
                    help="add deterministic text measures (perplexity, lexical diversity)")
    ap.add_argument("--reuse", action="store_true",
                    help="recompute measures on stored cells, no new generations")
    args = ap.parse_args()
    slug = re.sub(r"[^a-z0-9]+", "-", args.model.lower()).strip("-")
    tasks = [t for t in TASKS if t["id"] in args.tasks]
    path = HERE / f"results-{slug}.json"
    if args.reuse:
        payload = _read_results(path)
    else:
        payload = run(args.model, tasks, args.seeds)
        if path.exists() and not args.fresh:
            old = _read_results(path)
            seen = {(c["task"], c["seed"], c["condition"]) for c in payload["cells"]}
            payload["cells"] += [c for c in old["cells"]
                                 if (c["task"], c["seed"], c["condition"]) not in seen]
            payload["seeds"] = sorted({c["seed"] for c in payload["cells"]})
    stats = analyse(payload)
    payload["stats"] = stats
    if args.intrinsic:
        intrinsic.annotate(payload["stats"]["cells"])
    payload["stats"] = stats
    _write_results(path, payload)
    (HERE / f"report-{slug}.md").write_text(render(payload, stats))
    (HERE / f"math-{slug}.md").write_text(effects.render(payload))
    print(f"wrote {HERE / f'report-{slug}.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
