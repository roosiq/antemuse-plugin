"""Sources are real corpora, and say so when they are not there."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))

from kitchen import sources  # noqa: E402


def _has(corpus: str) -> bool:
    try:
        if corpus == "wordnet":
            return bool(sources._wn().synsets("walk"))
        return bool(sources._frames())
    except Exception:
        return False


def test_walk_steps_use_named_relations(tmp_path, monkeypatch):
    if not _has("wordnet"):
        pytest.skip("wordnet corpus not installed")
    monkeypatch.setattr(sources, "WALK_CURSOR", tmp_path / "cursor.json")
    steps = sources.walk_step(3)
    assert steps and len(steps) <= 3
    for line in steps:
        assert "→" in line
        assert any(rel in line for rel in ("hypernym", "hyponym", "holonym", "meronym",
                                           "similar", "also", "antonym"))
    # the walk continues from where it ended
    assert sources.cursor()


def test_walk_survives_a_broken_cursor(tmp_path, monkeypatch):
    if not _has("wordnet"):
        pytest.skip("wordnet corpus not installed")
    cursor = tmp_path / "cursor.json"
    cursor.write_text('{"synset": "not.a.synset"}')
    monkeypatch.setattr(sources, "WALK_CURSOR", cursor)
    assert sources.walk_step(1)


def test_dream_recombines_frames():
    if not _has("framenet"):
        pytest.skip("framenet corpus not installed")
    lines = sources.dream_recombine(3)
    assert len(lines) == 3
    assert all(l.startswith("invented · ") for l in lines)
    assert len({l for l in lines}) >= 2


def test_memory_pairs_report_the_join():
    lines = sources.memory_pairs(2)
    assert lines
    assert all(l.startswith(("JOINED", "adjacent", "no memories")) for l in lines)


def test_providers_cover_every_state():
    from kitchen import definitions
    assert set(sources.PROVIDERS) == set(definitions.STATES)
