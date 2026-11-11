"""No maintainer's home directory in anything that runs or gets read.

Thirty-three `/home/<user>` literals shipped in 0.10.16. Most were inert, but four were not: a
fallback URL in the pane, the frame bank the surface tests copied from (so those tests skipped
everywhere but the author's box and still reported a pass), the pytest interpreter `spec_audit`
measured with, and a command in SKILL.md a user could copy and run. Each one worked only on the
machine it was written on.

Prose is exempt: AGENTS.md records provenance, and specs/ and docs/ describe past work in past
tense. Code, tests, scripts, tools and the shipped instructions are not.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCAN = ("*.py", "*.js", "*.sh", "*.md", "*.yaml", "*.yml", "*.json")
# documentation of what happened, not instructions to a machine
EXEMPT_DIRS = {".git", "docs", "specs", "experiments", "node_modules", "__pycache__",
               ".pytest_cache", "dist", "assets"}
EXEMPT_FILES = {"AGENTS.md"}
PATTERN = re.compile(r"/home/[a-z0-9_.-]+|C:\\\\Users\\\\[^\\s\"']+", re.I)


def _shipped_files():
    for pattern in SCAN:
        for path in ROOT.rglob(pattern):
            if EXEMPT_DIRS & set(path.relative_to(ROOT).parts):
                continue
            if path.name in EXEMPT_FILES or path.name.startswith("."):
                continue
            yield path


def test_nothing_that_runs_names_someones_home_directory():
    offenders = []
    for path in _shipped_files():
        for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
            for hit in PATTERN.findall(line):
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {hit}")
    assert offenders == [], "hardcoded home directories in shipped code:\n" + "\n".join(offenders)


def test_the_pane_has_no_fallback_to_one_machine():
    """The pane's still lookup had a `file:///home/<user>/...` leg in a catch block.

    A fallback that only works on the author's machine is not a fallback: it turns "I cannot derive
    this" into "ask for a path nobody has". It returns an empty list and the caller moves on.
    """
    js = (ROOT / "desktop" / "plugin.js").read_text()
    assert "/home/" not in js
    assert "return []" in js[js.index("const liveStills"):][:900]

