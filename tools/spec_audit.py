#!/usr/bin/env python3
"""Does the spec record match the repository?

Two kinds of drift have bitten this repo: a change whose own header said
*proposed* while `docs/spec.md` §15 said implemented, and a recorded test count
from a suite that has since grown. Both are mechanical, so check them
mechanically.

Substring matching on status words is how that drift survives — "Not implemented."
contains "implemented" — so the first word of a status is matched with anchors.

    python3 tools/spec_audit.py            # table + drift
    python3 tools/spec_audit.py --counts   # also run pytest and compare §13
"""
from __future__ import annotations

import re
import subprocess
import sys
import tomllib  # noqa: F401  (imported for parity with the repo's python floor)
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGES = ROOT / "specs/changes"
DOC = ROOT / "docs/spec.md"

#: Four status words, and nothing else. A fifth synonym is how a table grows six of them
#: again — "verified", "approved", "planning" and "draft" all resolve to one of these.
STATUS_ALIASES = {
    "live": "live", "implemented": "live", "verified": "live", "retired": "live",
    "partial": "partial",
    "proposed": "proposed", "planning": "proposed", "draft": "proposed", "approved": "proposed",
    "not built": "not built", "notbuilt": "not built", "not implemented": "not built",
}
CANONICAL = ("live", "partial", "proposed", "not built")

#: §15 rows that survive on commit history alone: they were built before the change-log
#: discipline, and writing a spec for them now would invent a process that did not happen.
LEGACY_ROWS = {"origin-and-cleanup", "runtime-wiring", "scene-assets", "truncation-visibility",
               "wave3-audit", "wave4-shards"}


def status_word(text: str) -> str:
    """The status a human would read, in one of the four words.

    A header like "implemented (partial)" means partial, and "proposed — conflicts with the
    shipped path. Not implemented." means proposed: the first thing said is the status, and
    "not built" only wins when it is said first.
    """
    low = " ".join(text.lower().split())
    words = re.findall(r"[a-z]+", low)
    first_alias = next((i for i, w in enumerate(words) if w in STATUS_ALIASES), None)
    negated = min((i for i, w in enumerate(words[:2]) if w == "not"), default=None)
    if negated is not None and (first_alias is None or negated < first_alias):
        return "not built"
    if "partial" in words:
        return "partial"
    if first_alias is None:
        return "unknown"
    return STATUS_ALIASES[words[first_alias]]


def doc_rows() -> dict[str, str]:
    """Every §15 row, including the ones with no change folder — those are the orphans this
    audit has to be able to name."""
    text = DOC.read_text()
    # only §15 — other tables in the doc use backticked names too (walks, states, tools)
    start = text.find("## 15")
    end = text.find("## 16", start if start != -1 else 0)
    section = text[start:end] if start != -1 and end != -1 else text
    rows = {}
    # a row may carry a suffix (`desktop-surfaces` §9, `runtime-wiring` (J2)); the change is
    # still the backticked name, and a suffix must not hide the row from this audit
    for m in re.finditer(r"^\| `([a-z0-9\-]+)`[^|]*\| ([^|]+) \|", section, re.M):
        rows.setdefault(m.group(1), m.group(2).strip())
    return rows


def spec_status() -> dict[str, str]:
    out = {}
    for folder in sorted(CHANGES.iterdir()):
        f = folder / "spec.md"
        if not f.exists():
            continue
        for line in f.read_text().splitlines()[:20]:
            if line.lower().lstrip("-* ").startswith("status"):
                out[folder.name] = line.split(":", 1)[1].strip()
                break
    return out


def recorded_count() -> int | None:
    """The one authoritative line; dated blocks below it are evidence, not claims."""
    m = re.search(r"\*\*Current count: (\d+) tests\*\*", DOC.read_text())
    if m:
        return int(m.group(1))
    hits = re.findall(r"(\d+) passed", DOC.read_text())
    return int(hits[-1]) if hits else None


def pytest_bin() -> str:
    """How to run pytest here, without naming anyone's home directory.

    A hardcoded interpreter path meant this tool could only measure on the machine it was written
    on — and it measured the test count, which is the number a release note quotes.
    """
    import shutil

    found = shutil.which("pytest")
    return found or sys.executable


def actual_count() -> int | None:
    import os

    env = dict(os.environ)
    env.setdefault("NLTK_DATA", str(Path.home() / "nltk_data"))   # the caller's data, not ours
    cmd = [pytest_bin(), "-q"]
    if cmd[0] == sys.executable:
        cmd = [sys.executable, "-m", "pytest", "-q"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    m = re.search(r"(\d+) passed", proc.stdout)
    return int(m.group(1)) if m else None


def main(argv: list[str]) -> int:
    all_rows, specs = doc_rows(), spec_status()
    rows = {k: v for k, v in all_rows.items() if k in specs}
    drift = []
    for name in sorted(set(rows) | set(specs)):
        a, b = specs.get(name), rows.get(name)
        if a is None:
            print(f"{name:28s} spec.md —                      docs §15 {b}")
            continue
        if b is None:
            print(f"{name:28s} {status_word(a):12s}                  docs §15 (no row)")
            continue
        mark = "  " if status_word(a) == status_word(b) else "!!"
        print(f"{mark} {name:26s} {status_word(a):12s} §15 {status_word(b)}")
        if mark == "!!":
            drift.append(name)

    # the table is allowed four status words; a synonym means it drifted back to six
    for name, cell in sorted(rows.items()):
        word = status_word(cell)
        if word not in CANONICAL:
            print(f"!! {name:26s} §15 status {cell!r} is not one of {', '.join(CANONICAL)}")
            drift.append(f"row-status:{name}")

    # a row with no spec artifact is historical (commit history only); say how many
    orphans = sorted(set(all_rows) - set(specs))
    if orphans:
        print(f"\n   {len(orphans)} §15 row(s) with no specs/changes dir: {', '.join(orphans)}")

    if "--counts" in argv:
        rec, act = recorded_count(), actual_count()
        same = rec == act
        print(f"\n{'  ' if same else '!!'} test count: §13 records {rec}, suite has {act}")
        if not same:
            drift.append("test-count")

    print(f"\n{len(drift)} drift: {', '.join(drift) if drift else 'none'}")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
