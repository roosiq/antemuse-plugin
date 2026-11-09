"""The deterministic lane must be arithmetic, so it can be tested without a generator."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools import experiment_deterministic as det  # noqa: E402


def test_concepts_takes_the_head_word_not_the_adjective():
    assert det.concepts("Japanese lilac (n) → lookdown (n) · is a kind of") == ["lilac", "lookdown"]


def test_concepts_strips_the_seed_marker_and_the_gloss():
    line = "[seed=project:parser] walk · parser (n) → syntax tree (n) · “a sentence diagram”"
    assert det.concepts(line) == ["parser", "tree"]


def test_corpus_vocabulary_is_the_repository_talking_about_itself():
    vocab = det.corpus_vocab()
    assert len(vocab) > 500
    assert "state" in vocab and "antemuse" in vocab


def test_novelty_is_measured_against_the_corpus(monkeypatch):
    vocab = {"parser"}
    monkeypatch.setitem(det.sources.PROVIDERS, "walk",
                        lambda steps: ["parser (n) → xylophone (n) · is related to"])
    got = det.summarise("walk", 1, 3, vocab)
    assert got["novel_rate"] == 1.0          # xylophone is new, parser is not; 1 of 2 hits
    assert got["fresh_rate"] == 1.0


def test_repeats_inside_one_dose_count_as_stale(monkeypatch):
    line = "xylophone (n) → xylophone (n) · is a kind of"
    monkeypatch.setitem(det.sources.PROVIDERS, "walk", lambda steps: [line] * steps)
    got = det.summarise("walk", 3, 2, set())
    assert got["novel_rate"] == 1.0
    assert got["fresh_rate"] < 1.0           # the same concept again is not fresh
    assert got["diversity"] < 1.0


def test_a_generator_that_ignores_its_dose_is_visible_in_the_numbers(monkeypatch):
    monkeypatch.setitem(det.sources.PROVIDERS, "unstuck",
                        lambda steps: ["a (n) b", "c (n) d", "e (n) f"])
    one, three = det.summarise("unstuck", 1, 2, set()), det.summarise("unstuck", 3, 2, set())
    assert one["served_per_trial"] == three["served_per_trial"] == 3


def test_zero_dose_serves_nothing_rather_than_failing():
    got = det.summarise("walk", 0, 2, set())
    assert got["served_per_trial"] == 0 and got["novel_rate"] is None
