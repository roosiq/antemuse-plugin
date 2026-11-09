#!/usr/bin/env python3
"""Measure a dose deterministically: does item k still add a new concept?

    python3 tools/experiment_deterministic.py                  # every state, every dose
    python3 tools/experiment_deterministic.py --state walk --trials 400

No model, no tokens, no judgement. For a state, a dose and a trial:

    items      = sources.PROVIDERS[state](dose)      the material the state really serves
    concepts   = the head word of every arrow-headed segment
    novel      = concept not in this repository's own vocabulary (docs, code, specs)
    distinct   = concept not already served earlier in the same dose

The dose question the model lane cannot afford to answer — "is the sixth item worth
serving, or is it the fifth again?" — is answered here from the generator alone, at zero
cost and in seconds. Novelty is a property of the material, not of a mind: this lane can
choose a dose as a cost question, and it cannot claim the dose made anyone more creative.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))

from core import sources, states  # noqa: E402
from tools.experiment_outcome import BRACKET, GENERIC, WORD  # noqa: E402

DOSES = {"walk": (3, 6, 12), "daydream": (1, 2, 4), "doomscroll": (1, 3, 6),
         "dream": (1, 2, 4), "unstuck": (0, 1, 2)}
ARROWS = re.compile(r"→|->|↔|·")
OUT = ROOT / "experiments" / "state-settings" / "deterministic.json"


def corpus_vocab() -> set[str]:
    """The words this repository already uses about itself."""
    vocab: set[str] = set()
    for pattern in ("docs/*.md", "specs/**/*.md", "core/*.py", "tests/*.py", "README.md"):
        for path in ROOT.glob(pattern):
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            vocab.update(w.lower() for w in WORD.findall(text))
    return vocab


POS = re.compile(r"\((?:n|v|a|s|r)\)")


def concepts(line: str) -> list[str]:
    """Head words of the poles a delivered line names.

    A line is `pole (pos) → pole (pos) · relation · “gloss”`. The relation and the gloss
    are not concepts, and a state name in a seed marker is not one either, so when any
    segment carries a part of speech those segments are the poles and the rest is
    commentary. Lines without part-of-speech tags fall back to every segment.
    """
    clean = re.sub(r"“.*?”", " ", BRACKET.sub(" ", line or ""))
    segments = [s for s in ARROWS.split(clean) if s.strip()]
    tagged = [s for s in segments if POS.search(s)]
    use = tagged or segments
    out: list[str] = []
    for segment in use:
        words = [w.lower() for w in WORD.findall(segment)]
        words = [w for w in words if w not in GENERIC]
        if words:
            out.append(words[-1])
    return out


def distance(line: str) -> float | None:
    """WordNet path distance between the two poles of a delivered pair, when it is one."""
    clean = BRACKET.sub(" ", line or "")
    parts = [p for p in ARROWS.split(clean) if p.strip()]
    if len(parts) < 2:
        return None
    try:
        from nltk.corpus import wordnet as wn
        left, right = wn.synsets(concepts(parts[0])[-1]), wn.synsets(concepts(parts[1])[-1])
        if not left or not right:
            return None
        return float(left[0].path_similarity(right[0]) or 0.0)
    except Exception:
        return None


WALK_NAME = ""
FRESH_CACHE = False


def trial(state: str, dose: int, vocab: set[str]) -> dict:
    if state == "walk" and WALK_NAME:
        from core import walks
        items = list(walks.get(WALK_NAME).step(dose)) if dose else []
    else:
        if FRESH_CACHE and state == "doomscroll":
            # measure the source pool's variety, not the seen-set's memory of it
            try:
                from core import social
                social.CACHE.unlink()
            except Exception:
                pass
        provider = sources.PROVIDERS[state]
        items = list(provider(dose)) if dose else []
    seen: set[str] = set()
    per_position: list[dict] = []
    distances: list[float] = []
    for i, line in enumerate(items):
        got = concepts(line)
        novel = [c for c in got if c not in vocab]
        fresh = [c for c in got if c not in seen]
        seen.update(got)
        d = distance(line)
        if d is not None:
            distances.append(d)
        per_position.append({"novel": bool(novel), "fresh": bool(fresh),
                             "concepts": len(got)})
    return {"items": len(items), "positions": per_position, "distance": distances,
            "lines": [l for l in items]}


def summarise(state: str, dose: int, trials: int, vocab: set[str]) -> dict:
    rng = random.Random(f"{state}:{dose}")     # trial order only; the draws stay the system's
    runs = [trial(state, dose, vocab) for _ in range(trials)]
    del rng
    positions = defaultdict(lambda: {"novel": 0, "fresh": 0, "n": 0})
    for run in runs:
        for i, pos in enumerate(run["positions"]):
            cell = positions[i]
            cell["n"] += 1
            cell["novel"] += 1 if pos["novel"] else 0
            cell["fresh"] += 1 if pos["fresh"] else 0
    flat = [p for run in runs for p in run["positions"]]
    all_lines = [l for run in runs for l in run["lines"]]
    diversity = (len(set(all_lines)) / len(all_lines)) if all_lines else None
    distances = [d for run in runs for d in run["distance"]]
    return {
        "state": state,
        "dose": dose,
        "trials": trials,
        "served_per_trial": round(sum(r["items"] for r in runs) / max(1, len(runs)), 2),
        "novel_rate": (sum(1 for p in flat if p["novel"]) / len(flat)) if flat else None,
        "fresh_rate": (sum(1 for p in flat if p["fresh"]) / len(flat)) if flat else None,
        "by_position": {i + 1: {"novel": c["novel"] / c["n"], "fresh": c["fresh"] / c["n"],
                                "n": c["n"]}
                        for i, c in sorted(positions.items())},
        "mean_distance": (sum(distances) / len(distances)) if distances else None,
        # a templated generator can be news-free while every word in it is familiar; the
        # distinct-line ratio is what catches "the same sentence with a different noun"
        "diversity": diversity,
        "empty_trials": sum(1 for r in runs if r["items"] == 0),
    }


def wilson(hits: int, n: int) -> tuple[float, float, float]:
    if n == 0:
        return (0.0, 0.0, 0.0)
    z = 1.959963985
    p = hits / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", choices=sorted(DOSES))
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--walk", default="", help="measure a named walk (outer, vault, run3, orbit)")
    ap.add_argument("--fresh-cache", action="store_true",
                    help="doomscroll: drop the feed cache per trial, measuring source variety")
    ap.add_argument("--json", default=str(OUT))
    args = ap.parse_args()

    global WALK_NAME, FRESH_CACHE
    WALK_NAME, FRESH_CACHE = args.walk, args.fresh_cache
    vocab = corpus_vocab()
    chosen = [args.state] if args.state else sorted(DOSES)
    results = []
    for state in chosen:
        label = f" · walk {args.walk}" if args.walk and state == "walk" else ""
        print(f"\n{state}{label}  ·  corpus vocabulary: {len(vocab)} words")
        for dose in DOSES[state]:
            got = summarise(state, dose, args.trials, vocab)
            results.append(got)
            if got["novel_rate"] is None:
                print(f"  dose {dose:>2}: no material "
                      f"({'empty' if got['served_per_trial'] == 0 else 'unparsed'} trials)")
                continue
            trail = " ".join(f"{p:.0%}" for p in
                             [v["novel"] for v in got["by_position"].values()])
            print(f"  dose {dose:>2}: served {got['served_per_trial']:>4} · "
                  f"novel {got['novel_rate']:>5.0%} · fresh {got['fresh_rate']:>5.0%} · "
                  f"by position [{trail}] · "
                  f"distinct lines {got['diversity']:.0%}" if got["diversity"] is not None else "")

    path = Path(args.json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n")
    print(f"\nwrote {path.relative_to(ROOT)} · {len(results)} cells · "
          f"{args.trials} trials each · no model calls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
