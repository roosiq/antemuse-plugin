"""Condition E — the plain branching control.

E must hold the properties that make it usable as a control: N independent calls
at N distinct seeds, no source material of any kind, and no promoted candidate —
because a selector would make E what F already is.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from . import load  # noqa: E402

runner = load("run")

FIXTURE = Path(__file__).resolve().parents[2] / "evaluation" / "tasks" / "development.json"
TASK = json.loads(FIXTURE.read_text(encoding="utf-8"))["tasks"][0]
MODEL = "test-model-e"


class RecordingTransport:
    def __init__(self):
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        return {"text": f"answer {request['seed']}",
                "usage": {"input_tokens": 8, "output_tokens": 4}}


def _run(transport=None, cache_path=None, seed=5, selector=None):
    transport = transport or RecordingTransport()
    record = runner.run_condition(
        "E", TASK,
        model=MODEL,
        prompt_version="prompt-1",
        source_version="collider-6ed948a",
        seed=seed,
        transport=transport,
        cache_path=cache_path or Path("/tmp") / f"e-{seed}.jsonl",
        selector=selector,
    )
    return record, transport


def test_e_branches_at_distinct_seeds_with_no_material(tmp_path):
    record, transport = _run(cache_path=tmp_path / "e.jsonl")
    assert record["status"] == "ok"
    assert len(transport.requests) == runner.N

    seeds = [request["seed"] for request in transport.requests]
    assert len(set(seeds)) == runner.N, "branches must be independent draws"

    for request in transport.requests:
        assert request["instruction"] == runner.INSTRUCTIONS["A"]
        assert "material" not in request, "E carries no transfer material"
        assert "sources" not in request or request["sources"] == []


def test_e_promotes_nothing(tmp_path):
    record, _ = _run(cache_path=tmp_path / "e.jsonl")
    assert record["selected_candidate_id"] is None
    assert all(c["status"] == "ok" for c in record["candidates"])
    assert "sources" not in record


def test_e_ignores_a_selector_because_it_has_none(tmp_path):
    def explode(candidates):
        raise AssertionError("E must not run a selector")

    record, _ = _run(cache_path=tmp_path / "e.jsonl", selector=explode)
    assert record["status"] == "ok"
    assert record["selected_candidate_id"] is None


def test_e_is_reproducible_from_its_seed(tmp_path):
    first, one = _run(cache_path=tmp_path / "a.jsonl")
    second, two = _run(cache_path=tmp_path / "b.jsonl")
    assert first["run_id"] == second["run_id"]
    assert [r["seed"] for r in one.requests] == [r["seed"] for r in two.requests]

    other, three = _run(seed=6, cache_path=tmp_path / "c.jsonl")
    assert other["run_id"] != first["run_id"]


def test_e_and_c_differ_only_by_the_selection(tmp_path):
    e_record, e_transport = _run(cache_path=tmp_path / "e.jsonl")
    c_record, c_transport = _run_condition("C", cache_path=tmp_path / "c.jsonl")

    assert e_transport.requests[0]["instruction"] == c_transport.requests[0]["instruction"]
    assert e_record["transport_calls"] == c_record["transport_calls"]
    assert e_record["selected_candidate_id"] is None
    assert c_record["selected_candidate_id"] is not None


def _run_condition(condition, cache_path):
    transport = RecordingTransport()
    record = runner.run_condition(
        condition, TASK,
        model=MODEL,
        prompt_version="prompt-1",
        source_version="collider-6ed948a",
        seed=5,
        transport=transport,
        cache_path=cache_path,
        selector=None,
    )
    return record, transport
