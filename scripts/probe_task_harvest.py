#!/usr/bin/env python3
"""Harvest feasibility probe (task bank T1).

Deterministic and offline: walks the local repos and counts supply signals for
the evidence task bank families. Makes no model calls and writes nothing.

Usage: python3 plugin/scripts/probe_task_harvest.py [ROOT]

Every printed number is a count this script actually observed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache",
    ".mypy_cache", "dist", "build", ".next", ".wrangler", ".cache", "coverage",
    ".ruff_cache", ".turbo", "site-packages", ".m2", ".gradle",
    # git worktrees duplicate an existing tree; counting them double-counts
    # suites and data. Measured: toslop-model reported 1895 test-ish files in
    # one worktree alone.
    ".worktrees",
    # brand-agents keeps a snapshot of an agent home under brands/<x>/memory/.
    # That snapshot contains other projects' site-packages and skill tests; it
    # is not this repo's source. Measured: 510 of brand-agents' test-file hits
    # came from there (e.g. .../cache/uv/archive-v0/.../fsspec/tests).
    "hermes-home",
}
# A file only counts as a test if it both matches test naming and lives under a
# test directory. Measured: of brand-agents' 1134 name-only matches, the vast
# majority (338 + 300 + 257 + 257) were generated per-brand content under
# brands/, not suites; only supervisor/tests (38) and shipper/tests (16) are.
TEST_DIRS = {"test", "tests", "spec", "__tests__"}
FIX_RE = re.compile(r"\b(fix|fixes|fixed|repair|repairs|resolve|resolved|resolves|bug|regression)\b", re.I)
DATA_EXT = {".csv", ".json", ".jsonl", ".sql", ".tsv"}
DATA_PATH_MARKERS = ("data", "dataset", "datasets", "out", "outputs", "results", "exports", "fixtures")
TEST_NAME_PATTERNS = ("test_", "_test.", ".test.", ".spec.")
MIN_DATA_BYTES = 5_000

DEFAULT_REPOS = [
    "antemuse", "toslop", "concept.cooking", "slopslingers-infra",
    "toslop-model", "ontology-embedding-experiment", "brand-agents",
    "ryancook.name", "conceptcooking",
]


def git(repo, *args):
    try:
        out = subprocess.run(
            ("git", "-C", repo, *args), capture_output=True, text=True, timeout=60
        )
        return out.stdout if out.returncode == 0 else ""
    except Exception:
        return ""


def walk(repo):
    files = []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            files.append(os.path.relpath(os.path.join(dirpath, name), repo))
    return files


def probe(repo):
    row = {"repo": os.path.basename(repo), "exists": os.path.isdir(repo)}
    if not row["exists"]:
        return row
    row["is_git"] = os.path.isdir(os.path.join(repo, ".git"))
    row["commits"] = 0
    row["fix_commits"] = 0
    if row["is_git"]:
        count = git(repo, "rev-list", "--count", "HEAD").strip()
        row["commits"] = int(count) if count.isdigit() else 0
        subjects = git(repo, "log", "--pretty=%s").splitlines()
        row["fix_commits"] = sum(1 for s in subjects if FIX_RE.search(s))

    files = walk(repo)
    row["files"] = len(files)
    strict, loose = 0, 0
    for f in files:
        base = os.path.basename(f)
        if f.endswith((".min.js", ".map")):
            continue
        name_match = any(p in base for p in TEST_NAME_PATTERNS)
        if not name_match:
            continue
        loose += 1
        parts = [p.lower() for p in f.split(os.sep)]
        if any(p in TEST_DIRS for p in parts[:-1]):
            strict += 1
    row["test_files"] = strict
    row["test_name_only"] = loose
    row["colocated_tests"] = loose - strict

    # refactor supply: commits touching >= 2 non-test, non-doc files.
    row["multifile_commits"] = 0
    if row["is_git"]:
        numstat = git(repo, "log", "--pretty=\x01%H", "--numstat")
        cur, touched = None, set()
        def flush(commit, files_touched):
            real = [
                f for f in files_touched
                if not any(p in TEST_DIRS for p in f.lower().split("/"))
                and not f.lower().endswith((".md", ".json", ".txt", ".lock"))
            ]
            return len(real) >= 2
        for line in numstat.splitlines():
            if line.startswith("\x01"):
                if cur is not None and flush(cur, touched):
                    row["multifile_commits"] += 1
                cur, touched = line[1:], set()
                continue
            cols = line.split("\t")
            if len(cols) == 3 and cols[2]:
                touched.add(cols[2])
        if cur is not None and flush(cur, touched):
            row["multifile_commits"] += 1

    row["has_suite"] = any(
        os.path.exists(os.path.join(repo, p))
        for p in ("pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml", "package.json")
    )

    messy = []
    docs = []
    for f in files:
        parts = [p.lower() for p in f.split(os.sep)]
        ext = os.path.splitext(f)[1].lower()
        if ext == ".md":
            if parts[0] in ("docs", "specs") or "docs" in parts or "specs" in parts:
                docs.append(f)
        if ext in DATA_EXT and any(m in parts for m in DATA_PATH_MARKERS):
            try:
                if os.path.getsize(os.path.join(repo, f)) > MIN_DATA_BYTES:
                    messy.append(f)
            except OSError:
                pass
    row["messy_data"] = len(messy)
    row["docs"] = len(docs)
    return row


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "/home/ryan"
    rows = [probe(os.path.join(root, name)) for name in DEFAULT_REPOS]

    cols = ("commits", "fix_commits", "multifile_commits", "test_files", "colocated_tests", "messy_data", "docs")
    header = f"{'repo':<32}" + "".join(f"{c:>12}" for c in cols) + "  suite"
    print(header)
    print("-" * len(header))
    totals = Counter()
    for r in rows:
        if not r.get("exists"):
            print(f"{r['repo']:<32}{'ABSENT':>12}")
            continue
        line = f"{r['repo']:<32}"
        for c in cols:
            line += f"{r.get(c, 0):>12}"
            totals[c] += r.get(c, 0)
        line += "   yes" if r.get("has_suite") else "   no"
        print(line)
    print("-" * len(header))
    print(f"{'TOTAL':<32}" + "".join(f"{totals[c]:>12}" for c in cols))
    print(json.dumps({"repos": rows, "totals": dict(totals)}))


if __name__ == "__main__":
    main()
