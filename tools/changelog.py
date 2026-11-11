#!/usr/bin/env python3
"""Regenerate the changelog section for the current version from the commits that built it.

Hand-written changelogs drift: 0.10.15 shipped an entry whose newest section was 0.9.1, thirteen
releases behind the manifest, while the file's own second line said the two move together. This
derives the section from `git log`, so the only thing that can be wrong is a commit subject.

    python3 tools/changelog.py            # rewrite the section for the manifest version
    python3 tools/changelog.py --check    # exit 1 if the manifest version has no section

The section is replaced in place, newest first; older sections are left exactly as they are.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"
HEADER = (
    "# Changelog\n\n"
    "All notable changes to Antemuse. The manifest version and this file move\n"
    "together; the catalog entry is generated from the manifest at release time.\n\n"
)


def sh(*args: str) -> str:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout


def version() -> str:
    m = re.search(r'^version: "(.*)"', (ROOT / "plugin.yaml").read_text(), re.M)
    return m.group(1) if m else ""


def commits() -> list[tuple[str, str, str]]:
    """(sha, date, subject) since the last changelog section, newest first."""
    text = sh("git", "log", "--date=short", "--pretty=%h%x09%ad%x09%s")
    out = []
    for line in text.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            out.append((parts[0], parts[1], parts[2]))
    return out


def section(ver: str) -> str:
    rows = commits()
    # the newest changelog entry that already exists marks the boundary
    existing = CHANGELOG.read_text() if CHANGELOG.exists() else ""
    known = [m for m in re.findall(r"^## (\d+\.\d+\.\d+)", existing, re.M)]
    boundary_subject = None
    if known:
        boundary_subject = f"{known[0]}:"
    lines = [f"## {ver} — {dt.date.today().isoformat()}", ""]
    kept = []
    for _sha, date, subject in rows:
        if boundary_subject and subject.startswith(boundary_subject):
            break
        subject = re.sub(r"^\d+\.\d+\.\d+:\s*", "", subject).strip()
        if subject:
            kept.append(f"- {subject} ({date})")
    lines += kept or ["- No commits since the last entry."]
    return "\n".join(lines) + "\n\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    ver = version()
    if not ver:
        print("no version in plugin.yaml", file=sys.stderr)
        return 2
    text = CHANGELOG.read_text() if CHANGELOG.exists() else HEADER
    if args.check:
        has = re.search(rf"^## {re.escape(ver)}\b", text, re.M)
        print(f"{'ok' if has else 'MISSING'}: section {ver}")
        return 0 if has else 1
    body = text[len(HEADER):] if text.startswith(HEADER) else text.split("\n\n", 1)[-1]
    body = re.sub(rf"^## {re.escape(ver)}\b.*?(?=^## |\Z)", "", body, flags=re.M | re.S).lstrip()
    CHANGELOG.write_text(HEADER + section(ver) + body)
    print(f"changelog: {ver} written ({len(section(ver).splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
