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
    parts += ["", "Answer only in this state's own form. Do not list ideas yet."]
    text = bo._chat(bo.NOUS, bo.MODEL["model"], "\n".join(parts),
                    max_tokens=1200, seed=seed, attempts=2, timeout=180)
    return text.strip()


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
                cells.append({"task": task["id"], "brief": task["brief"], "seed": seed,
                              "condition": cond, "state_text": state_text, "text": text,
                              "ideas": ideas, "status": status, "truncated": truncated})
                print(f"  {task['id']}#{seed} {cond}: {len(ideas)} ideas ({status})",
                      file=sys.stderr)
    return {"model": model, "seeds": seeds, "cells": cells}


def analyse(payload: dict) -> dict:
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

    jobs = []
    for cell in cells:
        if len(cell["ideas"]) < 5:
            cell["novelty"] = cell["usefulness"] = None
            continue
        sample = ib.sample_ideas(cell["ideas"], cell["seed"])
        for j in ib.JUDGES:
            if j["model"] != payload["model"]:
                jobs.append((cell, j, sample))

    from concurrent.futures import ThreadPoolExecutor

    def work(job):
        cell, j, sample = job
        key = f"states|{j['name']}|{payload['model']}|{cell['task']}|{cell['seed']}|{cell['condition']}"
        cache = bo._load_judge_cache()
        verdict = cache.get(key)
        if verdict is None:
            try:
                verdict = ib.judge_sample(j["model"], cell["brief"], sample, cell["seed"])
            except Exception as exc:  # noqa: BLE001
                print(f"  judge {j['name']} failed: {exc}", file=sys.stderr)
                verdict = {"ok": False, "novelty": None, "usefulness": None}
            cache = bo._load_judge_cache()
            cache[key] = verdict
            bo._save_judge_cache(cache)
        return {"task": cell["task"], "seed": cell["seed"], "condition": cell["condition"],
                "judge": j["name"], **verdict}

    with ThreadPoolExecutor(max_workers=4) as pool:
        judged = list(pool.map(work, jobs))
    for c in cells:
        rows = [r for r in judged if r["task"] == c["task"] and r["seed"] == c["seed"]
                and r["condition"] == c["condition"] and r["ok"]]
        c["novelty"] = round(sum(r["novelty"] for r in rows) / len(rows), 2) if rows else None
        c["usefulness"] = round(sum(r["usefulness"] for r in rows) / len(rows), 2) if rows else None

    agg = {}
    for cond in CONDITIONS:
        cc = [c for c in cells if c["condition"] == cond]

        live = [c for c in cc if c["n_parsed"] > 0]

        def avg(k):
            v = [c[k] for c in live if c.get(k) is not None]
            return round(sum(v) / len(v), 3) if v else None
        agg[cond] = {"cells": len(cc), "ideas": avg("n_parsed"), "mean_pairwise": avg("mean_pairwise"),
                     "distinctiveness": avg("distinctiveness"), "novelty": avg("novelty"),
                     "usefulness": avg("usefulness"), "truncated": avg("truncated"),
                     "state_words": avg("state_words"), "mean_words": avg("mean_words"),
                     "failed": sum(1 for c in cc if c["n_parsed"] == 0)}
    return {"cells": cells, "aggregate": agg, "judged": judged}


def render(payload: dict, stats: dict) -> str:
    a = stats["aggregate"]
    lines = ["# 50 ideas, straight vs with a state in the middle", "",
             f"Two briefs × {len(payload['seeds'])} seed × {len(CONDITIONS)} conditions, model "
             f"`{payload['model']}`. In the state conditions the model holds the brief, answers a "
             "state turn, then returns to write the list.", "",
             "| condition | ideas / 50 | mean pairwise | distinctiveness | novelty | usefulness | state turn (words) |",
             "|---|---|---|---|---|---|---|"]
    for cond in CONDITIONS:
        e = a[cond]
        cells = "" if not e["failed"] else f" ({e['failed']}/{e['cells']} failed)"
        lines.append(f"| {LABEL[cond]} | {e['ideas']}{cells} | {e['mean_pairwise']} | "
                     f"{e['distinctiveness']} | {e['novelty']} | {e['usefulness']} | {e['state_words']} |")
    lines += ["", "Novelty and usefulness are a blind six-idea sample per cell, two judges that are "
                  "not the model under test. Truncated cells make the idea count unreliable; the "
                  "share is reported in the JSON.", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=[11])
    ap.add_argument("--tasks", nargs="*", default=[t["id"] for t in TASKS])
    ap.add_argument("--rejudge", action="store_true",
                    help="re-run only the judged sample on stored cells")
    args = ap.parse_args()
    slug = re.sub(r"[^a-z0-9]+", "-", args.model.lower()).strip("-")
    tasks = [t for t in TASKS if t["id"] in args.tasks]
    if args.rejudge:
        payload = json.loads((HERE / f"results-{slug}.json").read_text())
    else:
        payload = run(args.model, tasks, args.seeds)
    stats = analyse(payload)
    payload["stats"] = stats
    (HERE / f"results-{slug}.json").write_text(json.dumps(payload, indent=1))
    (HERE / f"report-{slug}.md").write_text(render(payload, stats))
    print(f"wrote {HERE / f'report-{slug}.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
