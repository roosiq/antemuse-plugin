"""Tests for deterministic cleanup and optional selection-only judging."""
from __future__ import annotations

import copy

import pytest

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import selection


def _candidate(candidate_id, thesis, application, source_ids=None, channel=None):
    record = {
        "candidate_id": candidate_id,
        "thesis": thesis,
        "application": application,
        "source_ids": list(source_ids or []),
    }
    if channel is not None:
        record["channel"] = channel
    return record


def test_normalize_text_lowercases_collapses_and_strips():
    assert selection.normalize_text("  Hello   World\n") == "hello world"
    assert selection.normalize_text("A\tB") == "a b"


def test_cleanup_dedups_exact_normalized_and_preserves_order():
    candidates = [
        _candidate("a", "First  Thesis", "App one"),
        _candidate("b", "first thesis", "APP ONE"),
        _candidate("c", "Second", "App two"),
    ]
    result = selection.cleanup_candidates(candidates)
    assert [c["candidate_id"] for c in result] == ["a", "c"]


def test_cleanup_removes_forbidden_topics_case_insensitively():
    candidates = [
        _candidate("a", "A safe thesis", "Safe app"),
        _candidate("b", "Weapons thesis", "App"),
        _candidate("c", "Thesis", "Contains WEAPONS here"),
    ]
    result = selection.cleanup_candidates(candidates, forbidden_topics=["weapons"])
    assert [c["candidate_id"] for c in result] == ["a"]


def test_cleanup_does_not_mutate_inputs():
    candidates = [_candidate("a", "T", "A"), _candidate("b", "T", "A")]
    snapshot = copy.deepcopy(candidates)
    selection.cleanup_candidates(candidates, forbidden_topics=["x"])
    assert candidates == snapshot


def test_cleanup_rejects_duplicate_candidate_ids():
    candidates = [_candidate("a", "T1", "A1"), _candidate("a", "T2", "A2")]
    with pytest.raises(ValueError):
        selection.cleanup_candidates(candidates)


def test_cleanup_rejects_invalid_candidates():
    with pytest.raises(ValueError):
        selection.cleanup_candidates([{"candidate_id": "", "thesis": "t", "application": "a", "source_ids": []}])
    with pytest.raises(ValueError):
        selection.cleanup_candidates([{"candidate_id": "a", "thesis": "t", "application": "a", "source_ids": "x"}])


def test_channel_for_derives_and_validates():
    assert selection.channel_for(_candidate("a", "t", "a", source_ids=["s1"])) == "collided"
    assert selection.channel_for(_candidate("a", "t", "a")) == "insights_without_collision"
    assert selection.channel_for(_candidate("a", "t", "a", source_ids=["s1"], channel="collided")) == "collided"
    with pytest.raises(ValueError):
        selection.channel_for(_candidate("a", "t", "a", source_ids=["s1"], channel="insights_without_collision"))
    with pytest.raises(ValueError):
        selection.channel_for(_candidate("a", "t", "a", channel="bogus"))


def test_select_default_is_first_unique_unjudged():
    candidates = [
        _candidate("a", "T1", "A1"),
        _candidate("b", "T1", "A1"),
        _candidate("c", "T2", "A2"),
        _candidate("d", "T3", "A3"),
    ]
    result = selection.select_for_synthesis(candidates, count=2)
    assert result["selection_status"] == "unjudged"
    assert [c["candidate_id"] for c in result["selected"]] == ["a", "c"]
    assert "error" not in result


def test_select_judged_sorts_by_mean_with_stable_ties():
    candidates = [
        _candidate("a", "T1", "A1"),
        _candidate("b", "T2", "A2"),
        _candidate("c", "T3", "A3"),
    ]
    scores = {
        "a": {"novelty": 3, "usefulness": 3, "coherence": 3, "surprise": 3, "potential": 3},
        "b": {"novelty": 5, "usefulness": 5, "coherence": 5, "surprise": 5, "potential": 5},
        "c": {"novelty": 3, "usefulness": 3, "coherence": 3, "surprise": 3, "potential": 3},
    }

    def judge(candidate):
        return scores[candidate["candidate_id"]]

    result = selection.select_for_synthesis(candidates, judge=judge, count=3)
    assert result["selection_status"] == "judged"
    assert result["threshold_used"] == 4.0
    assert [c["candidate_id"] for c in result["selected"]] == ["b", "a", "c"]
    for record in result["selected"]:
        assert set(record["axis_scores"]) == set(selection.AXES)


def test_select_judge_failure_falls_back_unjudged_with_error():
    candidates = [_candidate("a", "T1", "A1"), _candidate("b", "T2", "A2")]

    def judge(candidate):
        raise RuntimeError("boom")

    result = selection.select_for_synthesis(candidates, judge=judge, count=1)
    assert result["selection_status"] == "unjudged"
    assert [c["candidate_id"] for c in result["selected"]] == ["a"]
    assert "error" in result
    assert "axis_scores" not in result["selected"][0]


def test_select_judge_missing_axis_falls_back():
    candidates = [_candidate("a", "T1", "A1")]

    def judge(candidate):
        return {"novelty": 5}

    result = selection.select_for_synthesis(candidates, judge=judge, count=1)
    assert result["selection_status"] == "unjudged"
    assert "error" in result


def test_select_does_not_mutate_inputs():
    candidates = [_candidate("a", "T1", "A1"), _candidate("b", "T2", "A2")]
    snapshot = copy.deepcopy(candidates)

    def judge(candidate):
        return {axis: 5 for axis in selection.AXES}

    selection.select_for_synthesis(candidates, judge=judge, count=2)
    assert candidates == snapshot
