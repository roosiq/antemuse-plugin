"""Tests for core.orchestrator: independent branches, no network, no overrides."""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import collider, llm
from core.orchestrator import (
    CANDIDATE_SCHEMA,
    REQUIRED_CANDIDATE_FIELDS,
    SELECTED_STATUS_UNJUDGED,
    STATUS_ERROR,
    STATUS_OK,
    STATUS_PARTIAL,
    orchestrate,
)


# ------------------------------------------------------------------ fixtures

def _source(source_id: str, family: str = "fam") -> Dict[str, Any]:
    return {
        "id": source_id,
        "family": family,
        "mechanism": f"mechanism-{source_id}",
        "bridge_question": f"question-{source_id}",
    }


def _task() -> Dict[str, str]:
    return {"id": "task-1", "brief": "Design a calmer onboarding flow."}


def _budget(max_calls: int = 3) -> llm.LlmBudget:
    return llm.LlmBudget(
        max_calls=max_calls,
        max_output_tokens=256,
        timeout_seconds=5.0,
    )


def _candidate(source_id: str) -> Dict[str, Any]:
    return {
        "thesis": f"thesis-{source_id}",
        "mechanism": f"mechanism-{source_id}",
        "application": f"application-{source_id}",
        "first_step": f"first-step-{source_id}",
        "source_ids": [source_id],
    }


class _HostResult:
    def __init__(
        self,
        parsed: Optional[Any],
        *,
        text: str = "",
        usage: Optional[Dict[str, Any]] = None,
        provider: str = "fake-provider",
        model: str = "fake-model",
    ) -> None:
        self.parsed = parsed
        self.text = text
        self.usage = usage
        self.provider = provider
        self.model = model


class FakeHost:
    """A host that answers each branch with a candidate keyed by its source id.

    It records every call so tests can prove no provider/model override was
    passed and that each branch saw only its own input.
    """

    def __init__(
        self,
        *,
        fail_ids: Optional[set] = None,
        cost: Optional[float] = None,
        usage_per_call: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.fail_ids = fail_ids or set()
        self.cost = cost
        self.usage_per_call = usage_per_call

    async def acomplete_structured(self, **kwargs: Any) -> _HostResult:
        self.calls.append(kwargs)
        instructions = kwargs["instructions"]
        blocks = kwargs["input"]
        # The branch marker is appended by core.llm; recover the source id from
        # the branch's own input block, never from another branch.
        text = " ".join(b.get("text", "") for b in blocks if isinstance(b, dict))
        source_id = None
        for token in text.split():
            if token.startswith("id:") and len(token) > len("id:"):
                source_id = token[len("id:"):]
                break
        if source_id is None:
            # Fall back to the branch marker in the instructions.
            for line in instructions.splitlines():
                if line.startswith("Branch: "):
                    branch = line[len("Branch: "):]
                    source_id = branch.split("::", 1)[-1]
                    break
        assert source_id is not None

        if source_id in self.fail_ids:
            raise RuntimeError(f"host failed for {source_id}")

        usage = self.usage_per_call
        if usage is None:
            usage = {
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30,
                "cost_usd": self.cost,
            }
        return _HostResult(_candidate(source_id), text="{}", usage=usage)


# ------------------------------------------------------------------ tests

def test_orchestrate_returns_one_branch_per_selected_source() -> None:
    host = FakeHost()
    sources = [_source("s1"), _source("s2"), _source("s3")]
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=sources, budget=_budget(3), seed=7)
    )
    assert result.status == STATUS_OK
    assert len(result.branches) == 3
    assert {b.source_ids for b in result.branches} == {("s1",), ("s2",), ("s3",)}
    for branch in result.branches:
        assert branch.branch_id.startswith("task-1::")
        assert branch.branch_id.endswith(branch.source_ids[0])


def test_branch_ids_are_distinct_and_contain_task_and_source() -> None:
    host = FakeHost()
    sources = [_source("a"), _source("b")]
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=sources, budget=_budget(2), seed=1)
    )
    ids = [b.branch_id for b in result.branches]
    assert len(ids) == len(set(ids))
    for branch in result.branches:
        assert "task-1" in branch.branch_id
        assert branch.source_ids[0] in branch.branch_id


def test_each_branch_sees_only_its_own_source() -> None:
    host = FakeHost()
    sources = [_source("s1"), _source("s2")]
    asyncio.run(
        orchestrate(host, task=_task(), sources=sources, budget=_budget(2), seed=3)
    )
    assert len(host.calls) == 2
    for call in host.calls:
        text = " ".join(b.get("text", "") for b in call["input"])
        # Exactly one source id appears in this branch's input.
        present = [sid for sid in ("s1", "s2") if sid in text]
        assert len(present) == 1


def test_schema_required_fields_are_the_candidate_fields() -> None:
    required = CANDIDATE_SCHEMA["required"]
    for field in ("thesis", "mechanism", "application", "first_step"):
        assert field in required
    assert set(REQUIRED_CANDIDATE_FIELDS) <= set(required)


def test_schema_is_passed_to_host() -> None:
    host = FakeHost()
    asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1")], budget=_budget(1), seed=0)
    )
    assert host.calls[0]["json_schema"] is CANDIDATE_SCHEMA


def test_each_branch_instructions_carry_only_its_own_mechanism() -> None:
    host = FakeHost()
    sources = [_source("s1"), _source("s2")]
    asyncio.run(
        orchestrate(host, task=_task(), sources=sources, budget=_budget(2), seed=3)
    )
    assert len(host.calls) == 2
    for call in host.calls:
        instructions = call["instructions"]
        present = [sid for sid in ("s1", "s2") if f"mechanism-{sid}" in instructions]
        assert len(present) == 1
        assert "(see this branch's input block)" not in instructions


def test_missing_branch_instruction_mapping_raises() -> None:
    host = FakeHost()
    with pytest.raises(ValueError, match="missing instructions"):
        asyncio.run(
            llm.generate_structured(
                host,
                instructions={"only-branch": "do it"},
                inputs={"other-branch": ["x"]},
                json_schema=CANDIDATE_SCHEMA,
                branches=["other-branch"],
                budget=_budget(1),
            )
        )


def test_selected_source_ids_attached_to_branches() -> None:
    host = FakeHost()
    sources = [_source("s1"), _source("s2")]
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=sources, budget=_budget(2), seed=5)
    )
    for branch in result.branches:
        assert branch.source_ids == (branch.branch_id.split("::", 1)[1],)


def test_status_ok_when_all_branches_ok() -> None:
    host = FakeHost()
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1"), _source("s2")], budget=_budget(2), seed=0)
    )
    assert result.status == STATUS_OK


def test_status_partial_when_mixed() -> None:
    host = FakeHost(fail_ids={"s2"})
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1"), _source("s2")], budget=_budget(2), seed=0)
    )
    assert result.status == STATUS_PARTIAL
    assert len(result.selected_candidate_ids) == 1


def test_status_error_when_none_ok() -> None:
    host = FakeHost(fail_ids={"s1", "s2"})
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1"), _source("s2")], budget=_budget(2), seed=0)
    )
    assert result.status == STATUS_ERROR
    assert result.selected_candidate_ids == ()


def test_budget_skipping_counts_toward_partial() -> None:
    host = FakeHost()
    sources = [_source("s1"), _source("s2"), _source("s3")]
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=sources, budget=_budget(2), seed=0)
    )
    assert len(result.branches) == 3
    assert len(host.calls) == 2
    assert result.status == STATUS_PARTIAL
    assert sum(branch.status == llm.BUDGET for branch in result.branches) == 1


def test_budget_skipping_with_more_branches_than_calls() -> None:
    # Force more branches than max_calls by selecting all sources but capping calls.
    host = FakeHost()
    sources = [_source("s1"), _source("s2"), _source("s3")]
    # select_sources count=budget.max_calls, so branches == max_calls. To exercise
    # the budget path, call generate_structured directly with more branches.
    results = asyncio.run(
        llm.generate_structured(
            host,
            instructions="do it",
            inputs={f"b{i}": ["x"] for i in range(3)},
            json_schema=CANDIDATE_SCHEMA,
            branches=[f"b{i}" for i in range(3)],
            budget=_budget(2),
        )
    )
    statuses = [r.status for r in results]
    assert statuses.count(llm.BUDGET) == 1


def test_selected_status_is_unjudged() -> None:
    host = FakeHost()
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1")], budget=_budget(1), seed=0)
    )
    assert result.selected_status == SELECTED_STATUS_UNJUDGED


def test_selected_candidate_ids_are_ok_branch_ids_only() -> None:
    host = FakeHost(fail_ids={"s2"})
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1"), _source("s2")], budget=_budget(2), seed=0)
    )
    ok_ids = {b.branch_id for b in result.branches if b.ok}
    assert set(result.selected_candidate_ids) == ok_ids


def test_run_id_is_deterministic() -> None:
    host1 = FakeHost()
    host2 = FakeHost()
    sources = [_source("s1"), _source("s2")]
    r1 = asyncio.run(orchestrate(host1, task=_task(), sources=sources, budget=_budget(2), seed=42))
    r2 = asyncio.run(orchestrate(host2, task=_task(), sources=sources, budget=_budget(2), seed=42))
    assert r1.run_id == r2.run_id


def test_run_id_changes_with_seed() -> None:
    host1 = FakeHost()
    host2 = FakeHost()
    sources = [_source("s1"), _source("s2"), _source("s3")]
    r1 = asyncio.run(orchestrate(host1, task=_task(), sources=sources, budget=_budget(2), seed=1))
    r2 = asyncio.run(orchestrate(host2, task=_task(), sources=sources, budget=_budget(2), seed=2))
    assert r1.run_id != r2.run_id


def test_selection_is_deterministic() -> None:
    host1 = FakeHost()
    host2 = FakeHost()
    sources = [_source(f"s{i}") for i in range(6)]
    r1 = asyncio.run(orchestrate(host1, task=_task(), sources=sources, budget=_budget(3), seed=99))
    r2 = asyncio.run(orchestrate(host2, task=_task(), sources=sources, budget=_budget(3), seed=99))
    assert [b.source_ids for b in r1.branches] == [b.source_ids for b in r2.branches]


def test_usage_sums_actual_branch_usage() -> None:
    host = FakeHost()
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1"), _source("s2")], budget=_budget(2), seed=0)
    )
    assert result.usage.input_tokens == 20
    assert result.usage.output_tokens == 40
    assert result.usage.total_tokens == 60


def test_cost_included_when_every_ok_branch_reports_it() -> None:
    host = FakeHost(cost=0.01)
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1"), _source("s2")], budget=_budget(2), seed=0)
    )
    assert result.usage.cost_usd == pytest.approx(0.02)


def test_cost_includes_invalid_branch_after_billed_host_call() -> None:
    class PartiallyInvalidHost(FakeHost):
        async def acomplete_structured(self, **kwargs: Any) -> _HostResult:
            self.calls.append(kwargs)
            text = " ".join(b.get("text", "") for b in kwargs["input"])
            usage = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30, "cost_usd": 0.01}
            if "s2" in text:
                return _HostResult(None, text="not-json", usage=usage)
            return _HostResult(_candidate("s1"), text="{}", usage=usage)

    result = asyncio.run(
        orchestrate(
            PartiallyInvalidHost(),
            task=_task(),
            sources=[_source("s1"), _source("s2")],
            budget=_budget(2),
            seed=0,
        )
    )
    assert result.status == STATUS_PARTIAL
    assert {branch.status for branch in result.branches} == {llm.OK, llm.INVALID}
    assert result.usage.cost_usd == pytest.approx(0.02)


def test_cost_none_when_any_ok_branch_omits_it() -> None:
    class MixedCostHost(FakeHost):
        async def acomplete_structured(self, **kwargs: Any) -> _HostResult:
            result = await super().acomplete_structured(**kwargs)
            text = " ".join(b.get("text", "") for b in kwargs["input"])
            if "s2" in text:
                result.usage = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
            return result

    host = MixedCostHost(cost=0.01)
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1"), _source("s2")], budget=_budget(2), seed=0)
    )
    assert result.usage.cost_usd is None


def test_no_provider_or_model_override_kwargs() -> None:
    host = FakeHost()
    asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1")], budget=_budget(1), seed=0)
    )
    call = host.calls[0]
    assert "provider" not in call
    assert "model" not in call
    assert "api_key" not in call


def test_purpose_and_task_name_passed_through() -> None:
    host = FakeHost()
    asyncio.run(
        orchestrate(
            host,
            task=_task(),
            sources=[_source("s1")],
            budget=_budget(1),
            seed=0,
            purpose="orchestrate",
            task_name="onboarding",
        )
    )
    assert host.calls[0]["purpose"] == "orchestrate"
    assert host.calls[0]["task"] == "onboarding"


def test_empty_sources_raises() -> None:
    host = FakeHost()
    with pytest.raises(ValueError):
        asyncio.run(
            orchestrate(host, task=_task(), sources=[], budget=_budget(1), seed=0)
        )


def test_task_missing_id_raises() -> None:
    host = FakeHost()
    with pytest.raises(ValueError):
        asyncio.run(
            orchestrate(host, task={"brief": "x"}, sources=[_source("s1")], budget=_budget(1), seed=0)
        )


def test_task_missing_brief_raises() -> None:
    host = FakeHost()
    with pytest.raises(ValueError):
        asyncio.run(
            orchestrate(host, task={"id": "t"}, sources=[_source("s1")], budget=_budget(1), seed=0)
        )


def test_bad_budget_raises() -> None:
    host = FakeHost()
    with pytest.raises(ValueError):
        asyncio.run(
            orchestrate(host, task=_task(), sources=[_source("s1")], budget="nope", seed=0)  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("field_name", ["mechanism", "bridge_question"])
def test_missing_source_text_fields_raise_value_error(field_name: str) -> None:
    source = _source("s1")
    del source[field_name]
    with pytest.raises(ValueError, match=field_name):
        asyncio.run(
            orchestrate(FakeHost(), task=_task(), sources=[source], budget=_budget(1), seed=0)
        )


def test_source_selection_error_propagates() -> None:
    host = FakeHost()
    # A source with no family makes select_sources raise ValueError.
    bad = {"id": "s1"}
    with pytest.raises(ValueError):
        asyncio.run(
            orchestrate(host, task=_task(), sources=[bad], budget=_budget(1), seed=0)
        )


def test_branch_parsed_candidate_is_preserved() -> None:
    host = FakeHost()
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1")], budget=_budget(1), seed=0)
    )
    branch = result.branches[0]
    assert branch.ok
    assert branch.parsed == _candidate("s1")


def test_branch_error_is_sanitized_and_short() -> None:
    host = FakeHost(fail_ids={"s1"})
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1")], budget=_budget(1), seed=0)
    )
    branch = result.branches[0]
    assert branch.status == llm.ERROR
    assert branch.error is not None
    assert len(branch.error) <= llm.MAX_ERROR_CHARS


def test_no_hidden_selection_or_fabricated_candidates() -> None:
    host = FakeHost(fail_ids={"s1"})
    result = asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1")], budget=_budget(1), seed=0)
    )
    # The failed branch has no parsed candidate and is not selected.
    assert result.branches[0].parsed is None
    assert result.selected_candidate_ids == ()


def test_instructions_mention_brief_and_schema_fields() -> None:
    host = FakeHost()
    asyncio.run(
        orchestrate(host, task=_task(), sources=[_source("s1")], budget=_budget(1), seed=0)
    )
    instructions = host.calls[0]["instructions"]
    assert "Design a calmer onboarding flow." in instructions
    for field in ("thesis", "mechanism", "application", "first_step", "source_ids"):
        assert field in instructions


def test_branch_instructions_do_not_include_other_branches() -> None:
    host = FakeHost()
    sources = [_source("s1"), _source("s2")]
    asyncio.run(
        orchestrate(host, task=_task(), sources=sources, budget=_budget(2), seed=0)
    )
    for call in host.calls:
        text = " ".join(b.get("text", "") for b in call["input"])
        # Only one source id in this branch's input.
        assert sum(1 for sid in ("s1", "s2") if sid in text) == 1
