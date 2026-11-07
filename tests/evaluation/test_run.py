"""The baseline runner must be replayable, cache-isolated, and honest about failure.

Every test drives the runner through a fake transport, so no provider SDK,
network call, or wall clock enters the measurement. The properties held here
are the ones a later analysis depends on: A and B cost exactly one model call,
C costs N independent calls plus one selector, a replay costs nothing, and no
two conditions or models can ever answer for each other.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import pytest

from . import load  # noqa: E402

cache = load("cache")
runner = load("run")
condition_cache_key = cache.condition_cache_key
CONDITIONS = runner.CONDITIONS
INSTRUCTIONS = runner.INSTRUCTIONS
N = runner.N
run_condition = runner.run_condition
select_first = runner.select_first
validate_task = runner.validate_task

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "evaluation" / "tasks" / "development.json"
)
FIXTURES = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
TASKS = FIXTURES["tasks"]
TASK = TASKS[0]

MODEL = "test-model-a"
PROMPT_VERSION = "prompt-v1"
SOURCE_VERSION = "source-v1"
SEED = 7

ZERO_USAGE = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


class FakeTransport:
    """Records every structured request and answers with structured responses."""

    def __init__(self, respond=None):
        self.requests = []
        self._respond = respond

    def __call__(self, request):
        self.requests.append(copy.deepcopy(request))
        if self._respond is not None:
            return self._respond(request)
        return {
            "text": f"{request['condition']}/{request['branch_index']} text",
            "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        }


class FailingTransport:
    def __init__(self, fail_branches=None):
        self.requests = []
        self.fail_branches = fail_branches

    def __call__(self, request):
        self.requests.append(copy.deepcopy(request))
        if self.fail_branches is None or request["branch_index"] in self.fail_branches:
            raise RuntimeError("provider socket closed")
        return {
            "text": f"survived branch {request['branch_index']}",
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        }


class CountingSelector:
    def __init__(self, choice):
        self.calls = []
        self.choice = choice

    def __call__(self, candidates):
        self.calls.append(copy.deepcopy(candidates))
        return self.choice


def run(
    condition="A",
    task=None,
    *,
    transport=None,
    cache_path,
    selector=None,
    model=MODEL,
    prompt_version=PROMPT_VERSION,
    source_version=SOURCE_VERSION,
    seed=SEED,
):
    return run_condition(
        condition,
        TASK if task is None else task,
        model=model,
        prompt_version=prompt_version,
        source_version=source_version,
        seed=seed,
        transport=FakeTransport() if transport is None else transport,
        cache_path=cache_path,
        selector=selector,
    )


def shard_lines(path):
    if not Path(path).exists():
        return []
    text = Path(path).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def key_for(condition, *, model=MODEL, task_id=None):
    return condition_cache_key(
        model=model,
        condition=condition,
        task_id=TASK["id"] if task_id is None else task_id,
        prompt_version=PROMPT_VERSION,
        source_version=SOURCE_VERSION,
        seed=SEED,
    )


# --- the condition matrix ---------------------------------------------------


def test_conditions_are_exactly_a_b_c_with_three_branches_for_c():
    assert CONDITIONS == {"A", "B", "C"}
    assert N == 3


def test_condition_a_makes_one_call_and_selects_its_only_candidate(tmp_path):
    transport = FakeTransport()
    record = run("A", transport=transport, cache_path=tmp_path / "shard.jsonl")

    assert len(transport.requests) == 1
    assert record["transport_calls"] == 1
    assert [c["candidate_id"] for c in record["candidates"]] == ["A-0"]
    assert record["selected_candidate_id"] == "A-0"
    assert record["status"] == "ok"


def test_condition_b_makes_one_call_with_a_length_matched_creativity_instruction(tmp_path):
    transport_a = FakeTransport()
    transport_b = FakeTransport()
    run("A", transport=transport_a, cache_path=tmp_path / "a.jsonl")
    record_b = run("B", transport=transport_b, cache_path=tmp_path / "b.jsonl")

    assert len(transport_b.requests) == 1
    assert len(transport_a.requests) == 1
    instruction_a = transport_a.requests[0]["instruction"]
    instruction_b = transport_b.requests[0]["instruction"]

    assert instruction_b != instruction_a
    # The whole point of condition B: the only difference from A is the request
    # to be creative, not the length of the instruction.
    assert len(instruction_b) == len(instruction_a)
    assert "creativ" in instruction_b.lower()
    assert "creativ" not in instruction_a.lower()
    assert record_b["transport_calls"] == 1
    assert record_b["instruction"] == instruction_b
    assert INSTRUCTIONS["A"] == INSTRUCTIONS["C"]
    assert len(INSTRUCTIONS["B"]) == len(INSTRUCTIONS["A"])


def test_condition_c_draws_three_independent_branches_inside_one_run(tmp_path):
    transport = FakeTransport()
    record = run("C", transport=transport, cache_path=tmp_path / "shard.jsonl")

    assert len(transport.requests) == N == 3
    assert record["transport_calls"] == 3
    assert [r["condition"] for r in transport.requests] == ["C", "C", "C"]
    assert sorted(r["branch_index"] for r in transport.requests) == [0, 1, 2]

    # Independent draws: the three branches must not be the same request.
    seeds = [r["seed"] for r in transport.requests]
    assert len(set(seeds)) == 3
    assert all(isinstance(s, int) for s in seeds)

    candidate_ids = [c["candidate_id"] for c in record["candidates"]]
    assert len(set(candidate_ids)) == 3
    assert candidate_ids == ["C-0", "C-1", "C-2"]
    assert [c["branch"] for c in record["candidates"]] == [0, 1, 2]

    # C is one condition, not three cache entries.
    assert len(shard_lines(tmp_path / "shard.jsonl")) == 1


def test_condition_c_invokes_the_supplied_selector_once_and_believes_it(tmp_path):
    selector = CountingSelector("C-2")
    record = run(
        "C",
        transport=FakeTransport(),
        cache_path=tmp_path / "shard.jsonl",
        selector=selector,
    )

    assert len(selector.calls) == 1
    assert len(selector.calls[0]) == 3
    assert record["selected_candidate_id"] == "C-2"
    # The record names a selection, never a claim of quality.
    assert "best" not in {k.lower() for k in record}


def test_default_selector_takes_the_first_candidate_not_the_judged_best(tmp_path):
    def respond(request):
        # Later candidates are longer and "nicer" — select_first must ignore that.
        return {
            "text": "x" * (request["branch_index"] + 1) + " polished prose",
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        }

    record = run(
        "C", transport=FakeTransport(respond), cache_path=tmp_path / "shard.jsonl"
    )

    assert record["selected_candidate_id"] == "C-0"
    assert select_first(record["candidates"]) == "C-0"
    # The default is deterministic and total: it never invents a candidate.
    assert select_first([]) is None
    assert select_first([dict(record["candidates"][0], status="transport_error")]) is None


# --- run records ------------------------------------------------------------


REQUIRED_RECORD_FIELDS = {
    "run_id",
    "condition",
    "task_id",
    "model",
    "seed",
    "prompt_version",
    "source_version",
    "candidates",
    "selected_candidate_id",
    "transport_calls",
    "usage",
    "status",
    "cache_status",
    "created_by",
    "task",
}


def test_record_carries_every_field_and_round_trips_through_json(tmp_path):
    record = run("C", cache_path=tmp_path / "shard.jsonl")

    assert REQUIRED_RECORD_FIELDS <= set(record)
    assert record["created_by"] == "offline_runner"
    assert record["condition"] == "C"
    assert record["task_id"] == TASK["id"]
    assert record["model"] == MODEL
    assert record["seed"] == SEED
    assert record["prompt_version"] == PROMPT_VERSION
    assert record["source_version"] == SOURCE_VERSION
    assert record["task"] == TASK
    assert record["cache_status"] == "miss"

    assert json.loads(json.dumps(record, allow_nan=False)) == record


def test_run_id_is_pinned_to_the_documented_derivation_from_the_cache_key(tmp_path):
    record = run("A", cache_path=tmp_path / "shard.jsonl")
    key = key_for("A")
    expected = "run-" + hashlib.sha256(
        f"antemuse-eval-run-v1:{key}".encode("utf-8")
    ).hexdigest()[:32]

    assert record["run_id"] == expected
    # The id is derived from the key, not a second independent hash of the inputs.
    assert record["run_id"] != key
    assert record["run_id"].startswith("run-")


def test_run_id_does_not_move_with_the_wall_clock(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 1_000_000.0)
    first = run("A", cache_path=tmp_path / "first.jsonl", transport=FakeTransport())

    monkeypatch.setattr(time, "time", lambda: 2_000_000_000.0)
    second = run("A", cache_path=tmp_path / "second.jsonl", transport=FakeTransport())

    assert first["run_id"] == second["run_id"]
    assert "created_at" not in first and "timestamp" not in first
    # Nor does the task text leak into the identifier.
    assert "lighthouse" not in first["run_id"].lower()
    assert TASK["id"] not in first["run_id"]


def test_run_id_ignores_task_text_while_the_record_keeps_the_task(tmp_path):
    edited = dict(TASK, brief=TASK["brief"] + " Add one more sentence about the stairs.")
    assert edited["brief"] != TASK["brief"]

    original = run("A", cache_path=tmp_path / "one.jsonl", transport=FakeTransport())
    changed = run(
        "A", task=edited, cache_path=tmp_path / "two.jsonl", transport=FakeTransport()
    )

    assert original["run_id"] == changed["run_id"]
    assert changed["task"] == edited
    assert changed["task"]["brief"] != original["task"]["brief"]


def test_usage_totals_are_the_sum_of_the_candidate_usages(tmp_path):
    single = run("A", cache_path=tmp_path / "a.jsonl")
    assert single["usage"] == {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
    assert single["candidates"][0]["usage"] == single["usage"]

    triple = run("C", cache_path=tmp_path / "c.jsonl")
    assert triple["usage"] == {
        "input_tokens": 30,
        "output_tokens": 15,
        "total_tokens": 45,
    }


# --- cache behaviour --------------------------------------------------------


def test_exact_replay_returns_the_stored_record_and_makes_zero_calls(tmp_path):
    path = tmp_path / "shard.jsonl"
    first_transport = FakeTransport()
    first = run("A", transport=first_transport, cache_path=path)

    replay_transport = FakeTransport()
    replay = run("A", transport=replay_transport, cache_path=path)

    assert len(first_transport.requests) == 1
    assert replay_transport.requests == []  # no transport call on a hit
    assert replay["cache_status"] == "hit"
    assert first["cache_status"] == "miss"
    assert replay["run_id"] == first["run_id"]
    assert replay["transport_calls"] == first["transport_calls"]
    # Everything except the cache verdict is byte-identical.
    assert {k: v for k, v in replay.items() if k != "cache_status"} == {
        k: v for k, v in first.items() if k != "cache_status"
    }
    # The stored record itself was written as a miss, once, and not rewritten.
    lines = shard_lines(path)
    assert len(lines) == 1
    assert lines[0]["record"]["cache_status"] == "miss"


def test_c_replay_makes_no_calls_and_does_not_reinvoke_the_selector(tmp_path):
    path = tmp_path / "shard.jsonl"
    selector = CountingSelector("C-1")
    run("C", cache_path=path, selector=selector)
    assert len(selector.calls) == 1

    replay_transport = FakeTransport()
    replay = run("C", transport=replay_transport, cache_path=path, selector=selector)

    assert replay_transport.requests == []
    assert len(selector.calls) == 1
    assert replay["cache_status"] == "hit"
    assert replay["selected_candidate_id"] == "C-1"
    assert len(shard_lines(path)) == 1


def test_a_returned_record_is_a_copy_so_mutation_cannot_rewrite_history(tmp_path):
    path = tmp_path / "shard.jsonl"
    run("C", cache_path=path)

    tampered = run("C", cache_path=path)
    tampered["candidates"][0]["text"] = "the reviewer edited this in place"
    tampered["selected_candidate_id"] = "C-0"

    again = run("C", cache_path=path)
    assert again["candidates"][0]["text"] == "C/0 text"
    assert again["selected_candidate_id"] == "C-0"
    assert shard_lines(path)[0]["record"]["candidates"][0]["text"] == "C/0 text"


def test_conditions_never_answer_for_each_other_in_one_cache(tmp_path):
    path = tmp_path / "shard.jsonl"
    records = {}
    expected_calls = {"A": 1, "B": 1, "C": N}
    for condition in ("A", "B", "C"):
        transport = FakeTransport()
        records[condition] = run(condition, transport=transport, cache_path=path)
        assert len(transport.requests) == expected_calls[condition], condition
        assert records[condition]["cache_status"] == "miss"
        assert records[condition]["condition"] == condition

    lines = shard_lines(path)
    assert len(lines) == 3
    assert len({line["key"] for line in lines}) == 3
    assert records["A"]["candidates"][0]["text"] == "A/0 text"
    assert records["B"]["candidates"][0]["text"] == "B/0 text"
    assert records["C"]["candidates"][1]["text"] == "C/1 text"


def test_a_different_model_never_hits(tmp_path):
    path = tmp_path / "shard.jsonl"
    run("A", cache_path=path, model="test-model-a")
    other = FakeTransport()
    second = run("A", cache_path=path, model="test-model-b", transport=other)

    assert len(other.requests) == 1
    assert second["cache_status"] == "miss"
    assert second["model"] == "test-model-b"
    assert second["run_id"] != run("A", cache_path=path)["run_id"]
    assert len(shard_lines(path)) == 2


def test_a_different_seed_never_hits(tmp_path):
    path = tmp_path / "shard.jsonl"
    run("A", cache_path=path)
    other = FakeTransport()
    second = run("A", cache_path=path, seed=SEED + 1, transport=other)

    assert len(other.requests) == 1
    assert second["cache_status"] == "miss"
    assert second["seed"] == SEED + 1


# --- failure must be recorded, never faked --------------------------------


def test_malformed_condition_is_a_named_failure_record_with_no_calls(tmp_path):
    path = tmp_path / "shard.jsonl"
    for bad in ("D", "a", "", None):
        transport = FakeTransport()
        record = run(bad, transport=transport, cache_path=path)

        assert record["status"] == "invalid_condition", bad
        assert record["condition"] == (bad if isinstance(bad, str) else None)
        assert record["run_id"] is None
        assert record["transport_calls"] == 0
        assert record["candidates"] == []
        assert record["selected_candidate_id"] is None
        assert record["cache_status"] == "miss"
        assert record["created_by"] == "offline_runner"
        assert record["error"]
        assert transport.requests == []
    assert shard_lines(path) == []


def test_transport_failure_is_named_and_not_cached_as_success(tmp_path):
    path = tmp_path / "shard.jsonl"
    failing = FailingTransport()
    record = run("A", transport=failing, cache_path=path)

    assert record["status"] == "transport_error"
    assert record["transport_calls"] == 1
    assert record["selected_candidate_id"] is None
    assert record["error"] and "provider socket closed" in record["error"]
    assert record["candidates"][0]["status"] == "transport_error"
    assert record["candidates"][0]["text"] is None
    assert record["candidates"][0]["usage"] == ZERO_USAGE
    assert record["usage"] == ZERO_USAGE
    # A failed run leaves the shard untouched, so a retry can still succeed.
    assert shard_lines(path) == []

    retry_transport = FakeTransport()
    retry = run("A", transport=retry_transport, cache_path=path)
    assert len(retry_transport.requests) == 1
    assert retry["cache_status"] == "miss"
    assert retry["status"] == "ok"
    assert len(shard_lines(path)) == 1


@pytest.mark.parametrize(
    "response",
    [
        "not a dict",
        None,
        {},
        {"text": ""},
        {"text": "   "},
        {"text": None},
        {"text": "fine", "usage": {"input_tokens": -1}},
        {"text": "fine", "usage": {"input_tokens": "10"}},
        {"text": "fine", "usage": "many tokens"},
    ],
    ids=[
        "string",
        "none",
        "empty-dict",
        "empty-text",
        "blank-text",
        "null-text",
        "negative-usage",
        "string-usage",
        "non-dict-usage",
    ],
)
def test_a_malformed_response_is_a_failure_not_a_candidate(tmp_path, response):
    path = tmp_path / "shard.jsonl"
    record = run(
        "A",
        transport=FakeTransport(respond=lambda _request: response),
        cache_path=path,
    )

    assert record["status"] == "transport_error"
    assert record["selected_candidate_id"] is None
    assert record["candidates"][0]["text"] is None
    assert record["error"]
    assert shard_lines(path) == []


def test_partial_c_failure_is_partial_and_never_cached(tmp_path):
    path = tmp_path / "shard.jsonl"
    transport = FailingTransport(fail_branches={1})
    record = run("C", transport=transport, cache_path=path)

    assert record["transport_calls"] == 3
    assert record["status"] == "partial"
    assert [c["status"] for c in record["candidates"]] == [
        "ok",
        "transport_error",
        "ok",
    ]
    assert record["selected_candidate_id"] == "C-0"
    # Two candidates contributed usage; the failed branch contributed nothing.
    assert record["usage"] == {
        "input_tokens": 2,
        "output_tokens": 2,
        "total_tokens": 4,
    }
    assert shard_lines(path) == []


def test_c_with_every_branch_failing_is_a_transport_error(tmp_path):
    record = run(
        "C", transport=FailingTransport(), cache_path=tmp_path / "shard.jsonl"
    )

    assert record["status"] == "transport_error"
    assert record["transport_calls"] == 3
    assert record["selected_candidate_id"] is None
    assert all(c["status"] == "transport_error" for c in record["candidates"])
    assert record["usage"] == ZERO_USAGE


@pytest.mark.parametrize("bad_choice", ["C-9", "", None, 3])
def test_a_selector_choice_outside_the_candidates_is_not_trusted(tmp_path, bad_choice):
    path = tmp_path / "shard.jsonl"
    selector = CountingSelector(bad_choice)
    record = run("C", cache_path=path, selector=selector)

    assert len(selector.calls) == 1
    assert record["status"] == "selector_error"
    assert record["selected_candidate_id"] is None
    assert record["error"]
    assert shard_lines(path) == []


def test_a_selector_that_raises_is_named_not_swallowed(tmp_path):
    def selector(candidates):
        raise RuntimeError("selector model unavailable")

    record = run("C", cache_path=tmp_path / "shard.jsonl", selector=selector)

    assert record["status"] == "selector_error"
    assert record["selected_candidate_id"] is None
    assert "selector model unavailable" in record["error"]
    assert len(record["candidates"]) == 3


def test_selector_cannot_promote_a_failed_candidate(tmp_path):
    selector = CountingSelector("C-1")
    record = run(
        "C",
        transport=FailingTransport(fail_branches={1}),
        cache_path=tmp_path / "shard.jsonl",
        selector=selector,
    )

    assert record["status"] == "selector_error"
    assert record["selected_candidate_id"] is None


# --- task validation and fixtures ------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        lambda t: {},
        lambda t: {k: v for k, v in t.items() if k != "brief"},
        lambda t: dict(t, id=""),
        lambda t: dict(t, id="   "),
        lambda t: dict(t, brief=None),
        lambda t: dict(t, good_idea_qualities="one quality"),
        lambda t: dict(t, good_idea_qualities=[]),
        lambda t: dict(t, good_idea_qualities=["ok", ""]),
        lambda t: dict(t, forbidden_topics="violence"),
        lambda t: dict(t, reference_text=""),
        lambda t: dict(t, id=17),
    ],
    ids=[
        "empty",
        "missing-brief",
        "blank-id",
        "whitespace-id",
        "null-brief",
        "qualities-not-list",
        "qualities-empty",
        "quality-blank",
        "forbidden-not-list",
        "blank-reference",
        "non-string-id",
    ],
)
def test_malformed_tasks_are_rejected_before_any_call(tmp_path, mutate):
    transport = FakeTransport()
    with pytest.raises(ValueError):
        run(
            "A",
            task=mutate(TASK),
            transport=transport,
            cache_path=tmp_path / "shard.jsonl",
        )
    assert transport.requests == []


def test_task_must_be_an_object():
    with pytest.raises(ValueError):
        validate_task("a brief is not a task")


def test_both_development_fixtures_validate_and_look_like_tasks():
    assert isinstance(FIXTURES["tasks"], list)
    assert len(TASKS) == 2
    assert len({task["id"] for task in TASKS}) == 2
    for task in TASKS:
        assert validate_task(task) is None
        assert set(task) >= {
            "id",
            "brief",
            "good_idea_qualities",
            "forbidden_topics",
            "reference_text",
        }
        assert task["brief"].strip()
        assert len(task["reference_text"]) < 600
        assert task["good_idea_qualities"]
        # Fixtures are development-only: no contact details, no real names.
        assert "@" not in task["brief"]


def test_transport_and_selector_must_be_callable(tmp_path):
    with pytest.raises(TypeError):
        run_condition(
            "A",
            TASK,
            model=MODEL,
            prompt_version=PROMPT_VERSION,
            source_version=SOURCE_VERSION,
            seed=SEED,
            transport=None,
            cache_path=tmp_path / "shard.jsonl",
        )
    with pytest.raises(TypeError):
        run("A", cache_path=tmp_path / "shard.jsonl", selector="not callable")


def test_every_request_is_a_plain_json_object(tmp_path):
    transport = FakeTransport()
    task = TASKS[1]
    run("C", task=task, transport=transport, cache_path=tmp_path / "shard.jsonl")

    assert len(transport.requests) == 3
    for request in transport.requests:
        assert json.loads(json.dumps(request, allow_nan=False)) == request
        assert request["task_id"] == task["id"]
        assert request["brief"] == task["brief"]
        assert request["model"] == MODEL
        assert request["prompt_version"] == PROMPT_VERSION
        assert request["source_version"] == SOURCE_VERSION
        assert request["instruction"] == INSTRUCTIONS["C"]
