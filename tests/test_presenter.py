"""Operational projections are the only thing that leaves the run.

A run event is typed data with a small allowlisted surface. Everything the run
knows and must not publish — prompts, messages, responses, reasoning, private
memory, credentials — is dropped at the boundary, not scrubbed afterwards.
These tests attack that boundary rather than trusting it.
"""
from __future__ import annotations

import json
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ANTEMUSE_STATES_HOME", tempfile.mkdtemp(prefix="presenter-"))

import pytest  # noqa: E402

from core import presenter  # noqa: E402

SURFACES = ("terminal", "chat", "dashboard")

CORE_FIELDS = {
    "type", "operation", "state", "run_id", "seq", "at",
    "source_ids", "candidate_ids", "status", "usage",
}

TOKENS = {"SOURCE", "BRANCH", "SELECT", "REJECT", "FEEDBACK", "DONE", "FAIL", "USAGE", "START"}

EXPECTED_TOKEN = {
    "run_started": "START",
    "source_selected": "SOURCE",
    "branch_started": "BRANCH",
    "branch_completed": "BRANCH",
    "branch_failed": "FAIL",
    "candidate_selected": "SELECT",
    "candidate_rejected": "REJECT",
    "feedback_recorded": "FEEDBACK",
    "run_completed": "DONE",
    "run_failed": "FAIL",
    "usage_recorded": "USAGE",
}

BANNED_KEYS = (
    "prompt", "messages", "response_text", "reasoning", "chain_of_thought",
    "private_memory", "api_key", "authorization",
)

SECRETS = (
    "sk-live-TOPSECRET-001",
    "Bearer eyJhbGciOiJIUzI1NiJ9.TOPSECRET",
    "my-private-diary-entry-42",
    "the model thought about TOPSECRET reasoning",
)


def event(type_="run_started", **overrides):
    base = {
        "type": type_,
        "run_id": "run-1",
        "seq": 0,
        "at": 1700000000.0,
    }
    base.update(overrides)
    return base


def leaky_event(type_="branch_started"):
    """Every forbidden channel at once, including nested copies."""
    return {
        "type": type_,
        "run_id": "run-leak",
        "seq": 3,
        "at": 1700000001,
        "status": "running",
        "source_ids": ["src-a", "src-a", "src-b"],
        "candidate_ids": ["cand-1"],
        "prompt": "system: you are " + SECRETS[3],
        "messages": [{"role": "user", "content": SECRETS[0]}],
        "response_text": SECRETS[2],
        "reasoning": SECRETS[3],
        "chain_of_thought": SECRETS[3],
        "private_memory": {"entry": SECRETS[2]},
        "api_key": SECRETS[0],
        "authorization": SECRETS[1],
        "unknown_field": SECRETS[2],
        "metadata": {"api_key": SECRETS[0], "private_memory": SECRETS[2]},
        "sources": [
            {"id": "src-a", "api_key": SECRETS[0], "private_memory": SECRETS[2]},
            {"id": "src-b", "reasoning": SECRETS[3], "extra": {"prompt": SECRETS[3]}},
        ],
        "candidates": [
            {"id": "cand-1", "chain_of_thought": SECRETS[3], "authorization": SECRETS[1]},
        ],
        "usage": {
            "input_tokens": 11,
            "output_tokens": 5,
            "total_tokens": 16,
            "cost_usd": 0.002,
            "api_key": SECRETS[0],
            "provider": "openai",
        },
    }


def ops_of(events, surface="terminal"):
    return [presenter.project_event(e, surface=surface) for e in events]


def dump(op):
    return json.dumps(op, sort_keys=True, allow_nan=False)


# --------------------------------------------------------------------------
# shape and coverage
# --------------------------------------------------------------------------


def test_every_allowed_event_projects_on_every_surface():
    for type_, token in EXPECTED_TOKEN.items():
        for surface in SURFACES:
            op = presenter.project_event(event(type_), surface=surface)
            assert op is not None, (type_, surface)
            assert op["operation"] == token, (type_, surface, op["operation"])
            assert CORE_FIELDS <= set(op), (type_, surface, set(op))
            assert op["type"] == type_
            assert op["run_id"] == "run-1"
            assert op["seq"] == 0
            assert op["at"] == 1700000000.0
            json.dumps(op, allow_nan=False)


def test_operation_is_always_an_allowlisted_token():
    for type_ in EXPECTED_TOKEN:
        for surface in SURFACES:
            op = presenter.project_event(event(type_), surface=surface)
            assert op["operation"] in TOKENS


def test_terminal_and_chat_are_not_prose():
    for surface in ("terminal", "chat"):
        op = presenter.project_event(event("branch_completed"), surface=surface)
        assert set(op) == CORE_FIELDS
        text = dump(op).lower()
        for word in ("because", "since", "probably", "seems", "likely", "should", "maybe"):
            assert word not in text


def test_dashboard_may_add_a_factual_phrase_but_never_rationale():
    op = presenter.project_event(event("branch_completed"), surface="dashboard")
    assert op["operation"] == "BRANCH"
    assert op["operation_text"] == "branch completed"
    text = op["operation_text"].lower()
    for word in ("because", "since", "probably", "seems", "likely", "should", "maybe", "inferred"):
        assert word not in text
    # terminal/chat carry no operation_text at all
    for surface in ("terminal", "chat"):
        assert "operation_text" not in presenter.project_event(event("branch_completed"), surface=surface)


def test_state_is_a_short_lifecycle_word():
    assert presenter.project_event(event("run_started"), surface="chat")["state"] == "started"
    assert presenter.project_event(event("candidate_selected"), surface="chat")["state"] == "running"
    assert presenter.project_event(event("run_completed"), surface="terminal")["state"] == "completed"
    assert presenter.project_event(event("run_failed"), surface="terminal")["state"] == "failed"
    state = presenter.project_event(event("usage_recorded"), surface="terminal")["state"]
    assert state == "recorded"


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------


@pytest.mark.parametrize("surface", ["html", "", None, "TERMINAL", 3, {"terminal": 1}])
def test_unknown_surface_returns_none(surface):
    assert presenter.project_event(event(), surface=surface) is None


@pytest.mark.parametrize("type_", ["thought", "raw_prompt", "token", "", None, 7])
def test_unknown_event_type_returns_none(type_):
    assert presenter.project_event({"type": type_, "run_id": "r", "seq": 0}, surface="chat") is None


@pytest.mark.parametrize("bad", [None, [], "run_started", 3, object()])
def test_non_dict_event_returns_none(bad):
    assert presenter.project_event(bad, surface="terminal") is None


@pytest.mark.parametrize("seq", [-1, -99, True, False, "3", 3.0, None])
def test_seq_must_be_a_nonnegative_int(seq):
    assert presenter.project_event(event(seq=seq), surface="terminal") is None


@pytest.mark.parametrize("run_id", ["", "   ", None, 7, [], {}])
def test_run_id_must_be_nonempty(run_id):
    assert presenter.project_event(event(run_id=run_id), surface="terminal") is None


def test_missing_run_id_or_seq_is_refused():
    assert presenter.project_event({"type": "run_started", "seq": 0}, surface="chat") is None
    assert presenter.project_event({"type": "run_started", "run_id": "r"}, surface="chat") is None


# --------------------------------------------------------------------------
# redaction
# --------------------------------------------------------------------------


def test_no_banned_key_or_secret_value_survives_projection():
    op = presenter.project_event(leaky_event(), surface="terminal")
    assert op is not None
    payload = dump(op)
    for key in BANNED_KEYS:
        assert key not in payload, key
    for value in SECRETS:
        assert value not in payload, value
    assert op["source_ids"] == ["src-a", "src-b"]
    assert op["candidate_ids"] == ["cand-1"]


def test_nested_exfiltration_is_structural_not_pattern_matched():
    """Secret-shaped text inside an allowlisted id is refused, not escaped."""
    ev = event(
        "source_selected",
        source_ids=["src-ok", "sk-live-TOPSECRET-001", "api_key"],
        candidate_ids=[{"id": "cand-ok", "reasoning": SECRETS[3]}, 42, None],
    )
    op = presenter.project_event(ev, surface="dashboard")
    payload = dump(op)
    for key in BANNED_KEYS:
        assert key not in payload
    for value in SECRETS:
        assert value not in payload
    assert op["source_ids"] == ["src-ok"]
    assert op["candidate_ids"] == ["cand-ok", "42"]


def test_nested_source_and_candidate_objects_contribute_ids_only():
    """An event may carry objects, not just id lists. Only their id survives."""
    ev = event(
        "branch_completed",
        sources=[
            {"id": "src-nested-1", "api_key": SECRETS[0],
             "private_memory": {"entry": SECRETS[2]}, "title": "x"},
            {"id": "src-nested-2", "prompt": SECRETS[3], "reasoning": SECRETS[3]},
            {"id": "sk-live-TOPSECRET-001"},
            {"no_id": "dropped"},
            "src-nested-3",
        ],
        candidates=[
            {"id": "cand-nested-1", "chain_of_thought": SECRETS[3]},
            {"id": {"api_key": SECRETS[0]}},
        ],
    )
    op = presenter.project_event(ev, surface="terminal")
    assert op["source_ids"] == ["src-nested-1", "src-nested-2", "src-nested-3"]
    assert op["candidate_ids"] == ["cand-nested-1"]
    payload = dump(op)
    for key in BANNED_KEYS:
        assert key not in payload
    for value in SECRETS:
        assert value not in payload
    for dropped in ("title", "no_id", "entry"):
        assert dropped not in payload


def test_scalar_source_and_candidate_ids_are_accepted():
    op = presenter.project_event(
        event("source_selected", source_id="src-solo", candidate_id="cand-solo"),
        surface="chat",
    )
    assert op["source_ids"] == ["src-solo"]
    assert op["candidate_ids"] == ["cand-solo"]
    assert presenter.project_event(event("source_selected", source_id={"id": "src-n"}), surface="chat")["source_ids"] == ["src-n"]


def test_usage_keeps_only_the_four_allowed_numbers():
    op = presenter.project_event(
        event("usage_recorded", usage={"input_tokens": 1, "output_tokens": 2,
                                       "total_tokens": 3, "cost_usd": 0.5,
                                       "provider": "openai", "api_key": SECRETS[0],
                                       "model": "x", "cache": {"api_key": SECRETS[0]}}),
        surface="chat",
    )
    assert op["usage"] == {"input_tokens": 1, "output_tokens": 2,
                           "total_tokens": 3, "cost_usd": 0.5}
    assert SECRETS[0] not in dump(op)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, "12", True, None])
def test_non_finite_usage_is_dropped(value):
    op = presenter.project_event(
        event("usage_recorded", usage={"input_tokens": value, "total_tokens": 4}),
        surface="terminal",
    )
    assert op["usage"] == {"total_tokens": 4}


def test_at_never_becomes_wall_clock_and_nan_is_dropped():
    op = presenter.project_event(event(at=math.nan), surface="terminal")
    assert op["at"] is None
    assert presenter.project_event(event(at="2026-01-01T00:00:00Z"), surface="chat")["at"] == "2026-01-01T00:00:00Z"


def test_status_is_sanitized():
    for status in (SECRETS[0], "", 5, ["running"], {"api_key": SECRETS[0]}):
        op = presenter.project_event(event(status=status), surface="terminal")
        assert op["status"] in ("running", "started", "completed", "failed")
        assert SECRETS[0] not in dump(op)


# --------------------------------------------------------------------------
# determinism and strict JSON
# --------------------------------------------------------------------------


def test_repeated_calls_are_byte_identical():
    ev = leaky_event()
    first = [dump(presenter.project_event(ev, surface=s)) for s in SURFACES]
    for _ in range(20):
        assert [dump(presenter.project_event(ev, surface=s)) for s in SURFACES] == first


def test_output_is_strict_json():
    op = presenter.project_event(leaky_event("usage_recorded"), surface="dashboard")
    payload = dump(op)
    assert payload == dump(presenter.project_event(leaky_event("usage_recorded"), surface="dashboard"))
    assert "NaN" not in payload and "Infinity" not in payload


def test_projection_does_not_mutate_the_input_event():
    ev = leaky_event()
    before = json.dumps(ev, sort_keys=True, default=str)
    presenter.project_event(ev, surface="terminal")
    presenter.normalize_events([ev, ev], surface="terminal")
    assert json.dumps(ev, sort_keys=True, default=str) == before


# --------------------------------------------------------------------------
# normalization
# --------------------------------------------------------------------------


def test_normalize_sorts_by_run_then_seq_without_wall_clock(monkeypatch):
    import time

    def boom(*a, **k):
        raise AssertionError("normalize_events must not read the wall clock")

    monkeypatch.setattr(time, "time", boom)
    monkeypatch.setattr(time, "time_ns", boom)

    events = [
        event("run_started", run_id="run-b", seq=1),
        event("run_completed", run_id="run-a", seq=9),
        event("run_started", run_id="run-a", seq=0),
        event("candidate_selected", run_id="run-b", seq=0),
    ]
    ops = presenter.normalize_events(events, surface="terminal")
    assert [(o["run_id"], o["seq"]) for o in ops] == [
        ("run-a", 0), ("run-a", 9), ("run-b", 0), ("run-b", 1),
    ]
    assert [o["operation"] for o in ops] == ["START", "DONE", "SELECT", "START"]


def test_normalize_drops_invalid_and_unknown_events():
    events = [
        event("run_started", seq=0),
        event("run_started", seq=-1),
        event("run_started", seq=True),
        event("run_started", seq="2"),
        event("run_started", run_id=""),
        {"type": "telepathy", "run_id": "run-1", "seq": 1},
        "not an event",
        None,
        event("run_completed", seq=1),
    ]
    ops = presenter.normalize_events(events, surface="chat")
    assert [(o["seq"], o["type"]) for o in ops] == [(0, "run_started"), (1, "run_completed")]


def test_normalize_on_unknown_surface_yields_nothing():
    assert presenter.normalize_events([event()], surface="html") == []
    assert presenter.normalize_events([event()], surface=None) == []
    assert presenter.normalize_events(None, surface="chat") == []
    assert presenter.normalize_events("nope", surface="chat") == []


def test_normalize_preserves_latest_status_after_terminal_event():
    events = [
        event("run_started", seq=0, status="started"),
        event("branch_started", seq=1, status="running"),
        event("run_completed", seq=2, status="completed"),
        event("usage_recorded", seq=3, status=None),
        event("feedback_recorded", seq=4),
    ]
    ops = presenter.normalize_events(events, surface="dashboard")
    assert [o["status"] for o in ops] == [
        "started", "running", "completed", "completed", "completed",
    ]


def test_normalize_preserves_failed_status():
    ops = presenter.normalize_events(
        [event("run_started", seq=0), event("run_failed", seq=5), event("usage_recorded", seq=6)],
        surface="terminal",
    )
    assert [o["status"] for o in ops] == ["started", "failed", "failed"]
    assert [o["operation"] for o in ops] == ["START", "FAIL", "USAGE"]


def test_normalize_is_stable_and_does_not_leak():
    evs = [leaky_event("branch_started"), leaky_event("candidate_selected"), leaky_event("run_failed")]
    for ev, i in zip(evs, range(3)):
        ev["seq"] = i
    first = [dump(o) for o in presenter.normalize_events(evs, surface="terminal")]
    for _ in range(10):
        assert [dump(o) for o in presenter.normalize_events(evs, surface="terminal")] == first
    joined = "".join(first)
    for key in BANNED_KEYS:
        assert key not in joined
    for value in SECRETS:
        assert value not in joined


def test_normalize_tie_breaks_equal_seq_by_source_order():
    events = [
        event("source_selected", seq=2, source_ids=["second"]),
        event("source_selected", seq=2, source_ids=["first"]),
    ]
    ops = presenter.normalize_events(events, surface="chat")
    assert [o["source_ids"] for o in ops] == [["second"], ["first"]]


def test_normalize_surfaces_are_independent_copies():
    events = [event("run_started", seq=0)]
    a = presenter.normalize_events(events, surface="terminal")
    b = presenter.normalize_events(events, surface="dashboard")
    assert "operation_text" not in a[0]
    assert "operation_text" in b[0]
