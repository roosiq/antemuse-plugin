"""Idea burst: 50 ideas for one brief, with and without Antemuse material.

The unit of measurement is the idea list, not a paragraph. Three conditions run
through the plugin's own request builder:

    A  the brief alone
    B  the brief plus a creative instruction (placebo)
    D  A plus the deterministic collider block

Outcomes, in order of how much I trust them:

    unique ideas          parsed, exact-deduped, then semantic clusters at 0.88
    diversity             mean pairwise embedding distance over the list
    distinctiveness       mean nearest-neighbour distance to other cells' ideas
    judged novelty        six sampled ideas rated blind by two non-self judges
    judged usefulness     same sample, second axis

Nothing here is human-validated. n is small by design: this shows whether an
effect exists, not how large it is.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "experiments" / "before-after"))

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "before_after", PLUGIN / "experiments" / "before-after" / "run.py")
bo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bo)  # reuse its chat client, embeddings and judge cache

CONDITIONS = ["A", "B", "D"]
LABEL = {"A": "baseline", "B": "placebo", "D": "antemuse material"}
# judges must reliably emit short JSON; minimax/qwen often reason until the window
# closes and return nothing, so the pool is models that were tested for it
JUDGES = [{"name": "deepseek-v4.1-flash", "model": "deepseek/deepseek-v4.1-flash-1017"},
          {"name": "longcat-2.5", "model": "meituan/longcat-2.5:free"},
          {"name": "solar-mini4", "model": "upstage/solar-mini4:free"}]
IDEAS = 50
SEMANTIC_DUP = 0.88
SAMPLE_JUDGED = 6

TASKS = [
    {"id": "food-waste-city",
     "brief": f"List {IDEAS} distinct ideas for reducing food waste in a mid-size city. "
              "Number them 1 to 50. One sentence each."},
    {"id": "one-room-short-film",
     "brief": f"List {IDEAS} distinct ideas for a two-minute short film that can be shot "
              f"in a single room with two actors. Number them 1 to 50. One sentence each."},
]

JUDGE_PROMPT = """Five ideas for the same brief are below, in random order and without labels.

Brief: {brief}

{ideas}

Rate each idea on two axes, from 1 to 5:
- novelty: how much it departs from the obvious first ideas for this brief
- usefulness: how plausible it is that this actually works or gets made

Judge the ideas on their content. Ignore length and writing style.

Return only JSON: [{{"id": 1, "novelty": n, "usefulness": n}}, ...] for all five."""
JUDGE_N = 5


def parse_ideas(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(?:\d{1,2}[.)]|[-*•]|\(?\d{1,2}\)?)\s*(.+)$", line)
        body = m.group(1) if m else line
        body = re.sub(r"\s+", " ", body).strip(" .;")
        if len(body.split()) < 3:
            continue
        out.append(body)
    return out


def semantic_clusters_at(texts: list[str], threshold: float) -> list[list[int]]:
    global SEMANTIC_DUP
    keep = SEMANTIC_DUP
    SEMANTIC_DUP = threshold
    try:
        return semantic_clusters(texts)
    finally:
        SEMANTIC_DUP = keep


def semantic_clusters(texts: list[str]) -> list[list[int]]:
    vecs = bo.embed(texts)
    vecs = [v / (sum(x * x for x in v) ** 0.5 or 1.0) for v in vecs]
    n = len(vecs)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if sum(a * b for a, b in zip(vecs[i], vecs[j])) >= SEMANTIC_DUP:
                parent[find(i)] = find(j)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def mean_pairwise(texts: list[str], limit: int = 400) -> float | None:
    if len(texts) < 2:
        return None
    vecs = bo.embed(texts)
    vecs = [v / (sum(x * x for x in v) ** 0.5 or 1.0) for v in vecs]
    pairs = [(i, j) for i in range(len(vecs)) for j in range(i + 1, len(vecs))]
    if len(pairs) > limit:
        pairs = random.Random(0).sample(pairs, limit)
    sims = [sum(a * b for a, b in zip(vecs[i], vecs[j])) for i, j in pairs]
    return round(1 - sum(sims) / len(sims), 3)


def distinctiveness(texts: list[str], reference: list[str]) -> float | None:
    if not texts or not reference:
        return None
    a = bo.embed(texts)
    b = bo.embed(reference)
    a = [v / (sum(x * x for x in v) ** 0.5 or 1.0) for v in a]
    b = [v / (sum(x * x for x in v) ** 0.5 or 1.0) for v in b]
    d = []
    for v in a:
        best = max(sum(x * y for x, y in zip(v, w)) for w in b)
        d.append(1 - best)
    return round(sum(d) / len(d), 3)


def entropy(sizes: list[int]) -> float:
    import math
    total = sum(sizes)
    if total == 0:
        return 0.0
    return round(-sum((s / total) * math.log(s / total + 1e-12) for s in sizes), 3)


def sample_ideas(ideas: list[str], seed: int, k: int = SAMPLE_JUDGED) -> list[str]:
    rng = random.Random(f"{seed}-{len(ideas)}")
    pool = list(ideas)
    rng.shuffle(pool)
    return pool[:k]


def judge_sample(model: str, brief: str, ideas: list[str], seed: int) -> dict:
    order = list(range(len(ideas)))
    random.Random(f"j{seed}").shuffle(order)
    shown = [ideas[i] for i in order]
    body = "\n".join(f"{n + 1}. {t}" for n, t in enumerate(shown))
    raw = bo._chat(bo.NOUS, model, JUDGE_PROMPT.format(brief=brief, ideas=body),
                   temperature=0.0, max_tokens=500, attempts=2, timeout=90)
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return {"ok": False, "novelty": None, "usefulness": None}
    try:
        rows = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"ok": False, "novelty": None, "usefulness": None}
    nov = [r.get("novelty") for r in rows if isinstance(r.get("novelty"), (int, float))]
    use = [r.get("usefulness") for r in rows if isinstance(r.get("usefulness"), (int, float))]
    if not nov or not use:
        return {"ok": False, "novelty": None, "usefulness": None}
    return {"ok": True, "novelty": round(sum(nov) / len(nov), 2),
            "usefulness": round(sum(use) / len(use), 2), "scored": len(rows)}


def run(model: str, tasks: list[dict], seeds: list[int]) -> dict:
    bo.MODEL.clear()
    bo.MODEL.update({"endpoint": bo.NOUS, "model": model})
    bo.WORD_TARGET = None
    cells = []
    for task in tasks:
        for seed in seeds:
            for cond in CONDITIONS:
                material = None
                if cond == "D":
                    from evaluation.run import deterministic_material
                    material = deterministic_material(task["brief"], seed=seed)
                instruction = {"A": "Answer the brief as you normally would.",
                               "B": "Answer the brief as you normally would, but make the "
                                    "ideas as creative as you can.",
                               "D": "Answer the brief as you normally would."}[cond]
                parts = [instruction]
                if material:
                    parts.append(material["block"])
                parts.append(task["brief"])
                # 50 ideas plus a reasoning trace needs real headroom; a capped
                # completion silently turns "fewer ideas" into a fake finding
                try:
                    text = bo._chat(bo.NOUS, model, "\n\n".join(parts), max_tokens=6000,
                                    seed=seed, attempts=2, timeout=300)
                    status = "ok" if text.strip() else "empty"
                except Exception as exc:  # noqa: BLE001  one dead cell must not kill the run
                    print(f"  {task['id']}#{seed} {cond}: {exc}", file=sys.stderr)
                    text, status = "", f"error: {type(exc).__name__}"
                ideas = parse_ideas(text)
                truncated = len(ideas) < IDEAS or not text.rstrip().endswith((".", "\"", "”"))
                cells.append({"task": task["id"], "brief": task["brief"], "seed": seed,
                              "condition": cond, "text": text, "ideas": ideas,
                              "status": status, "truncated": truncated,
                              "sources": len(material["sources"]) if material else 0})
                print(f"  {task['id']}#{seed} {cond}: {len(ideas)} ideas ({status})",
                      file=sys.stderr)
    return {"model": model, "seeds": seeds, "cells": cells}


def analyse(payload: dict) -> dict:
    cells = payload["cells"]
    out = []
    for cell in cells:
        ideas = cell["ideas"]
        exact = list(dict.fromkeys(i.lower() for i in ideas))
        clusters = semantic_clusters(ideas) if len(ideas) > 1 else []
        reps = [ideas[c[0]] for c in clusters]
        reference = []
        for other in cells:
            if other is cell or other["task"] != cell["task"]:
                continue
            reference.extend(other["ideas"])
        stats = {
            "n_parsed": len(ideas),
            "n_exact": len(exact),
            "n_unique": len(clusters),
            "dup_rate": round(1 - len(clusters) / len(ideas), 3) if ideas else None,
            "mean_pairwise": mean_pairwise(ideas),
            "clusters": len(clusters),
            "clusters_075": len(semantic_clusters_at(ideas, 0.75)) if len(ideas) > 1 else None,
            "entropy": entropy([len(c) for c in clusters]),
            "mean_words": round(sum(len(i.split()) for i in ideas) / len(ideas), 1) if ideas else None,
            "distinctiveness": distinctiveness(ideas, reference),
            "sources": cell["sources"],
            "status": cell["status"],
        }
        cell.update(stats)
        cell["reps"] = reps[:40]
        out.append(cell)

    judged = []
    jobs = []
    for cell in out:
        sample = sample_ideas(cell["ideas"], cell["seed"])
        for j in JUDGES:
            if j["model"] == payload["model"]:
                continue
            jobs.append((cell, j, sample))

    def work(job):
        cell, j, sample = job
        key = f"{j['name']}|{payload['model']}|{cell['task']}|{cell['seed']}|{cell['condition']}"
        cache = bo._load_judge_cache()
        verdict = cache.get(key)
        if verdict is None:
            try:
                verdict = judge_sample(j["model"], cell["brief"], sample, cell["seed"])
            except Exception as exc:  # noqa: BLE001
                print(f"  judge {j['name']} failed: {exc}", file=sys.stderr)
                verdict = {"ok": False, "novelty": None, "usefulness": None}
            cache[key] = verdict
            bo._save_judge_cache(cache)
        return {"task": cell["task"], "seed": cell["seed"], "condition": cell["condition"],
                "judge": j["name"], **verdict}

    with ThreadPoolExecutor(max_workers=4) as pool:
        judged = list(pool.map(work, jobs))
    for c in out:
        rows = [r for r in judged if r["task"] == c["task"] and r["seed"] == c["seed"]
                and r["condition"] == c["condition"] and r["ok"]]
        c["novelty"] = round(sum(r["novelty"] for r in rows) / len(rows), 2) if rows else None
        c["usefulness"] = round(sum(r["usefulness"] for r in rows) / len(rows), 2) if rows else None
        c["judges_used"] = len(rows)

    agg = {}
    for cond in CONDITIONS:
        cc = [c for c in out if c["condition"] == cond]
        def avg(k):
            v = [c[k] for c in cc if c.get(k) is not None]
            return round(sum(v) / len(v), 3) if v else None
        agg[cond] = {"cells": len(cc), "ideas": avg("n_parsed"), "unique": avg("n_unique"),
                     "clusters_075": avg("clusters_075"),
                     "dup_rate": avg("dup_rate"), "mean_pairwise": avg("mean_pairwise"),
                     "entropy": avg("entropy"), "distinctiveness": avg("distinctiveness"),
                     "novelty": avg("novelty"), "usefulness": avg("usefulness"),
                     "truncated": avg("truncated"),
                     "mean_words": avg("mean_words")}
    return {"cells": out, "aggregate": agg, "judged": judged}


def render(payload: dict, stats: dict) -> str:
    a = stats["aggregate"]
    lines = ["# Idea burst — 50 ideas, with and without material", "",
             f"Two briefs × {len(payload['seeds'])} seeds × 3 conditions, model `{payload['model']}`. "
             "Each cell is one call returning a numbered list of 50 ideas.", "",
             "| condition | ideas | mean pairwise | distinctiveness | novelty | usefulness | truncated |",
             "|---|---|---|---|---|---|---|"]
    for cond in CONDITIONS:
        e = a[cond]
        lines.append(f"| {cond} — {LABEL[cond]} | {e['ideas']} | {e['mean_pairwise']} | "
                     f"{e['distinctiveness']} | {e['novelty']} | {e['usefulness']} | {e['truncated']} |")
    lines += ["", "Ideas = number parsed out of the 50 asked for; truncated = share of cells that fell short "
                  "or ended mid-sentence, which invalidates the quantity comparison for those cells. "
                  "Distinctiveness = mean distance to the nearest idea from the other conditions "
                  "on the same brief. Judged axes are a blind sample of six ideas per cell, "
                  "two judges, neither the model under test.", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=[11, 12])
    ap.add_argument("--tasks", nargs="*", default=[t["id"] for t in TASKS])
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()
    slug = re.sub(r"[^a-z0-9]+", "-", args.model.lower()).strip("-")
    out_path = HERE / f"results-{slug}.json"
    if args.report_only:
        payload = json.loads(out_path.read_text())
        stats = analyse(payload)
    else:
        tasks = [t for t in TASKS if t["id"] in args.tasks]
        payload = run(args.model, tasks, args.seeds)
        stats = analyse(payload)
        payload["stats"] = stats
        out_path.write_text(json.dumps(payload, indent=1))
    (HERE / f"report-{slug}.md").write_text(render(payload, stats))
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
