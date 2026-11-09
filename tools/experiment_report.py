#!/usr/bin/env python3
"""Report the experiment ledger: rates per arm, with intervals, and the honest caveat.

    python3 tools/experiment_report.py              # table for every state in the ledger
    python3 tools/experiment_report.py --state walk

A rate is a count of booleans. Nothing here is a model judgement, and nothing here is
called a result below the pre-registered 60-entries-per-arm floor: at that size the output
is labelled PILOT and the decision rule is not applied.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "experiments" / "state-settings" / "ledger.jsonl"
MIN_PER_ARM = 60
ARMS = ("half", "default", "double", "control")


def wilson(hits: int, n: int) -> tuple[float, float, float]:
    if n == 0:
        return (0.0, 0.0, 0.0)
    z = 1.959963985
    p = hits / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def summarise(entries: list[dict]) -> dict:
    kept = [r for r in entries if not r.get("excluded")]
    by = defaultdict(lambda: {"hits": 0, "n": 0})
    for r in kept:
        cell = by[r["arm"]]
        cell["n"] += 1
        cell["hits"] += 1 if r.get("outcome") else 0
    out = {}
    for arm in ARMS:
        if arm not in by:
            continue
        hits, n = by[arm]["hits"], by[arm]["n"]
        p, lo, hi = wilson(hits, n)
        out[arm] = {"hits": hits, "n": n, "rate": p, "lo": lo, "hi": hi}
    return out


def render(state: str, cells: dict, excluded: int) -> str:
    if not cells:
        return f"{state}: no kept entries"
    short = min(c["n"] for c in cells.values()) < MIN_PER_ARM
    head = f"{state}  " + ("· PILOT (below 60/arm: not a result, decision rule not applied)"
                           if short else "· main-run size")
    lines = [head, f"  {'arm':<9}{'hits':>5}{'n':>5}{'rate':>8}{'95% CI':>16}"]
    for arm, c in cells.items():
        lines.append(f"  {arm:<9}{c['hits']:>5}{c['n']:>5}"
                     f"{c['rate'] * 100:>7.0f}%   [{c['lo'] * 100:.0f}%, {c['hi'] * 100:.0f}%]")
    base = cells.get("default")
    ctrl = cells.get("control")
    if base and ctrl:
        diff = (base["rate"] - ctrl["rate"]) * 100
        lines.append(f"  default − control: {diff:+.0f} points "
                     f"(n={base['n']} vs {ctrl['n']}; intervals overlap until N is large)")
    if excluded:
        lines.append(f"  excluded: {excluded} (kept in the ledger, out of the rates)")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state")
    ap.add_argument("--ledger", default=str(LEDGER))
    args = ap.parse_args()
    entries = rows(Path(args.ledger))
    if not entries:
        print("ledger is empty: no sessions have run")
        return 0
    states = [args.state] if args.state else sorted({r["state"] for r in entries})
    for state in states:
        subset = [r for r in entries if r["state"] == state]
        print(render(state, summarise(subset), sum(1 for r in subset if r.get("excluded"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
