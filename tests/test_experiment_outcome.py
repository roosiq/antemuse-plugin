"""Primary outcomes are computed, not judged — so they are testable without a model."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools import experiment_outcome as outcome  # noqa: E402


def test_carry_finds_the_concept_the_walk_delivered():
    material = ["list system→Japanese lilac [far] → Japanese lilac→lookdown"]
    assert outcome.compute("walk", "I planted a lilac in the readme.", material) is True


def test_carry_is_false_when_the_work_ignores_the_walk():
    material = ["list system→Japanese lilac [far]"]
    assert outcome.compute("walk", "I fixed the parser bug and added a test.", material) is False


def test_landing_needs_both_halves_of_a_pair():
    material = ["the parser and the lighthouse"]
    assert outcome.compute("daydream", "a parser for the lighthouse config", material) is True
    assert outcome.compute("daydream", "a parser for the config", material) is False


def test_adoption_needs_the_source_actually_used():
    material = ["hn · https://news.ycombinator.com/item?id=1 · something"]
    assert outcome.compute("doomscroll", "I read news.ycombinator.com before writing", material) is True
    assert outcome.compute("doomscroll", "I refactored the queue", material) is False


def test_kept_is_true_only_when_something_was_kept_or_the_text_carries_it():
    material = ["the parser and the lighthouse"]
    assert outcome.compute("dream", "nothing", material, {"kept": ["h-1"]}) is True
    assert outcome.compute("dream", "nothing at all", material, {"kept": []}) is False


def test_adopted_matches_the_direction_not_the_whole_sentence():
    assert outcome.compute("unstuck", "spec: write the parser first", [],
                           {"direction": "write the parser first"}) is True
    assert outcome.compute("unstuck", "spec: paint the shed", [],
                           {"direction": "write the parser first"}) is False


def test_an_unknown_state_is_refused_rather_than_guessed():
    try:
        outcome.compute("vibes", "x", [])
    except SystemExit as exc:
        assert "no primary outcome" in str(exc)
    else:
        raise AssertionError("an unknown state must not return an outcome")


def test_wilson_interval_is_sane_at_the_edges():
    from tools.experiment_report import wilson
    p, lo, hi = wilson(0, 5)
    assert p == 0.0 and lo == 0.0 and 0 < hi < 1
    p, lo, hi = wilson(5, 5)
    assert p == 1.0 and hi == 1.0 and 0 < lo < 1
    p, lo, hi = wilson(3, 5)
    assert lo < p < hi
