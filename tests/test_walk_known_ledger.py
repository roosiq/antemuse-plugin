"""The ledger is an input to the walk, not a gate on it.

Kept from the gap-fix review: the walk used to stall when every concept it could
reach had been seen before, and it used to walk into the concepts it had already
been to. Both are properties of the walk, so they survive the cut to one state.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import history, walks  # noqa: E402


def _has_wordnet() -> bool:
    try:
        from nltk.corpus import wordnet as wn
        wn.synsets("hand")
        return True
    except Exception:
        return False


def test_a_walk_still_delivers_when_every_concept_is_known(tmp_path, monkeypatch):
    """A ledger that has seen everything is not a reason to stall."""
    if not _has_wordnet():
        pytest.skip("wordnet not installed")
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    monkeypatch.setattr(history, "known", lambda term, exclude_session="": True)
    spec = dict(walks.BUILTIN["outer"], name="outer")
    lines = walks.GraphWalk(spec, tmp_path / "c.json").step(3)
    assert len(lines) == 3, "a known graph must not stall the walk"
    assert all("→" in line for line in lines)


def test_the_ledger_steers_the_walk_away_from_a_known_concept(tmp_path, monkeypatch):
    """When one neighbour is known and the rest are not, the known one is not chosen."""
    if not _has_wordnet():
        pytest.skip("wordnet not installed")
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    known = {"agent"}
    monkeypatch.setattr(history, "known",
                        lambda term, exclude_session="": term.lower() in known)
    spec = dict(walks.BUILTIN["wander"], name="wander")
    destinations = []
    for i in range(12):
        lines = walks.GraphWalk(spec, tmp_path / f"w{i}.json").step(2)
        for line in lines:
            destinations.append(line.split("·")[0].split("→")[-1].split("(")[0].strip().lower())
    repeats = [d for d in destinations if d in known]
    assert len(repeats) <= len(destinations) // 4, repeats
