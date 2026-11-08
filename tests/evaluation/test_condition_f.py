"""Condition F — separated branches with Collider sources, then selection.

What F must hold: one call per selected source, each branch carrying only its own
source (separation, not a shared context with three answers), instructions built
by production's own `orchestrator.branch_plan`, a selector that picks exactly one
of the successful candidates, and a record that names every source used.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from . import load  # noqa: E402

runner = load("run")

import sys  # noqa: E402

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core import collider, orchestrator  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[2] / "evaluation" / "tasks" / "development.json"
TASK = json.loads(FIXTURE.read_text(encoding="utf-8"))["tasks"][0]
MODEL = "test-model-f"


class RecordingTransport:
    def __init__(self):
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        return {"text": f"answer from {request.get('sources')}",
                "usage": {"input_tokens": 10, "output_tokens": 5}}


def _run(transport=None, cache_path=None, seed=11, selector=None):
    transport = transport or RecordingTransport()
    record = runner.run_condition(
        "F", TASK,
        model=MODEL,
        prompt_version="prompt-1",
        source_version="collider-6ed948a",
        seed=seed,
        transport=transport,
        cache_path=cache_path or Path("/tmp") / f"f-{seed}.jsonl",
        selector=selector,
    )
    return record, transport


def _branches(transport):
    return [r for r in transport.requests if r.get("stage") != "synthesis"]


def _synthesis(transport):
    found = [r for r in transport.requests if r.get("stage") == "synthesis"]
    return found[0] if found else None


def test_f_runs_one_branch_per_source_then_one_synthesis(tmp_path):
    record, transport = _run(cache_path=tmp_path / "f.jsonl")
    assert record["status"] == "ok"
    assert len(_branches(transport)) == runner.N, "one call per branch"
    assert _synthesis(transport) is not None, "F must also write a final answer"
    assert record["transport_calls"] == runner.N + 1
    assert len(record["candidates"]) == runner.N
    assert record["selected_candidate_id"] in {c["candidate_id"] for c in record["candidates"]}


def test_each_branch_sees_only_its_own_source(tmp_path):
    record, transport = _run(cache_path=tmp_path / "f.jsonl")
    seen = [r["sources"] for r in _branches(transport)]
    assert all(len(sources) == 1 for sources in seen), seen
    assert len({sources[0] for sources in seen}) == len(seen), "branches must not share a source"

    for request in _branches(transport):
        text = json.dumps(request["inputs"])
        for other in {sources[0] for sources in seen} - set(request["sources"]):
            assert other not in text, "a branch leaked a sibling's source into its inputs"


def test_f_uses_productions_own_branch_plan(tmp_path):
    _, transport = _run(cache_path=tmp_path / "f.jsonl")
    # compare against the plan production builds for the same bank and seed
    plan = orchestrator.branch_plan({"id": "eval-task", "brief": TASK["brief"]},
                                    list(collider.load_bank()), seed=11, count=runner.N)
    branches = _branches(transport)
    assert [p["instruction"] for p in plan] == [r["instruction"] for r in branches]
    assert [p["inputs"] for p in plan] == [r["inputs"] for r in branches]
    assert [p["source_id"] for p in plan] == [r["sources"][0] for r in branches]


def test_the_record_names_every_source_used(tmp_path):
    record, transport = _run(cache_path=tmp_path / "f.jsonl")
    assert record["sources"] == [r["sources"][0] for r in _branches(transport)]
    assert len(record["sources"]) == runner.N


def test_f_is_reproducible_from_its_seed(tmp_path):
    first, _ = _run(cache_path=tmp_path / "one.jsonl")
    second, _ = _run(cache_path=tmp_path / "two.jsonl")
    assert first["run_id"] == second["run_id"]
    assert first["sources"] == second["sources"]
    assert first["selected_candidate_id"] == second["selected_candidate_id"]


def test_an_explicit_selector_decides_and_the_default_is_deterministic(tmp_path):
    def last(candidates):
        return candidates[-1]["candidate_id"]

    chosen, _ = _run(cache_path=tmp_path / "a.jsonl", selector=last)
    assert chosen["selected_candidate_id"] == chosen["candidates"][-1]["candidate_id"]

    first, _ = _run(cache_path=tmp_path / "b.jsonl")
    second, _ = _run(cache_path=tmp_path / "c.jsonl")
    assert first["selected_candidate_id"] == second["selected_candidate_id"]


def test_a_missing_bank_fails_loudly(tmp_path):
    with pytest.raises(ValueError):
        runner.branch_material(TASK["brief"], seed=1, artifacts=[])


def test_the_final_answer_is_written_from_the_selected_candidate_only(tmp_path):
    record, transport = _run(cache_path=tmp_path / "f.jsonl")
    request = _synthesis(transport)
    chosen = next(c for c in record["candidates"]
                  if c["candidate_id"] == record["selected_candidate_id"])

    assert chosen["text"] in request["instruction"]
    for other in record["candidates"]:
        if other["candidate_id"] != chosen["candidate_id"]:
            assert other["text"] not in request["instruction"], "a sibling leaked into synthesis"

    assert record["synthesis"]["status"] == "ok"
    assert record["synthesis"]["candidate_id"] == chosen["candidate_id"]
    assert record["synthesis"]["text"]


def test_a_failed_synthesis_is_named_and_not_counted_as_an_answer(tmp_path):
    class HalfBroken(RecordingTransport):
        def __call__(self, request):
            if request.get("stage") == "synthesis":
                raise RuntimeError("upstream said no")
            return super().__call__(request)

    record, _ = _run(transport=HalfBroken(), cache_path=tmp_path / "f.jsonl")
    assert record["status"] == "synthesis_error"
    assert record["synthesis"]["status"] == "transport_error"
    assert "upstream said no" in record["error"]
    assert record["selected_candidate_id"] is not None, "the selection still stands"
