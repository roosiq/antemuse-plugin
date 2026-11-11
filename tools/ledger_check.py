#!/usr/bin/env python3
"""Check the state-settings experiment ledger before anyone analyses it.

The ledger is the only record the experiment trusts, so it is checked by a script that
has no opinion: every entry carries its assignment, its dose as delivered, and its
outcome — and a missing field fails the run rather than being filled in later.

    python3 tools/ledger_check.py                 # validate a state-settings ledger.jsonl (research tree, not published)
    python3 tools/ledger_check.py --summary       # counts per state/arm

Exit 1 on any violation. Predicted outcomes are refused: an outcome must be a boolean,
and `null` is allowed only for excluded entries with a stated reason.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "experiments" / "state-settings" / "ledger.jsonl"

ARMS = {"half", "default", "double", "control"}
STATES = {"walk", "daydream", "doomscroll", "dream", "unstuck"}
ENDINGS = {"complete", "returned", "expired", "abandoned"}
EXCLUSION_REASONS = {
    "hand-typed-state",
    "dose-not-delivered",
    "truncated-answer",
    "control-recent-state",
    "platform-failure",
    "outcome-definition-changed",
}

STRING_FIELDS = ("session_id", "model", "provider", "state", "arm", "ending_reason")
INT_FIELDS = ("block_seed", "dose", "ceiling_minutes", "turns", "seconds_to_dose",
              "tokens_in", "tokens_out", "tool_failures", "tool_blocks")
FLOAT_FIELDS = ("entered_at",)


def _is_bool(value) -> bool:
    return isinstance(value, bool)


def check_entry(n: int, row: dict) -> list[str]:
    errs: list[str] = []

    def need(field, ok, why):
        if field not in row:
            errs.append(f"line {n}: missing {field}")
        elif not ok(row[field]):
            errs.append(f"line {n}: {field}={row[field]!r} — {why}")

    for field in STRING_FIELDS:
        need(field, lambda v: isinstance(v, str) and v.strip(), "must be a non-empty string")
    for field in INT_FIELDS:
        need(field, lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0,
             "must be a non-negative integer")
    for field in FLOAT_FIELDS:
        need(field, lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
             "must be a number")

    if row.get("state") not in STATES:
        errs.append(f"line {n}: unknown state {row.get('state')!r}")
    if row.get("arm") not in ARMS:
        errs.append(f"line {n}: unknown arm {row.get('arm')!r}")
    if row.get("ending_reason") not in ENDINGS:
        errs.append(f"line {n}: unknown ending {row.get('ending_reason')!r}")

    state, arm = row.get("state"), row.get("arm")
    if state == "unstuck" and arm == "half":
        errs.append(f"line {n}: unstuck has no half arm (a direction is the state)")
    if arm == "control" and row.get("dose") not in (0, None):
        errs.append(f"line {n}: control entries deliver no dose")

    if "outcome" not in row:
        errs.append(f"line {n}: missing outcome")
    elif row["outcome"] is not None and not _is_bool(row["outcome"]):
        errs.append(f"line {n}: outcome must be a boolean or null (got {row['outcome']!r})")

    excluded = bool(row.get("excluded"))
    if excluded:
        if row.get("exclusion_reason") not in EXCLUSION_REASONS:
            errs.append(f"line {n}: excluded without a known exclusion_reason")
        if row.get("outcome") is not None:
            errs.append(f"line {n}: an excluded entry must not carry an outcome")
    else:
        if row.get("outcome") is None:
            errs.append(f"line {n}: a kept entry needs an outcome (null = excluded)")
        if row.get("exclusion_reason"):
            errs.append(f"line {n}: exclusion_reason on a kept entry")

    spent = (row.get("tokens_in"), row.get("tokens_out"))
    if all(isinstance(x, int) and not isinstance(x, bool) for x in spent) \
            and int(spent[0]) + int(spent[1]) == 0:
        errs.append(f"line {n}: zero tokens recorded — the cost column would be a lie")

    return errs


def load(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for i, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"line {i}: not JSON — {exc}")
    return rows


def summary(rows: list[dict]) -> str:
    kept = [r for r in rows if not r.get("excluded")]
    per = collections.Counter((r["state"], r["arm"]) for r in kept)
    lines = [f"{len(rows)} entries · {len(kept)} kept · {len(rows) - len(kept)} excluded"]
    for state in sorted(STATES):
        parts = [f"{arm} {per[(state, arm)]}" for arm in ("half", "default", "double", "control")
                 if per[(state, arm)] or arm != "half"]
        lines.append(f"  {state:<11} " + " · ".join(parts))
    short = [f"{s}/{a}={n}" for (s, a), n in per.items() if a != "control" and n < 60]
    if short:
        lines.append("  below the 60/arm floor (pilot, not a result): " + ", ".join(sorted(short)))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()

    rows = load(Path(args.ledger))
    errors: list[str] = []
    for n, row in enumerate(rows, 1):
        errors.extend(check_entry(n, row))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"ledger ok: {len(rows)} entries")
    if args.summary and rows:
        print(summary(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
