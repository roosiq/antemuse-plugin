#!/usr/bin/env python3
"""Report how often persisted concept verdicts were kept."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Use history's ledger-path API so this tool resolves the same ledger as the plugin without writing it.
from core import history  # noqa: E402


DEFAULT_SINCE_DAYS = 30


def counts(since_days: int) -> tuple[int, int]:
    """Return keep/trash totals from the ledger's verdict rows.

    A verdict is a `served` row whose move is `keep` or `trash`. The counting
    lives in `core.history.verdicts()` so the pane's tally and this report can
    never disagree about what a verdict is.
    """
    try:
        if not history.db_path().exists():
            return 0, 0                      # a report never creates the ledger it reads
        tally = history.verdicts(max(0, int(since_days)))
    except Exception:  # health: BLE001 -- an unreadable ledger reports nothing, not an error
        return 0, 0
    return int(tally.get("keep") or 0), int(tally.get("trash") or 0)


def report(since_days: int) -> dict[str, int | float | None]:
    keep, trash = counts(since_days)
    total = keep + trash
    return {
        "keep": keep,
        "trash": trash,
        "rate": keep / total if total else None,
        "since_days": since_days,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", type=int, default=DEFAULT_SINCE_DAYS,
                        metavar="DAYS", help="only count verdicts from the past DAYS (default: 30)")
    parser.add_argument("--json", action="store_true", help="print machine-readable counts")
    args = parser.parse_args(argv)
    if args.since < 0:
        parser.error("--since must be zero or greater")

    result = report(args.since)
    if args.json:
        print(json.dumps(result))
    elif result["rate"] is None:
        print("no verdicts recorded yet")
    else:
        print(
            f"hit rate: {result['keep']} kept, {result['trash']} trashed "
            f"· {float(result['rate']) * 100:.1f}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
