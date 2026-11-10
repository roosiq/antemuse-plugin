"""How much does a straight list of 100 ideas vary on its own?

No state anywhere. Ask the same model for 100 ideas, four times, and compare the
four lists with each other — then compare each model against the others. That
gives the floor: how much a list moves when nothing was done to the model.

If a state's effect is smaller than this floor, the state effect is not
distinguishable from just asking again.

Usage: python variation.py --models ... --repeats 4 --count 100
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import statistics as st
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

import overlap as ov  # noqa: E402

MODELS = ["deepseek/deepseek-v4.1-flash-1017", "qwen/qwen3.8-max-prime",
          "minimax/minimax-m3.1-flash", "openai/gpt-6.1-terra",
          "openai/gpt-6.1-sol", "anthropic/claude-opus-5.5"]
THRESHOLD = 0.80

BRIEF = ("List {n} distinct ideas for reducing food waste in a mid-size city. "
         "Number them 1 to {n}. One sentence each.")


def slug(model: str) -> str:
    return model.replace("/", "-").replace(".", "-").replace(":", "-")


def generate(model: str, n: int, repeats: int) -> dict:
    bo.MODEL.clear()
    bo.MODEL.update({"endpoint": bo.NOUS, "model": model})
    lists = []
    for seed in range(11, 11 + repeats):
        prompt = BRIEF.format(n=n)
        try:
            text = bo._chat(bo.NOUS, model, prompt, max_tokens=12000, seed=seed,
                            attempts=2, timeout=420)
            status = "ok"
        except Exception as exc:  # noqa: BLE001
            print(f"  {model} seed {seed}: {exc}", file=sys.stderr)
            text, status = "", f"error: {type(exc).__name__}"
        ideas = ib.parse_ideas(text)
        lists.append({"seed": seed, "text": text, "ideas": ideas, "status": status})
        print(f"  {model} seed {seed}: {len(ideas)} ideas ({status})", file=sys.stderr)
    return {"model": model, "count": n, "repeats": repeats, "lists": lists}


def report(payload: dict) -> str:
    n = payload["count"]
    models = [m for m in payload["models"] if any(len(l["ideas"]) >= n // 2 for l in m["lists"])]
    lines = [f"# Straight lists of {n} ideas, asked {payload['repeats']} times", "",
             "No state. Two ideas count as the same at embedding similarity "
             f"{THRESHOLD:.2f}. 'Twin' = share of a list's ideas that reappear in the other list.",
             ""]

    lines += ["## Same model, asked again", "",
              "| model | lists | twin ideas | avg best match | distinct in the pooled set |",
              "|---|---|---|---|---|"]
    within_nn, within_twin = [], []
    for m in models:
        usable = [l for l in m["lists"] if len(l["ideas"]) >= n // 2]
        emb = [bo.embed(l["ideas"]) for l in usable]
        twins, nns = [], []
        for i in range(len(emb)):
            for j in range(i + 1, len(emb)):
                twins.append((ov.shared_share(emb[i], emb[j], THRESHOLD)
                              + ov.shared_share(emb[j], emb[i], THRESHOLD)) / 2)
                nns.append(ov.mean_nn(emb[i], emb[j]))
        allideas = [idea for l in usable for idea in l["ideas"]]
        unique = ov.pool_unique(allideas, THRESHOLD)
        within_nn.append(st.mean(nns))
        within_twin.append(st.mean(twins))
        lines.append(f"| {ov.SHORT.get(m['model'], m['model'])} | {len(usable)} | "
                     f"{st.mean(twins) * 100:.0f}% | {st.mean(nns):.2f} | "
                     f"{unique} of {len(allideas)} ({unique / len(allideas) * 100:.0f}%) |")
    lines += ["", f"Average across models: **{st.mean(within_twin) * 100:.0f}% of ideas are "
                  f"twins when the same model is asked again**, best match {st.mean(within_nn):.2f}.", ""]

    lines += ["## Different models, asked once each", "",
              "| | " + " | ".join(ov.SHORT.get(m["model"], m["model"])[:9] for m in models) + " |",
              "|---" * (len(models) + 1) + "|"]
    emb = {m["model"]: bo.embed([l for l in m["lists"] if len(l["ideas"]) >= n // 2][0]["ideas"])
           for m in models}
    names = [m["model"] for m in models]
    for a in names:
        row = []
        for b in names:
            if a == b:
                row.append("—")
            else:
                row.append(f"{(ov.shared_share(emb[a], emb[b], THRESHOLD) + ov.shared_share(emb[b], emb[a], THRESHOLD)) / 2 * 100:.0f}%")
        lines.append(f"| **{ov.SHORT.get(a, a)}** | " + " | ".join(row) + " |")
    cross = [(ov.shared_share(emb[a], emb[b], THRESHOLD) + ov.shared_share(emb[b], emb[a], THRESHOLD)) / 2
             for i, a in enumerate(names) for b in names[i + 1:]]
    cross_nn = [ov.mean_nn(emb[a], emb[b]) for i, a in enumerate(names) for b in names[i + 1:]]
    lines += ["", f"Across models: **{st.mean(cross) * 100:.0f}% twins**, best match "
                  f"{st.mean(cross_nn):.2f}.", ""]

    lines += ["## Reading it", "",
              f"Re-asking the same model reproduces {st.mean(within_twin) * 100:.0f}% of its ideas; "
              f"a different model reproduces {st.mean(cross) * 100:.0f}%. Anything a state changes "
              "by less than the first number is inside the noise of simply asking twice.", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=MODELS)
    ap.add_argument("--repeats", type=int, default=4)
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args()

    results = []
    for model in a.models:
        path = HERE / f"variation-{slug(model)}.json"
        if a.report_only and path.exists():
            results.append(json.loads(path.read_text()))
            continue
        if path.exists():
            print(f"keeping {path.name}", file=sys.stderr)
            results.append(json.loads(path.read_text()))
            continue
        payload = generate(model, a.count, a.repeats)
        path.write_text(json.dumps(payload, indent=1))
        results.append(payload)

    text = report({"models": results, "count": a.count, "repeats": a.repeats})
    (HERE / "variation.md").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
