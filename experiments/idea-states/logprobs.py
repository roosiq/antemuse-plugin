"""Self-perplexity from the model's own logprobs.

The separate small LM measures "how predictable is this text to a bystander".
This measures how predictable the text was to the model that wrote it: every
token it emitted came back with a logprob, so the list carries its own
per-token negative log-likelihood. No second model, no scoring calls.

What it is: the mean surprisal of the model's own sample under its own
distribution at the sampling temperature. Lower means the model was on rails.

What it is not: a quality measure, and not comparable across models — each
model is normalised by itself. Use it inside one model, across conditions.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics as st
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
sys.path.insert(0, str(PLUGIN))

import importlib.util


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ib = _load("idea_burst", PLUGIN / "experiments" / "idea-burst" / "run.py")
states = _load("states_run", HERE / "run.py")

TOKENS = {}


def _token() -> str | None:
    d = json.load(open(os.path.expanduser("~/.hermes/auth.json")))
    return d["providers"]["nous"].get("access_token")


def chat_lp(model: str, prompt: str, *, max_tokens: int = 6000, seed: int | None = None,
            timeout: int = 300) -> dict:
    """One completion, keeping the per-token logprobs."""
    if "tok" not in TOKENS:
        TOKENS["tok"] = _token()
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "temperature": 1.0, "max_tokens": max_tokens, "logprobs": True, "top_logprobs": 1}
    if seed is not None:
        body["seed"] = seed
    req = urllib.request.Request(
        "https://inference-api.nousresearch.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKENS['tok']}"})
    out = json.load(urllib.request.urlopen(req, timeout=timeout))
    choice = out["choices"][0]
    content = choice["message"].get("content") or ""
    lp = (choice.get("logprobs") or {}).get("content") or []
    return {"text": content, "tokens": [(t["token"], float(t["logprob"])) for t in lp]}


def split_by_line(tokens: list[tuple[str, float]]) -> list[list[float]]:
    """Group token logprobs into lines; numbered lists put one idea per line."""
    lines: list[list[float]] = [[]]
    for tok, lp in tokens:
        if "\n" in tok:
            parts = tok.split("\n")
            lines[-1].append(lp)
            for _ in parts[1:]:
                lines.append([])
        else:
            lines[-1].append(lp)
    return [ln for ln in lines if len(ln) >= 4]


def run(model: str, seeds: list[int]) -> dict:
    states.bo.MODEL.clear()
    states.bo.MODEL.update({"endpoint": states.bo.NOUS, "model": model})
    cells = []
    for task in states.TASKS:
        for seed in seeds:
            for cond in states.CONDITIONS:
                state_text = ""
                try:
                    if cond != "N":
                        state_text = states.state_turn(cond, task["brief"], seed)
                        prompt = states.RETURN_PROMPT.format(state_text=state_text,
                                                             n=states.IDEAS, brief=task["brief"])
                    else:
                        prompt = task["brief"]
                    got = chat_lp(model, prompt, seed=seed)
                    text, toks = got["text"], got["tokens"]
                except Exception as exc:  # noqa: BLE001
                    print(f"  {task['id']}#{seed} {cond}: {exc}", file=sys.stderr)
                    text, toks = "", []
                ideas = ib.parse_ideas(text)
                lines = split_by_line(toks)
                nll = [sum(ln) / len(ln) for ln in lines]
                cells.append({"model": model, "task": task["id"], "brief": task["brief"],
                              "seed": seed, "condition": cond, "ideas": ideas,
                              "tokens": len(toks), "n_parsed": len(ideas),
                              "self_nll": round(sum(-x for x in nll) / len(nll), 3) if nll else None,
                              "self_ppl": round(math_exp(nll), 1) if nll else None,
                              "idea_nll_sd": round(st.pstdev([-x for x in nll]), 3) if len(nll) > 1 else None,
                              "state_words": len(state_text.split())})
                print(f"  {task['id']}#{seed} {cond}: {len(ideas)} ideas, "
                      f"nll {cells[-1]['self_nll']}", file=sys.stderr)
    return {"model": model, "seeds": seeds, "cells": cells}


def math_exp(nll: list[float]) -> float:
    import math
    return math.exp(sum(-x for x in nll) / len(nll))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=[11])
    args = ap.parse_args()
    slug = re.sub(r"[^a-z0-9]+", "-", args.model.lower()).strip("-")
    payload = run(args.model, args.seeds)
    (HERE / f"results-lp-{slug}.json").write_text(json.dumps(payload, indent=1))
    agg = {}
    for cond in states.CONDITIONS:
        cc = [c for c in payload["cells"] if c["condition"] == cond and c["self_nll"]]
        agg[cond] = {k: round(st.mean([c[k] for c in cc]), 3) if cc else None
                     for k in ("self_nll", "self_ppl", "idea_nll_sd", "n_parsed")}
    lines = ["# Self-perplexity from the model's own logprobs", "",
             f"Model `{args.model}`, {len(args.seeds)} seed × 2 briefs × 4 conditions. "
             "Per-token negative log-likelihood of the model's own output.", "",
             "| condition | ideas | mean NLL/token | self-perplexity | sd across ideas |",
             "|---|---|---|---|---|"]
    for cond in states.CONDITIONS:
        a = agg[cond]
        lines.append(f"| {states.LABEL[cond]} | {a['n_parsed']} | {a['self_nll']} | "
                     f"{a['self_ppl']} | {a['idea_nll_sd']} |")
    lines += ["", "Lower NLL means the model was more on rails. Not comparable across "
                  "models; compare conditions within a model.", ""]
    (HERE / f"report-lp-{slug}.md").write_text("\n".join(lines))
    print(f"wrote {HERE / f'report-lp-{slug}.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
