"""Condition D — deterministic Antemuse material, one answer call, no inference before it.

What D must prove: the material comes from the real deterministic path (bank →
collision → selection), it costs exactly one model call, it is reproducible from
its seed, and when the bank is unavailable the run fails loudly instead of
quietly degrading into condition A.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from . import load  # noqa: E402

runner = load("run")

FIXTURE = Path(__file__).resolve().parents[2] / "evaluation" / "tasks" / "development.json"
TASK = json.loads(FIXTURE.read_text(encoding="utf-8"))["tasks"][0]
MODEL = "test-model-d"


class RecordingTransport:
    def __init__(self, text="an answer"):
        self.requests = []
        self.text = text

    def __call__(self, request):
        self.requests.append(request)
        return {"text": self.text, "usage": {"input_tokens": 10, "output_tokens": 20}}


def _run(condition="D", transport=None, cache_path=None, seed=7, tasks=None):
    transport = transport or RecordingTransport()
    record = runner.run_condition(
        condition,
        TASK,
        model=MODEL,
        prompt_version="prompt-1",
        source_version="collider-6ed948a",
        seed=seed,
        transport=transport,
        cache_path=cache_path or Path("/tmp") / f"d-{condition}-{seed}.jsonl",
        selector=None,
    )
    return record, transport


def test_d_makes_one_call_and_carries_real_material(tmp_path):
    record, transport = _run(cache_path=tmp_path / "d.jsonl")
    assert record["status"] == "ok"
    assert len(transport.requests) == 1, "D must not make auxiliary calls"

    request = transport.requests[0]
    assert request["condition"] == "D"
    assert request["instruction"] == runner.INSTRUCTIONS["A"], "D keeps A's wording"
    assert "[EXPLORATION:" in request["material"], request["material"][:120]
    assert "not findings" in request["material"]
    assert request["sources"], "the request must name its sources"


def test_d_records_provenance_but_not_candidate_bodies(tmp_path):
    record, _ = _run(cache_path=tmp_path / "d.jsonl")
    assert record["sources"], "the record must name the sources used"
    assert all(str(s).startswith("collider_") for s in record["sources"])
    for candidate in record["candidates"]:
        assert "mechanism" not in json.dumps(record["sources"])


def test_d_is_reproducible_from_its_seed(tmp_path):
    first, _ = _run(cache_path=tmp_path / "one.jsonl")
    second, _ = _run(cache_path=tmp_path / "two.jsonl")
    assert first["run_id"] == second["run_id"]
    assert first["sources"] == second["sources"]

    other, _ = _run(seed=8, cache_path=tmp_path / "three.jsonl")
    assert (other["run_id"], other["sources"]) != (first["run_id"], first["sources"])


def test_a_missing_bank_fails_loudly_instead_of_becoming_condition_a(tmp_path):
    with pytest.raises(ValueError):
        runner.deterministic_material(TASK["brief"], seed=1, artifacts=[])


def test_a_replay_of_d_costs_nothing(tmp_path):
    path = tmp_path / "d.jsonl"
    _run(cache_path=path)
    again, transport = _run(cache_path=path)
    assert again["cache_status"] == "hit"
    assert transport.requests == []


def test_a_and_d_differ_only_by_the_material(tmp_path):
    a_record, a_transport = _run("A", cache_path=tmp_path / "a.jsonl")
    d_record, d_transport = _run("D", cache_path=tmp_path / "d.jsonl")

    a_request = a_transport.requests[0]
    d_request = d_transport.requests[0]
    assert a_request["instruction"] == d_request["instruction"]
    assert "material" not in a_request, "A must not carry transfer material"
    assert d_request["material"]
    assert a_record["transport_calls"] == d_record["transport_calls"] == 1
    assert "sources" not in a_record
