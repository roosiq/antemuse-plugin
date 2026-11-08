"""A cell cut off at the token ceiling must be visible, and never replayed as whole.

The failure this guards against is quiet: a model that spends its budget reasoning
returns text that ends mid-sentence, the runner sees a non-empty string, records
`status: ok`, and a later comparison treats half an answer as a whole one. These
tests bind the finish reason into the record, carry it through F's synthesis, keep
an older-schema record from being replayed, and make the default selector prefer a
complete answer over a truncated one.
"""
from __future__ import annotations

import copy
import json

import pytest

from . import load  # noqa: E402

cache = load("cache")
runner = load("run")
run_condition = runner.run_condition
select_first = runner.select_first

TASK = json.loads(
    (__import__("pathlib").Path(__file__).resolve().parents[2]
     / "evaluation" / "tasks" / "development.json").read_text(encoding="utf-8")
)["tasks"][0]

MODEL = "test-model-truncation"
PROMPT_VERSION = "prompt-v1"
SOURCE_VERSION = "source-v1"
SEED = 11


def _respond(finish_reason="stop", text="a finished answer"):
    return {
        "text": text,
        "usage": {"input_tokens": 10, "output_tokens": 20},
        "finish_reason": finish_reason,
    }


def _run(tmp_path, condition="A", respond=None, seed=SEED, model=MODEL):
    return run_condition(
        condition,
        TASK,
        model=model,
        prompt_version=PROMPT_VERSION,
        source_version=SOURCE_VERSION,
        seed=seed,
        transport=lambda request: _respond() if respond is None else respond(request),
        cache_path=tmp_path / "cache.jsonl",
    )


def test_finish_reason_is_recorded_verbatim(tmp_path):
    stop = _run(tmp_path, respond=lambda r: _respond("stop"))
    assert stop["candidates"][0]["finish_reason"] == "stop"
    assert stop["candidates"][0]["truncated"] is False
    assert stop["truncated"] is False

    length = _run(tmp_path, respond=lambda r: _respond("length"), seed=SEED + 1)
    assert length["candidates"][0]["finish_reason"] == "length"
    assert length["candidates"][0]["truncated"] is True
    assert length["truncated"] is True
    assert length["truncated_candidates"] == ["A-0"]


def test_absent_finish_reason_is_not_invented(tmp_path):
    record = _run(tmp_path, respond=lambda r: {
        "text": "an answer", "usage": {"input_tokens": 1, "output_tokens": 2},
    })
    assert record["candidates"][0]["finish_reason"] is None
    assert record["candidates"][0]["truncated"] is False


def test_a_non_string_finish_reason_is_malformed(tmp_path):
    record = _run(tmp_path, respond=lambda r: {
        "text": "an answer", "finish_reason": 42,
    })
    assert record["status"] == "transport_error"
    assert record["candidates"][0]["status"] == "transport_error"
    assert "finish_reason" in (record["candidates"][0]["error"] or record["error"] or "")


def test_record_declares_its_schema(tmp_path):
    record = _run(tmp_path)
    assert record["record_schema"] == runner.RECORD_SCHEMA
    assert runner.RECORD_SCHEMA == "record-2"


def test_an_older_schema_record_is_not_replayed(tmp_path):
    """A record from a runner that never recorded finish reasons is a miss."""
    path = tmp_path / "cache.jsonl"
    key = cache.condition_cache_key(
        model=MODEL, condition="A", task_id=TASK["id"],
        prompt_version=PROMPT_VERSION, source_version=SOURCE_VERSION, seed=SEED,
    )
    cache.JsonlCache(path).put(key, {"status": "ok", "candidates": [], "usage": {}})

    calls = []

    def transport(request):
        calls.append(request)
        return _respond("length")

    record = run_condition(
        "A", TASK, model=MODEL, prompt_version=PROMPT_VERSION,
        source_version=SOURCE_VERSION, seed=SEED,
        transport=transport, cache_path=path,
    )
    assert calls, "an old-schema record must not stand in for a run"
    assert record["cache_status"] == "miss"
    assert record["record_schema"] == runner.RECORD_SCHEMA
    assert record["truncated"] is True


def test_a_current_schema_record_still_replays_for_free(tmp_path):
    path = tmp_path / "cache.jsonl"
    first = _run(tmp_path)
    calls = []

    def transport(request):
        calls.append(request)
        return _respond()

    replay = run_condition(
        "A", TASK, model=MODEL, prompt_version=PROMPT_VERSION,
        source_version=SOURCE_VERSION, seed=SEED,
        transport=transport, cache_path=path,
    )
    assert calls == []
    assert replay["cache_status"] == "hit"
    assert replay["run_id"] == first["run_id"]


def test_default_selector_prefers_a_complete_candidate():
    candidates = [
        {"candidate_id": "C-0", "status": "ok", "truncated": True},
        {"candidate_id": "C-1", "status": "ok", "truncated": False},
        {"candidate_id": "C-2", "status": "ok", "truncated": True},
    ]
    assert select_first(candidates) == "C-1"


def test_default_selector_takes_a_truncated_one_rather_than_nothing():
    candidates = [
        {"candidate_id": "C-0", "status": "transport_error", "truncated": False},
        {"candidate_id": "C-1", "status": "ok", "truncated": True},
    ]
    assert select_first(candidates) == "C-1"


def test_synthesis_carries_its_own_finish_reason(tmp_path):
    def respond(request):
        if request.get("stage") == "synthesis":
            return _respond("length", "a synthesised answer that stops mid-")
        return _respond("stop", f"branch {request['branch_index']}")

    record = _run(tmp_path, condition="F", respond=respond)
    assert record["status"] == "ok"
    assert record["synthesis"]["finish_reason"] == "length"
    assert record["synthesis"]["truncated"] is True
    # The branches were complete, the synthesis was not: the record says so once,
    # at the top, instead of leaving a reader to notice a dangling dash.
    assert record["truncated"] is True
    assert len(record["candidates"]) == runner.N
