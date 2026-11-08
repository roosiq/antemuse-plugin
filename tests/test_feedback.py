"""Tests for feedback validation, history, id sets, and strategy routing."""
from __future__ import annotations

import pytest

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import collider, feedback


def _artifact(artifact_id, family):
    return {"id": artifact_id, "family": family}


def test_feedback_validates_verdict_and_id():
    with pytest.raises(ValueError):
        feedback.Feedback(candidate_id="", verdict="love")
    with pytest.raises(ValueError):
        feedback.Feedback(candidate_id="a", verdict="meh")


def test_feedback_defaults_at_to_utc_z():
    entry = feedback.Feedback(candidate_id="a", verdict="love")
    assert entry.at is not None and entry.at.endswith("Z")


def test_store_preserves_history_and_order():
    store = feedback.FeedbackStore()
    store.record("a", "love")
    store.record("a", "trash")
    store.record("b", "like")
    history = store.list()
    assert [entry.verdict for entry in history] == ["love", "trash", "like"]
    assert [entry.candidate_id for entry in store.list("a")] == ["a", "a"]


def test_store_rejects_empty_candidate_id():
    store = feedback.FeedbackStore()
    with pytest.raises(ValueError):
        store.record("", "love")


def test_ids_loved_liked_and_trash():
    store = feedback.FeedbackStore()
    store.record("a", "love")
    store.record("b", "like")
    store.record("c", "trash")
    assert store.ids(loved=True) == {"a"}
    assert store.ids(liked=True) == {"b"}
    assert store.ids(loved=True, liked=True) == {"a", "b"}
    assert "c" not in store.ids(loved=True, liked=True)


def test_strategies_routes_to_deepen_when_loved():
    store = feedback.FeedbackStore()
    store.record("a", "love")
    artifacts = [_artifact("a", "fam1"), _artifact("b", "fam2")]
    result = feedback.strategies(store, artifacts, seed=1)
    assert [a["id"] for a in result] == ["a"]


def test_strategies_routes_to_refresh_when_only_liked():
    store = feedback.FeedbackStore()
    store.record("b", "like")
    artifacts = [_artifact("a", "fam1"), _artifact("b", "fam2")]
    result = feedback.strategies(store, artifacts, seed=1)
    assert [a["id"] for a in result] == ["b"]


def test_strategies_raises_when_no_positive_feedback():
    store = feedback.FeedbackStore()
    store.record("a", "trash")
    artifacts = [_artifact("a", "fam1")]
    with pytest.raises(ValueError):
        feedback.strategies(store, artifacts, seed=1)


def test_strategies_does_not_infer_sentiment_from_note():
    store = feedback.FeedbackStore()
    store.record("a", "trash", note="I love this so much")
    artifacts = [_artifact("a", "fam1")]
    with pytest.raises(ValueError):
        feedback.strategies(store, artifacts, seed=1)
