"""The worked examples are generated, and they stay generated.

A hand-written example is the one kind of copy that can quietly stop being true: the state's
material changes with the corpus, and a README that quotes last month's pair is fiction. This
runs the generator's own structural check so the file cannot rot in place.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_examples_file_is_present_and_structurally_sound():
    proc = subprocess.run([sys.executable, str(ROOT / "tools" / "examples.py"), "--check"],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_readme_points_at_the_generated_examples():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/EXAMPLES.md" in readme, "the README must link the generated examples"
    assert "## What it looks like in use" in readme


def test_no_example_quotes_a_random_seed():
    text = (ROOT / "docs" / "EXAMPLES.md").read_text(encoding="utf-8")
    assert "seed=random:" not in text, "a random seed makes the path meaningless"


def test_the_examples_never_show_a_walk_serving_material():
    """A walk withholds its material by design; an example must not imply otherwise."""
    text = (ROOT / "docs" / "EXAMPLES.md").read_text(encoding="utf-8")
    walk = text.split("## 1.", 1)[1].split("## 2.", 1)[0]
    assert "What arrived" not in walk, "a walk example showed arrivals"
    assert "does not inject" in walk
