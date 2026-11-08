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

STATUS_WORDS = ("implemented", "verified", "partial", "proposed", "planning",
                "draft", "approved", "retired")


def status_word(text: str) -> str:
    """The status a human would read, not the first substring that matches."""
    words = re.findall(r"[a-z]+", text.lower())
    # "not implemented" is not "implemented"
    for i, word in enumerate(words):
        if word in STATUS_WORDS:
            if i and words[i - 1] == "not":
                return "not-" + word
            return word
    return "unknown"


def doc_rows() -> dict[str, str]:
    text = DOC.read_text()
    names = {p.name for p in CHANGES.iterdir() if p.is_dir()}
    rows = {}
    for m in re.finditer(r"^\| `([a-z0-9\-]+)` \| ([^|]+) \|", text, re.M):
        if m.group(1) in names:
            rows[m.group(1)] = m.group(2).strip()
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
    for candidate in ("/home/ryan/.local/bin/pytest", "pytest"):
        if Path(candidate).exists() or candidate == "pytest":
            return candidate
    return sys.executable


def actual_count() -> int | None:
    proc = subprocess.run([pytest_bin(), "-q"], cwd=ROOT, capture_output=True, text=True,
                          env={**__import__("os").environ, "NLTK_DATA": "/home/ryan/nltk_data"})
    m = re.search(r"(\d+) passed", proc.stdout)
    return int(m.group(1)) if m else None


def main(argv: list[str]) -> int:
    rows, specs = doc_rows(), spec_status()
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
