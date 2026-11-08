"""Focused tests for deterministic collision planning."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import collider
from core.collision import (
    CANDIDATE_TYPE,
    CHANNEL_COLLIDED,
    CHANNEL_INSIGHTS,
    STATUS,
    Candidate,
    CollisionResult,
    collide,
)


@pytest.fixture(scope="module")
def bank():
    return collider.load_bank()


@pytest.fixture()
def task():
    return {
        "id": "task-001",
        "brief": "Design a calmer morning routine for remote workers.",
    }


def test_collide_returns_collision_result(bank, task):
    result = collide(task, bank, seed=7, count=2)
    assert isinstance(result, CollisionResult)
    assert result.task_id == "task-001"
    assert result.seed == 7
    assert result.status == STATUS
    assert len(result.source_ids) == 2
    assert len(result.candidates) == 2
    assert all(isinstance(c, Candidate) for c in result.candidates)


def test_source_selection_is_deterministic(bank, task):
    a = collide(task, bank, seed=11, count=3)
    b = collide(task, bank, seed=11, count=3)
    assert a.run_id == b.run_id
    assert a.source_ids == b.source_ids
    assert [c.to_dict() for c in a.candidates] == [c.to_dict() for c in b.candidates]


def test_source_selection_matches_collider(bank, task):
    result = collide(task, bank, seed=3, count=2)
    expected = collider.select_sources(bank, strategy="fresh", seed=3, count=2)
    assert result.source_ids == tuple(r["id"] for r in expected)


def test_collided_candidate_fields(bank, task):
    result = collide(task, bank, seed=5, count=1)
    candidate = result.candidates[0]
    source = next(r for r in bank if r["id"] == candidate.source_ids[0])

    assert candidate.channel == CHANNEL_COLLIDED
    assert candidate.candidate_type == CANDIDATE_TYPE
    assert candidate.source_ids == (source["id"],)
    assert source["title"] in candidate.thesis
    assert "task-001" in candidate.thesis
    assert candidate.mechanism == source["mechanism"]
    assert source["bridge_question"] in candidate.application
    assert task["brief"] in candidate.application
    assert source["mechanism"] in candidate.first_step
    assert task["brief"] in candidate.first_step
    assert result.run_id in candidate.candidate_id
    assert source["id"] in candidate.candidate_id


def test_ablation_metadata(bank, task):
    result = collide(task, bank, seed=5, count=1)
    candidate = result.candidates[0]
    ablation = candidate.ablation
    assert ablation["removed_source_ids"] == [candidate.source_ids[0]]
    assert set(ablation["changed_fields"]) == {
        "thesis",
        "mechanism",
        "application",
        "first_step",
    }
    assert isinstance(ablation["explanation"], str)
    assert candidate.source_ids[0] in ablation["explanation"]
    assert "mechanism" in ablation["explanation"]
    assert "bridge" in ablation["explanation"]


def test_run_id_stable_and_source_sensitive(bank, task):
    a = collide(task, bank, seed=2, count=1)
    b = collide(task, bank, seed=2, count=1)
    assert a.run_id == b.run_id
    assert a.run_id.startswith("collision-")
    assert len(a.run_id) == len("collision-") + 64

    other = collide(task, bank, seed=2, count=2)
    assert other.run_id != a.run_id


def test_run_id_changes_with_seed(bank, task):
    a = collide(task, bank, seed=1, count=1)
    b = collide(task, bank, seed=2, count=1)
    assert a.run_id != b.run_id


def test_run_id_changes_with_task_id(bank):
    t1 = {"id": "task-a", "brief": "same brief"}
    t2 = {"id": "task-b", "brief": "same brief"}
    a = collide(t1, bank, seed=4, count=1)
    b = collide(t2, bank, seed=4, count=1)
    assert a.run_id != b.run_id


def test_independent_insight_channel(bank):
    task = {
        "id": "task-002",
        "brief": "Improve onboarding docs.",
        "independent_insight": "Shorter docs are read more often.",
    }
    result = collide(task, bank, seed=9, count=1)
    channels = [c.channel for c in result.candidates]
    assert CHANNEL_COLLIDED in channels
    assert CHANNEL_INSIGHTS in channels

    insight = next(c for c in result.candidates if c.channel == CHANNEL_INSIGHTS)
    assert insight.source_ids == ()
    assert insight.mechanism == "independent_task_observation"
    assert insight.application == "Shorter docs are read more often."
    assert insight.ablation["removed_source_ids"] == []
    assert insight.ablation["changed_fields"] == []
    assert "collision" in insight.ablation["explanation"]


def test_no_independent_insight_fabricated(bank, task):
    result = collide(task, bank, seed=9, count=1)
    assert all(c.channel == CHANNEL_COLLIDED for c in result.candidates)


def test_blank_independent_insight_not_emitted(bank):
    task = {
        "id": "task-003",
        "brief": "Some brief.",
        "independent_insight": "   ",
    }
    result = collide(task, bank, seed=9, count=1)
    assert all(c.channel == CHANNEL_COLLIDED for c in result.candidates)


def test_invalid_task_errors(bank):
    with pytest.raises(ValueError):
        collide({}, bank, seed=1)
    with pytest.raises(ValueError):
        collide({"id": "", "brief": "x"}, bank, seed=1)
    with pytest.raises(ValueError):
        collide({"id": "t", "brief": ""}, bank, seed=1)
    with pytest.raises(ValueError):
        collide("not a mapping", bank, seed=1)


def test_invalid_sources_errors(task):
    with pytest.raises(ValueError):
        collide(task, [], seed=1)
    with pytest.raises(ValueError):
        collide(task, [{"id": "x"}], seed=1)
    with pytest.raises(ValueError):
        collide(task, [{"id": "", "family": "f"}], seed=1)
    with pytest.raises(ValueError):
        collide(task, "not a sequence", seed=1)


@pytest.mark.parametrize("field_name", ["title", "mechanism", "bridge_question"])
def test_missing_source_text_fields_raise_value_error(task, field_name):
    source = {
        "id": "s1",
        "family": "f1",
        "title": "Source",
        "mechanism": "Mechanism",
        "bridge_question": "Question",
    }
    del source[field_name]
    with pytest.raises(ValueError, match=field_name):
        collide(task, [source], seed=1)


def test_invalid_count_errors(bank, task):
    with pytest.raises(ValueError):
        collide(task, bank, seed=1, count=0)
    with pytest.raises(ValueError):
        collide(task, bank, seed=1, count=-1)
    with pytest.raises(ValueError):
        collide(task, bank, seed=1, count=True)
    with pytest.raises(ValueError):
        collide(task, bank, seed=1, count="2")


def test_zero_usage(bank, task):
    result = collide(task, bank, seed=1, count=1)
    assert result.usage == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def test_to_dict_is_strict_json(bank, task):
    result = collide(task, bank, seed=1, count=2)
    payload = result.to_dict()
    encoded = json.dumps(payload, allow_nan=False)
    decoded = json.loads(encoded)
    assert decoded == payload
    assert isinstance(decoded["candidates"], list)
    assert isinstance(decoded["source_ids"], list)
    for candidate in decoded["candidates"]:
        assert isinstance(candidate["source_ids"], list)
        assert isinstance(candidate["ablation"], dict)


def test_candidate_to_dict_roundtrip(bank, task):
    result = collide(task, bank, seed=1, count=1)
    candidate = result.candidates[0]
    payload = candidate.to_dict()
    assert payload["candidate_id"] == candidate.candidate_id
    assert payload["source_ids"] == list(candidate.source_ids)
    json.dumps(payload, allow_nan=False)


def test_no_llm_or_network_imports():
    module_path = Path(collider.__file__).resolve().parent / "collision.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    forbidden = {
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "urllib",
        "urllib3",
        "socket",
        "http",
        "aiohttp",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in forbidden, f"forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                assert root not in forbidden, f"forbidden import: {node.module}"
