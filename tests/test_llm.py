"""The auxiliary adapter keeps its promises: few calls, short waits, named failures.

Every host here is a fake. No test reaches a model, a network or Hermes.
"""
from __future__ import annotations

import asyncio
import gc
import os
import sys
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm import (  # noqa: E402
    BUDGET,
    ERROR,
    INVALID,
    MAX_ERROR_CHARS,
    OK,
    TIMEOUT,
    BranchResult,
    LlmBudget,
    Usage,
    generate_structured,
)

SCHEMA = {
    "type": "object",
    "required": ["title", "mood"],
    "properties": {"title": {"type": "string"}, "mood": {"type": "string"}},
}
INSTRUCTIONS = "Read the material and name the scene. Stay literal."


def run(coro):
    """pytest-asyncio is not installed here; one loop per test is enough."""
    return asyncio.run(coro)


def budget(**overrides) -> LlmBudget:
    values = {"max_calls": 3, "max_output_tokens": 200, "timeout_seconds": 2.0}
    values.update(overrides)
    return LlmBudget(**values)


@dataclass
class FakeResult:
    text: str = '{"title": "a room", "mood": "quiet"}'
    parsed: Optional[Any] = field(default_factory=lambda: {"title": "a room", "mood": "quiet"})
    usage: Optional[Any] = None
    provider: str = "fake-provider"
    model: str = "fake-model"


class FakeHost:
    """Records every call; answers, sleeps or raises by branch id."""

    def __init__(self, responder=None, delay: float = 0.0):
        self.calls: List[Dict[str, Any]] = []
        self.responder = responder
        self.delay = delay
        self.active = 0
        self.peak = 0

    async def acomplete_structured(self, **kwargs):
        self.calls.append(kwargs)
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            if self.responder is not None:
                return self.responder(kwargs)
            return FakeResult()
        finally:
            self.active -= 1


def branch_of(call: Dict[str, Any]) -> str:
    for line in call["instructions"].splitlines():
        if line.startswith("Branch: "):
            return line[len("Branch: "):]
    raise AssertionError("branch marker missing from instructions")


def by_id(results: List[BranchResult]) -> Dict[str, BranchResult]:
    return {result.branch_id: result for result in results}


# ------------------------------------------------------------------ the budget

@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_calls": 0, "max_output_tokens": 10, "timeout_seconds": 1},
        {"max_calls": 1, "max_output_tokens": 0, "timeout_seconds": 1},
        {"max_calls": 1, "max_output_tokens": 10, "timeout_seconds": 0},
        {"max_calls": 1, "max_output_tokens": 10, "timeout_seconds": -1},
        {"max_calls": True, "max_output_tokens": 10, "timeout_seconds": 1},
        {"max_calls": 1, "max_output_tokens": 10, "timeout_seconds": 1, "max_concurrency": 0},
    ],
)
def test_budget_rejects_values_that_are_not_ceilings(kwargs):
    with pytest.raises(ValueError):
        LlmBudget(**kwargs)


def test_budget_is_per_call_not_a_financial_claim():
    b = budget()
    assert (b.max_calls, b.max_output_tokens, b.timeout_seconds) == (3, 200, 2.0)
    assert not hasattr(b, "max_cost")


# -------------------------------------------------------------- usage and shape

def test_usage_is_read_from_the_host_result():
    class Result:
        provider = "fake"
        model = "model-1"
        usage = {"input_tokens": 11, "output_tokens": 7, "cost_usd": 0.0002}

    usage = Usage.from_host_result(Result())
    assert (usage.input_tokens, usage.output_tokens, usage.total_tokens) == (11, 7, 18)
    assert usage.cost_usd == pytest.approx(0.0002)
    assert (usage.provider, usage.model) == ("fake", "model-1")


def test_missing_usage_is_zero_and_unknown_never_invented():
    usage = Usage.from_host_result(FakeResult(usage=None))
    assert usage == Usage()
    assert usage.total_tokens == 0
    assert usage.cost_usd is None
    assert (usage.provider, usage.model) == ("unknown", "unknown")


def test_nonsense_usage_values_stay_zero():
    class Result:
        provider = ""
        model = 42
        usage = {"input_tokens": -5, "output_tokens": "many", "total_tokens": 3, "cost_usd": -1}

    usage = Usage.from_host_result(Result())
    assert (usage.input_tokens, usage.output_tokens) == (0, 0)
    # the host did report a total; it is kept, not recomputed into a lie
    assert usage.total_tokens == 3
    assert usage.cost_usd is None
    assert (usage.provider, usage.model) == ("unknown", "unknown")


def test_usage_refuses_negative_tokens():
    with pytest.raises(ValueError):
        Usage(input_tokens=-1)


def test_branch_result_refuses_unknown_status():
    with pytest.raises(ValueError):
        BranchResult("a", "maybe")


# ------------------------------------------------------------------ the happy path

def test_each_branch_gets_its_own_blocks_and_its_own_instructions():
    host = FakeHost()
    results = run(
        generate_structured(
            host,
            instructions=INSTRUCTIONS,
            inputs={"calm": "a still lake", "tense": "a closing door"},
            json_schema=SCHEMA,
            branches=["calm", "tense"],
            budget=budget(max_calls=2),
            purpose="antemuse.scene",
            task="name_scene",
        )
    )

    assert [r.branch_id for r in results] == ["calm", "tense"]
    assert [r.status for r in results] == [OK, OK]
    assert all(r.parsed == {"title": "a room", "mood": "quiet"} for r in results)

    calls = {branch_of(call): call for call in host.calls}
    assert calls["calm"]["input"] == [{"type": "text", "text": "a still lake"}]
    assert calls["tense"]["input"] == [{"type": "text", "text": "a closing door"}]
    assert "Branch: calm" in calls["calm"]["instructions"]
    assert "Branch: tense" in calls["tense"]["instructions"]
    assert calls["calm"]["instructions"] != calls["tense"]["instructions"]
    assert all(call["instructions"].startswith(INSTRUCTIONS) for call in host.calls)


def test_budget_is_passed_and_provider_is_not_overridden():
    host = FakeHost()
    run(
        generate_structured(
            host,
            instructions=INSTRUCTIONS,
            inputs=["material"],
            json_schema=SCHEMA,
            branches=["only"],
            budget=budget(max_calls=1, max_output_tokens=64, timeout_seconds=1.5),
            purpose="antemuse.scene",
            task="name_scene",
        )
    )

    call = host.calls[0]
    assert call["max_tokens"] == 64
    assert call["timeout"] == 1.5
    assert call["purpose"] == "antemuse.scene"
    assert call["task"] == "name_scene"
    assert call["json_schema"] is SCHEMA
    assert "provider" not in call and "model" not in call
    assert "agent_id" not in call and "profile" not in call


def test_branches_run_concurrently():
    host = FakeHost(delay=0.05)
    results = run(
        generate_structured(
            host,
            instructions=INSTRUCTIONS,
            inputs=["one", "two", "three"],
            json_schema=SCHEMA,
            branches=["a", "b", "c"],
            budget=budget(max_calls=3, timeout_seconds=2.0),
        )
    )
    assert [r.status for r in results] == [OK, OK, OK]
    assert host.peak == 3


def test_optional_concurrency_ceiling_is_respected():
    host = FakeHost(delay=0.03)
    run(
        generate_structured(
            host,
            instructions=INSTRUCTIONS,
            inputs=["one", "two", "three", "four"],
            json_schema=SCHEMA,
            branches=["a", "b", "c", "d"],
            budget=budget(max_calls=4, timeout_seconds=2.0, max_concurrency=2),
        )
    )
    assert host.peak == 2
    assert len(host.calls) == 4


# ------------------------------------------------- the deadline starts at the call

def no_unawaited(caught) -> None:
    leaks = [w for w in caught if "never awaited" in str(w.message)]
    assert not leaks, [str(w.message) for w in leaks]


def test_queue_time_is_not_charged_to_the_call():
    """Four healthy branches behind two slots: waiting is not spending the budget."""
    host = FakeHost(delay=0.2)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        results = run(
            generate_structured(
                host,
                instructions=INSTRUCTIONS,
                inputs=["one", "two", "three", "four"],
                json_schema=SCHEMA,
                branches=["a", "b", "c", "d"],
                budget=budget(max_calls=4, timeout_seconds=0.3, max_concurrency=2),
            )
        )
        gc.collect()

    # Each call takes 0.2s, well inside the 0.3s timeout. The second pair only
    # starts after the first pair finishes, so a deadline measured from enqueue
    # would expire while they run -- and nothing about them is late.
    assert [r.status for r in results] == [OK, OK, OK, OK]
    assert all(r.parsed == {"title": "a room", "mood": "quiet"} for r in results)
    assert all(r.error is None for r in results)
    assert host.peak == 2
    assert {branch_of(call) for call in host.calls} == {"a", "b", "c", "d"}
    no_unawaited(caught)


def test_a_branch_queued_behind_a_slow_sibling_is_invoked_and_named():
    """A branch cancelled while queued must not become a fabricated timeout."""

    class SlowFirst:
        """Calls are recorded on entry, so a cancelled call still shows it ran."""

        def __init__(self):
            self.calls: List[Dict[str, Any]] = []

        async def acomplete_structured(self, **kwargs):
            self.calls.append(kwargs)
            if branch_of(kwargs) == "slow":
                await asyncio.sleep(0.3)
            return FakeResult()

    host = SlowFirst()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        results = by_id(
            run(
                generate_structured(
                    host,
                    instructions=INSTRUCTIONS,
                    inputs={"slow": "hold", "quick": "go"},
                    json_schema=SCHEMA,
                    branches=["slow", "quick"],
                    budget=budget(max_calls=2, timeout_seconds=0.1, max_concurrency=1),
                )
            )
        )
        gc.collect()

    # The slow call spends its own deadline and times out; the second branch
    # must then actually run, on its own clock, and answer for itself.
    assert results["slow"].status == TIMEOUT
    assert results["quick"].status == OK
    assert results["quick"].parsed == {"title": "a room", "mood": "quiet"}
    assert results["quick"].error is None
    assert [branch_of(call) for call in host.calls] == ["slow", "quick"]
    no_unawaited(caught)


# -------------------------------------------------------------- bad model output

def test_missing_required_key_is_invalid_with_raw_text_kept():
    host = FakeHost(responder=lambda call: FakeResult(text='{"title": "a room"}', parsed={"title": "a room"}))
    result = run(
        generate_structured(
            host,
            instructions=INSTRUCTIONS,
            inputs=["material"],
            json_schema=SCHEMA,
            branches=["loose"],
            budget=budget(max_calls=1),
        )
    )[0]

    assert result.status == INVALID
    assert result.parsed is None
    assert result.raw_text == '{"title": "a room"}'
    assert result.error is not None
    assert "mood" in result.error
    assert "missing required key" in result.error


def test_parsed_that_is_not_an_object_is_invalid():
    host = FakeHost(responder=lambda call: FakeResult(text='["a room"]', parsed=["a room"]))
    result = run(
        generate_structured(
            host,
            instructions=INSTRUCTIONS,
            inputs=["material"],
            json_schema=SCHEMA,
            branches=["listy"],
            budget=budget(max_calls=1),
        )
    )[0]

    assert result.status == INVALID
    assert result.parsed is None
    assert result.raw_text == '["a room"]'
    assert result.usage == Usage()


def test_empty_host_result_is_invalid_not_invented():
    host = FakeHost(responder=lambda call: None)
    result = run(
        generate_structured(
            host,
            instructions=INSTRUCTIONS,
            inputs=["material"],
            json_schema=SCHEMA,
            branches=["empty"],
            budget=budget(max_calls=1),
        )
    )[0]

    assert result.status == INVALID
    assert result.parsed is None
    assert result.raw_text == ""


def test_one_timeout_does_not_cancel_its_siblings():
    class MixedHost(FakeHost):
        async def acomplete_structured(self, **kwargs):
            if branch_of(kwargs) == "slow":
                await asyncio.sleep(0.2)
            return await super().acomplete_structured(**kwargs)

    host = MixedHost()
    results = by_id(
        run(
            generate_structured(
                host,
                instructions=INSTRUCTIONS,
                inputs={"slow": "hold", "quick": "go"},
                json_schema=SCHEMA,
                branches=["slow", "quick"],
                budget=budget(max_calls=2, timeout_seconds=0.05),
            )
        )
    )
    assert results["slow"].status == TIMEOUT
    assert results["quick"].status == OK


# -------------------------------------------------------------- error hygiene

def test_exception_text_is_redacted_truncated_and_prompt_free():
    def responder(call):
        fake_key = "sk" + "-" + "live" + "0123456789abcdef"
        raise RuntimeError(
            "provider rejected "
            + call["instructions"]
            + " material: a still lake "
            + "Bearer abcdef123456 "
            + "api_key=SUPERSECRET "
            + fake_key
            + " "
            + "z" * 600
        )

    host = FakeHost(responder=responder)
    result = run(
        generate_structured(
            host,
            instructions=INSTRUCTIONS,
            inputs=["a still lake"],
            json_schema=SCHEMA,
            branches=["secretive"],
            budget=budget(max_calls=1),
        )
    )[0]

    assert result.status == ERROR
    assert result.parsed is None
    assert result.raw_text == ""
    error = result.error
    assert error is not None
    assert len(error) <= MAX_ERROR_CHARS
    assert error.endswith("...")
    assert "SUPERSECRET" not in error
    assert "abcdef123456" not in error
    assert ("sk" + "-" + "live" + "0123456789abcdef") not in error
    assert "[redacted]" in error
    assert "Bearer [redacted]" in error
    # the instructions and the input block are request material, not error text
    assert INSTRUCTIONS not in error
    assert "a still lake" not in error
    assert "[prompt]" in error


def test_short_exception_keeps_its_message():
    host = FakeHost(responder=lambda call: (_ for _ in ()).throw(ValueError("no capacity")))
    result = run(
        generate_structured(
            host,
            instructions=INSTRUCTIONS,
            inputs=["material"],
            json_schema=SCHEMA,
            branches=["refused"],
            budget=budget(max_calls=1),
        )
    )[0]

    assert result.status == ERROR
    assert result.error == "ValueError: no capacity"


# ------------------------------------------------------------- budget skips

def test_branches_past_max_calls_are_recorded_not_run():
    host = FakeHost()
    results = run(
        generate_structured(
            host,
            instructions=INSTRUCTIONS,
            inputs={"a": "one", "b": "two", "c": "three", "d": "four"},
            json_schema=SCHEMA,
            branches=["a", "b", "c", "d"],
            budget=budget(max_calls=2),
        )
    )

    assert [r.branch_id for r in results] == ["a", "b", "c", "d"]
    assert [r.status for r in results] == [OK, OK, BUDGET, BUDGET]
    assert len(host.calls) == 2
    assert {branch_of(call) for call in host.calls} == {"a", "b"}
    for skipped in results[2:]:
        assert skipped.parsed is None
        assert skipped.raw_text == ""
        assert skipped.usage == Usage()
        assert skipped.error is not None
        assert "max_calls=2" in skipped.error


def test_call_count_never_exceeds_max_calls():
    host = FakeHost()
    run(
        generate_structured(
            host,
            instructions=INSTRUCTIONS,
            inputs=[f"material {i}" for i in range(10)],
            json_schema=SCHEMA,
            branches=[f"b{i}" for i in range(10)],
            budget=budget(max_calls=1),
        )
    )
    assert len(host.calls) == 1


# ------------------------------------------------------------- caller mistakes

def test_string_branches_are_a_count_not_a_sequence_of_characters():
    host = FakeHost()
    results = run(
        generate_structured(
            host,
            instructions=INSTRUCTIONS,
            inputs=["one", "two"],
            json_schema=SCHEMA,
            branches=2,
            budget=budget(max_calls=2),
        )
    )
    assert [r.branch_id for r in results] == ["branch-1", "branch-2"]
    assert all(r.status == OK for r in results)


def test_duplicate_branch_ids_are_refused():
    host = FakeHost()
    with pytest.raises(ValueError, match="duplicate"):
        run(
            generate_structured(
                host,
                instructions=INSTRUCTIONS,
                inputs=["one", "two"],
                json_schema=SCHEMA,
                branches=["same", "same"],
                budget=budget(max_calls=2),
            )
        )


def test_missing_input_for_a_branch_is_refused():
    host = FakeHost()
    with pytest.raises(ValueError, match="no input block"):
        run(
            generate_structured(
                host,
                instructions=INSTRUCTIONS,
                inputs={"a": "one"},
                json_schema=SCHEMA,
                branches=["a", "b"],
                budget=budget(max_calls=2),
            )
        )


def test_input_count_must_match_branch_count():
    host = FakeHost()
    with pytest.raises(ValueError, match="entries"):
        run(
            generate_structured(
                host,
                instructions=INSTRUCTIONS,
                inputs=["one"],
                json_schema=SCHEMA,
                branches=["a", "b"],
                budget=budget(max_calls=2),
            )
        )


def test_empty_instructions_are_refused():
    host = FakeHost()
    with pytest.raises(ValueError, match="instructions"):
        run(
            generate_structured(
                host,
                instructions="   ",
                inputs=["one"],
                json_schema=SCHEMA,
                branches=["a"],
                budget=budget(max_calls=1),
            )
        )


def test_a_host_without_the_method_is_refused():
    with pytest.raises(TypeError, match="acomplete_structured"):
        run(
            generate_structured(
                object(),
                instructions=INSTRUCTIONS,
                inputs=["one"],
                json_schema=SCHEMA,
                branches=["a"],
                budget=budget(max_calls=1),
            )
        )
