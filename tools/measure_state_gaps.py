#!/usr/bin/env python3
"""Measure the three moves that had no number after they were built.

    python3 tools/measure_state_gaps.py

No model, no tokens. Three questions the spec asks and the code had not answered:

walk     does the ledger stop a walk repeating itself across sessions?
dream    how often is a connection real, and how often is it the labelled fallback?
unstuck  is the direction specific, or is it a sentence that could have been said anywhere?

Each answer is a fraction with its denominator printed, so a number that comes back bad is
visible as bad rather than averaged away.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TRIALS = 100
DOSE = 6


def walk_repeat_rate(trials: int = TRIALS, dose: int = DOSE, steer: bool = True) -> dict:
    """Two sessions of the same walk. How often does session B land where A already went?

    `steer=False` disables the ledger's influence on selection, which is the control: without
    it the number would say "the ledger helps" with nothing behind the claim.
    """
    from core import history, walks

    spec = dict(walks.BUILTIN["outer"], name="outer")
    seen_a, repeated, steps = set(), 0, 0

    with tempfile.TemporaryDirectory() as home:
        os.environ["ANTEMUSE_STATES_HOME"] = home
        os.environ.pop("ANTEMUSE_NO_SCAN", None)
        for trial in range(trials):
            w = walks.GraphWalk(spec, Path(home) / f"a{trial}.json")
            for line in w.step(dose):
                label = _destination(line)
                if label:
                    seen_a.add(history.identify(label)[1] if history.identify(label) else label)
        if not steer:
            history.known = lambda term, exclude_session="": False  # type: ignore[assignment]
        for trial in range(trials):
            w = walks.GraphWalk(spec, Path(home) / f"b{trial}.json")
            for line in w.step(dose):
                label = _destination(line)
                if not label:
                    continue
                key = history.identify(label)[1] if history.identify(label) else label
                steps += 1
                if key in seen_a:
                    repeated += 1
        stats = history.stats()
    return {"repeated": repeated, "steps": steps, "steering": steer,
            "rate": round(repeated / steps, 3) if steps else None,
            "concepts_in_ledger": stats["concepts"],
            "sessions": 2, "trials": trials, "dose": dose}


def _arrow_labels(line: str) -> list:
    """The concepts a walk line moves between: `a (n) → b (n)` or `a → b → c` (ran)."""
    body = line.split("·")[0]
    out = []
    for part in body.split("→"):
        part = part.strip()
        if not part:
            continue
        part = part.split("(")[0].strip()
        if part:
            out.append(part)
    return out


def _destination(line: str) -> str:
    """Where a step actually took the walk — the right-hand end of its arrows."""
    labels = _arrow_labels(line)
    return labels[-1] if labels else ""


def dream_connection_hit_rate(trials: int = 20, steps: int = 2) -> dict:
    """Real connections vs the labelled fallback, on the day's actual commits."""
    from core import sources

    real = fallback = invented = 0
    examples = []
    for _ in range(trials):
        for line in sources.day_connections(steps):
            if line.startswith("connection"):
                real += 1
                if len(examples) < 3:
                    examples.append(line[:150])
            elif line.startswith("no connection today"):
                fallback += 1
            elif line.startswith("inventing instead"):
                invented += 1
    total = real + fallback + invented
    return {"real": real, "no_connection": fallback, "invented": invented,
            "rate": round(real / total, 3) if total else None,
            "trials": trials, "steps": steps, "examples": examples}


def unstuck_specificity(trials: int = TRIALS) -> dict:
    """A direction is specific when its evidence names something this repo actually has —
    a commit, a file, a graph neighbour, the ledger — not a sentence that fits any repo."""
    from core import sources

    firsts, with_evidence = [], 0
    for _ in range(trials):
        lines = sources.unstuck_text(1)
        # line 0 is `starts from seed=…`; the direction is the line that says `direction`
        line = next((l for l in lines if l.startswith("direction")), "")
        if not line:
            continue
        firsts.append(line.split("·", 1)[1].strip()[:70] if "·" in line else line[:70])
        rest = " ".join(lines).lower()
        if any(tok in rest for tok in ("commit", "file", ".py", ".md", "graph", "history",
                                       "memory", "spec")):
            with_evidence += 1
    distinct = len(set(firsts))
    return {"trials": len(firsts), "with_evidence": with_evidence,
            "evidence_rate": round(with_evidence / len(firsts), 3) if firsts else None,
            "distinct_directions": distinct,
            "distinct_rate": round(distinct / len(firsts), 3) if firsts else None,
            "sample": firsts[:4]}


def main() -> int:
    out = {}
    started = time.time()
    out["walk"] = walk_repeat_rate()
    out["walk_without_steering"] = walk_repeat_rate(steer=False)
    out["dream"] = dream_connection_hit_rate()
    out["unstuck"] = unstuck_specificity()
    print(json.dumps(out, indent=2, sort_keys=True))
    print(f"\n{time.time() - started:.1f}s")
    dest = ROOT / "experiments" / "state-settings" / "gaps.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
