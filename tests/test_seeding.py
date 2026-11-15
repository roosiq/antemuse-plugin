"""Walk seeding remains deterministic and falls forward when a source is empty."""
from __future__ import annotations

import sys
from pathlib import Path

from conftest import requires_tree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core import seeding  # noqa: E402


@requires_tree(".git")
def test_project_vocabulary_comes_from_repository():
    terms = seeding.project_terms()
    assert terms and all(term == term.lower() for term in terms)


def test_walk_mix_matches_declared_ratio():
    counts = {"project": 0, "conversation": 0, "random": 0}
    for i in range(400):
        counts[seeding._tier("walk", 1_700_000_000 + i, 0)] += 1
    total = sum(counts.values())
    for name, wanted in (("project", 50), ("conversation", 30), ("random", 20)):
        assert abs(100 * counts[name] / total - wanted) <= 8


def test_empty_tier_falls_forward():
    original = seeding.conversation_terms
    try:
        seeding.conversation_terms = lambda *_a, **_kw: []
        got = seeding.entry("walk", when=1_700_000_000)
        assert got["source"] in ("project", "random") and got["term"]
    finally:
        seeding.conversation_terms = original


def test_same_walk_entry_replays_same_seed():
    first = seeding.entry("walk", when=1_700_000_000, counter=3)
    assert first == seeding.entry("walk", when=1_700_000_000, counter=3)


def test_used_term_is_skipped():
    first = seeding.entry("walk", when=1_700_000_000)
    next_seed = seeding.entry("walk", when=1_700_000_000, exclude=[first["term"]])
    assert next_seed["term"].lower() != first["term"].lower()


def test_marker_is_audit_trail():
    assert seeding.marker({"source": "project", "term": "parser"}) == "seed=project:parser"
