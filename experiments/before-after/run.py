"""Before/after demonstration for the Antemuse plugin.

Runs the plugin's own offline evaluation conditions against one model and renders a
readable comparison. This is a demonstration on two development tasks, not a
preregistered result and not evidence of a general creativity effect.

Conditions (from evaluation/run.py):
  A  baseline — "Answer the brief as you normally would."
  B  placebo — same call plus a matched-length "make it creative" instruction.
  D  Antemuse material — A's instruction plus a deterministic collider block.

A vs D answers "does the material change the output?"; B exists so the answer is not
confounded with simply asking for creativity.

Run with the breadth venv (numpy + sentence-transformers), from the plugin repo:

  env -u PYTHONPATH -u VIRTUAL_ENV HF_HUB_OFFLINE=1 \
    /home/ryan/breadth/.venv/bin/python experiments/before-after/run.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evaluation import run as harness  # noqa: E402

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache.jsonl"
JUDGE_CACHE = HERE / "judge-cache.json"
RESULTS = HERE / "results.json"
REPORT = HERE / "report.md"

TASKS_PATH = ROOT / "evaluation" / "tasks" / "development.json"
LOCAL = {"endpoint": "http://127.0.0.1:8090/v1", "model": "Qwen3.8 Flash Next",
         "extra": {"chat_template_kwargs": {"enable_thinking": False}}}
JUDGES = [
    {"name": "reflection/beam-1.0-501b", "model": "reflection/beam-1.0-501b-a23b:free"},
    {"name": "deepseek-v4.1-flash", "model": "deepseek/deepseek-v4.1-flash-1017"},
    {"name": "upstage/solar-mini4", "model": "upstage/solar-mini4:free"},
]
NOUS = "https://inference-api.nousresearch.com/v1"
SEEDS = [11, 12, 13]
CONDITIONS = ["A", "B", "D"]
CONDITION_LABEL = {"A": "baseline", "B": "placebo (creative instruction)", "D": "antemuse material"}


def _token() -> str | None:
    if os.environ.get("BREADTH_API_KEY"):
        return os.environ["BREADTH_API_KEY"]
    path = Path.home() / ".hermes" / "auth.json"
    if not path.exists():
        return None
    return json.loads(path.read_text()).get("providers", {}).get("nous", {}).get("access_token")


def _chat(endpoint: str, model: str, prompt: str, *, max_tokens: int = 900,
          temperature: float = 1.0, seed: int | None = None, extra: dict | None = None,
          attempts: int = 3, timeout: int = 240) -> str:
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature, "max_tokens": max_tokens}
    if seed is not None:
        body["seed"] = seed
    if extra:
        body.update(extra)
    headers = {"Content-Type": "application/json"}
    if not endpoint.startswith("http://127.0.0.1"):
        headers["Authorization"] = f"Bearer {_token()}"
    last = "empty content"
    for _ in range(attempts):
        req = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions",
                                     data=json.dumps(body).encode(), headers=headers)
        try:
            out = json.load(urllib.request.urlopen(req, timeout=timeout))
            msg = out["choices"][0]["message"]
            text = (msg.get("content") or "").strip()
            if text:
                return text
            last = "empty content" + (" (reasoning only)" if msg.get("reasoning_content") else "")
            body["max_tokens"] = min(int(body["max_tokens"]) * 3, 6000)
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
    raise RuntimeError(last)


MODEL = dict(LOCAL)
WORD_TARGET: int | None = None


def transport(req: dict) -> dict:
    """The plugin's transport contract: request dict in, text + usage out."""
    parts = [req["instruction"]]
    if req.get("material"):
        parts.append(req["material"])
    parts.append(req["brief"])
    if WORD_TARGET:
        parts.append(f"Write the paragraph in {WORD_TARGET - 10}-{WORD_TARGET + 10} words.")
    prompt = "\n\n".join(parts)
    text = _chat(MODEL["endpoint"], MODEL["model"], prompt, seed=req.get("seed"),
                 extra=MODEL.get("extra"))
    return {"text": text, "usage": {}}


# ---------------------------------------------------------------- metrics

_MODEL = None


def embed(texts: list[str]):
    from sentence_transformers import SentenceTransformer
    import numpy as np

    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return np.asarray(_MODEL.encode(texts, normalize_embeddings=True), dtype=float)


def pool_diversity(texts: list[str]) -> dict:
    import numpy as np

    if len(texts) < 2:
        return {"mean_pairwise": None}
    v = embed(texts)
    sim = v @ v.T
    iu = np.triu_indices(len(texts), k=1)
    d = (1.0 - sim)[iu]
    return {"mean_pairwise": round(float(d.mean()), 3),
            "max_pairwise": round(float(d.max()), 3),
            "min_pairwise": round(float(d.min()), 3)}


def distance_to_pool(texts: list[str], ref: list[str]) -> float | None:
    import numpy as np

    if not texts or not ref:
        return None
    a, b = embed(texts), embed(ref)
    return round(float((1.0 - a @ b.T).mean()), 3)


# ---------------------------------------------------------------- judging

JUDGE_PROMPT = """Two candidate paragraphs answer the same brief.

Brief:
{brief}

Candidate A:
<<<
{a}
>>>

Candidate B:
<<<
{b}
>>>

Which paragraph is more creative — more novel while still appropriate to the brief?
Ignore length and surface polish unless they change novelty or appropriateness.
Reply with JSON only: {{"choice": "A" or "B"}}"""


def _choice(raw: str) -> str | None:
    m = re.search(r'"choice"\s*:\s*"([AB])"', raw)
    return m.group(1) if m else None


def _load_judge_cache() -> dict:
    """Tolerant read: a half-written or doubled file must not kill a run."""
    if not JUDGE_CACHE.exists():
        return {}
    text = JUDGE_CACHE.read_text()
    decoder = json.JSONDecoder()
    best: dict = {}
    i = 0
    while i < len(text):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            break
        try:
            obj, i = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            break
        if isinstance(obj, dict) and len(obj) > len(best):
            best = obj
    return best


def _save_judge_cache(cache: dict) -> None:
    # unique temp name: two threads saving at once must not fight over one path
    tmp = JUDGE_CACHE.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_text(json.dumps(cache))
        os.replace(tmp, JUDGE_CACHE)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def judge_both_orders(model: str, brief: str, a: str, b: str) -> dict:
    first = _choice(_chat(NOUS, model, JUDGE_PROMPT.format(brief=brief, a=a, b=b),
                          temperature=0.0, max_tokens=500, attempts=2, timeout=90))
    second = _choice(_chat(NOUS, model, JUDGE_PROMPT.format(brief=brief, a=b, b=a),
                           temperature=0.0, max_tokens=500, attempts=2, timeout=90))
    flipped = {"A": "B", "B": "A", None: None}
    ok = first is not None and first == flipped[second]
    return {"choice": first if ok else None, "consistent": ok}


# ---------------------------------------------------------------- run

def run(seeds: list[int]) -> dict:
    tasks = json.loads(TASKS_PATH.read_text())["tasks"]
    records: dict[tuple[str, str, int], dict] = {}
    for task in tasks:
        for seed in seeds:
            for cond in CONDITIONS:
                rec = harness.run_condition(
                    cond, task, model=MODEL["model"],
                    prompt_version=f"before-after-1{'-w' + str(WORD_TARGET) if WORD_TARGET else ''}",
                    source_version="antemuse-local", seed=seed, transport=transport,
                    cache_path=CACHE)
                if rec["status"] != "ok":
                    print(f"  !! {cond} {task['id']} seed={seed}: {rec['status']} {rec.get('error')}",
                          file=sys.stderr)
                records[(task["id"], cond, seed)] = rec
                print(f"  {cond} {task['id']} seed={seed}: "
                      f"{len(rec['candidates'][0]['text'].split()) if rec['candidates'] else 0} words",
                      file=sys.stderr)
    return {"tasks": tasks, "records": records}


def analyse(data: dict) -> dict:
    tasks, records = data["tasks"], data["records"]
    seeds = sorted({k[2] for k in records})

    per_condition = {}
    for cond in CONDITIONS:
        texts = [records[(t["id"], cond, s)]["candidates"][0]["text"]
                 for t in tasks for s in seeds if (t["id"], cond, s) in records]
        entry = pool_diversity(texts)
        entry["n"] = len(texts)
        entry["mean_words"] = round(sum(len(t.split()) for t in texts) / len(texts), 1)
        per_condition[cond] = entry

    # A's outputs are the reference pool for "distance from baseline"
    a_texts = [records[(t["id"], "A", s)]["candidates"][0]["text"] for t in tasks for s in seeds]
    for cond in CONDITIONS:
        texts = [records[(t["id"], cond, s)]["candidates"][0]["text"] for t in tasks for s in seeds]
        per_condition[cond]["distance_to_baseline"] = distance_to_pool(texts, a_texts)

    # blind pairwise: A vs D and B vs D, both orders, two judges
    # a model never judges its own outputs; keep at least two other families
    judges = {j["name"]: j["model"] for j in JUDGES if j["model"] != MODEL["model"]}
    stats_judges = sorted(judges)
    jobs = []
    for t in tasks:
        for s in seeds:
            for left, right in (("A", "D"), ("B", "D")):
                a_text = records[(t["id"], left, s)]["candidates"][0]["text"]
                b_text = records[(t["id"], right, s)]["candidates"][0]["text"]
                for jname, jmodel in judges.items():
                    jobs.append((t["id"], t["brief"], s, left, right, jname, jmodel, a_text, b_text))

    lock = __import__("threading").Lock()

    def work(job):
        task_id, brief, seed, left, right, jname, jmodel, a_text, b_text = job
        key = f"{jname}|{MODEL['model']}|{task_id}|{seed}|{left}|{right}"
        with lock:
            verdict = _load_judge_cache().get(key)
        if verdict is None:
            try:
                verdict = judge_both_orders(jmodel, brief, a_text, b_text)
            except Exception as exc:  # noqa: BLE001
                print(f"  judge {jname} failed on {task_id}#{seed}: {exc}", file=sys.stderr)
                verdict = {"choice": None, "consistent": False}
            with lock:
                cache = _load_judge_cache()
                cache[key] = verdict
                _save_judge_cache(cache)
        winner = left if verdict["choice"] == "A" else (right if verdict["choice"] == "B" else None)
        print(f"  judge {left}v{right} {task_id}#{seed} {jname}: {winner}", file=sys.stderr)
        return {"task": task_id, "seed": seed, "left": left, "right": right,
                "judge": jname, "winner": winner, "consistent": verdict["consistent"]}

    with __import__("concurrent.futures").futures.ThreadPoolExecutor(max_workers=6) as pool:
        pairs = list(pool.map(work, jobs))

    winrates = {}
    for left, right in (("A", "D"), ("B", "D")):
        valid = [p for p in pairs if p["left"] == left and p["winner"]]
        wins = sum(1 for p in valid if p["winner"] == right)
        winrates[f"{right}_vs_{left}"] = {
            "wins": wins, "n": len(valid),
            "rate": round(wins / len(valid), 3) if valid else None}
    positional = sum(1 for p in pairs if not p["consistent"])
    return {"per_condition": per_condition, "pairs": pairs,
            "winrates": winrates, "positional_pairs": positional, "n_pairs": len(pairs),
            "seeds": seeds, "judges": stats_judges}


def render(data: dict, stats: dict) -> str:
    model = next(iter(data["records"].values()))["model"]
    target = f" Every condition is asked for {WORD_TARGET - 10}-{WORD_TARGET + 10} words." if WORD_TARGET else ""
    lines = ["# Antemuse — before / after", "",
             f"Two development tasks × 3 seeds × 3 conditions, one model (`{model}`), "
             f"identical token budget.{target}", "",
             "| condition | what changes | n | mean words | mean pairwise distance | distance to baseline |",
             "|---|---|---|---|---|---|"]
    for cond in CONDITIONS:
        e = stats["per_condition"][cond]
        lines.append(f"| {cond} — {CONDITION_LABEL[cond]} | "
                     f"{'nothing' if cond == 'A' else ('a creativity instruction' if cond == 'B' else 'deterministic collider block')} | "
                     f"{e['n']} | {e.get('mean_words')} | {e['mean_pairwise']} | {e.get('distance_to_baseline')} |")
    lines += ["", "## Blind pairwise (both orders, 2 judge families)", ""]
    for key, w in stats["winrates"].items():
        lines.append(f"- **{key}**: {w['wins']}/{w['n']} consistent decisions "
                     f"({w['rate']})")
    lines += [f"- positional (order-inconsistent) decisions: {stats['positional_pairs']}"
              f"/{stats['n_pairs']}",
              f"- judges: {', '.join(stats.get('judges', []))} (the model under test never judges itself)", ""]

    lines += ["## Example — same task, same seed", ""]
    task = data["tasks"][0]
    seed = stats["seeds"][0]
    for cond in ("A", "D"):
        rec = data["records"][(task["id"], cond, seed)]
        text = rec["candidates"][0]["text"] if rec["candidates"] else "(no output)"
        lines += [f"**{cond} — {CONDITION_LABEL[cond]}**", "", f"> {text}", ""]
    lines += ["## What this shows and does not show", "",
              "- It shows whether the material changes the three paragraphs this model writes, "
              "under a fixed budget, on two tasks.",
              "- It does not establish a general effect: n=6 per condition, one model, dev tasks.",
              "- Judges are order-controlled but not human-validated; treat win rates as directional.",
              "- Material-condition outputs are noticeably shorter; length is a plausible confound in both "
              "the diversity numbers and the win rates, and is reported in the table for that reason.",
              "- The plugin's preregistered state experiment "
              "(`experiments/state-settings/preregistration.md`) remains the evidence path; "
              "this page is the demonstration."]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--word-target", type=int, default=None,
                    help="force a length range on every condition so length cannot drive the result")
    ap.add_argument("--model", default="local",
                    help="'local' or a Nous model id (e.g. meituan/longcat-2.5:free)")
    args = ap.parse_args()
    global WORD_TARGET
    WORD_TARGET = args.word_target
    if args.model != "local":
        global RESULTS, REPORT
        MODEL.clear()
        MODEL.update({"endpoint": NOUS, "model": args.model})
        slug = re.sub(r"[^a-z0-9]+", "-", args.model.lower()).strip("-")
        suffix = f"-w{WORD_TARGET}" if WORD_TARGET else ""
        RESULTS = HERE / f"results-{slug}{suffix}.json"
        REPORT = HERE / f"report-{slug}{suffix}.md"

    if args.report_only and RESULTS.exists():
        payload = json.loads(RESULTS.read_text())
        stats = payload["stats"]
        tasks = json.loads(TASKS_PATH.read_text())["tasks"]
        records = {tuple(k.split("|")): v for k, v in payload["records"].items()}
        records = {(k[0], k[1], int(k[2])): v for k, v in records.items()}
        data = {"tasks": tasks, "records": records}
    else:
        data = run(args.seeds)
        stats = analyse(data)

    REPORT.write_text(render(data, stats))
    payload = {
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "stats": stats,
        "word_target": WORD_TARGET,
        "records": {f"{k[0]}|{k[1]}|{k[2]}": rec for k, rec in data["records"].items()},
    }
    RESULTS.write_text(json.dumps(payload, indent=1))
    print(f"wrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
