"""Async independent structured branch orchestration.

One task, several sources, one branch per source. Each branch sees only its own
source artifact and the task brief; no branch sees another branch's candidates
or output. The branches are run through ``core.llm.generate_structured`` with a
fixed schema, and the results are collected into an ``OrchestrationResult``.

Selection is delegated to ``core.collider.select_sources`` with the ``fresh``
strategy, so the same seed and source bank reproduce the same branches. Nothing
here scores, ranks, or judges a candidate: ``selected_candidate_ids`` is the
list of branch ids that came back ``ok``, in branch order, and
``selected_status`` is always ``"unjudged"``.

No provider or model is chosen here. The host owns those; this module passes
only the instructions, per-branch inputs, schema, branch ids, budget, purpose
and task name through to ``core.llm``.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from . import collider, llm

#: The four fields every branch must return, plus the source ids it drew on.
REQUIRED_CANDIDATE_FIELDS: Tuple[str, ...] = (
    "thesis",
    "mechanism",
    "application",
    "first_step",
    "source_ids",
)

#: The schema handed to the host. Top-level required list names the four
#: candidate fields; ``source_ids`` is required too so a branch cannot drop
#: the provenance of its own answer.
CANDIDATE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": list(REQUIRED_CANDIDATE_FIELDS),
    "properties": {
        "thesis": {"type": "string"},
        "mechanism": {"type": "string"},
        "application": {"type": "string"},
        "first_step": {"type": "string"},
        "source_ids": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}

#: Statuses an orchestration run can end in.
STATUS_OK = "ok"
STATUS_PARTIAL = "partial"
STATUS_ERROR = "error"

#: Selection is never a quality judgement.
SELECTED_STATUS_UNJUDGED = "unjudged"

INSTRUCTIONS_TEMPLATE = (
    "You are one independent branch of a structured idea-generation run. "
    "You see only the task brief and one source artifact; you do not see any "
    "other branch's candidates or output, and you must not assume they exist.\n\n"
    "Task brief:\n{brief}\n\n"
    "Source artifact mechanism:\n{mechanism}\n\n"
    "Source artifact bridge question:\n{bridge_question}\n\n"
    "Return exactly one JSON object with these fields:\n"
    "- thesis: the central claim this source supports for the task\n"
    "- mechanism: how the source's mechanism produces that claim\n"
    "- application: how the claim would be applied to the task\n"
    "- first_step: the smallest concrete next action\n"
    "- source_ids: the ids of the source artifacts you drew on (this branch's "
    "source id only)\n"
    "Do not include any other branch's candidates or outputs."
)


@dataclass(frozen=True)
class BranchResult:
    """One branch's outcome, enriched with the source ids it was given."""

    branch_id: str
    source_ids: Tuple[str, ...]
    status: str
    parsed: Optional[Any] = None
    raw_text: str = ""
    usage: llm.Usage = field(default_factory=llm.Usage)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status == llm.OK


@dataclass(frozen=True)
class OrchestrationResult:
    """The whole run: branches, selection, usage, and an optional error."""

    run_id: str
    task_id: str
    seed: Any
    status: str
    branches: Tuple[BranchResult, ...]
    selected_candidate_ids: Tuple[str, ...]
    selected_status: str
    usage: llm.Usage
    error: Optional[str] = None


# ------------------------------------------------------------------ helpers

def _require_task(task: Any) -> Tuple[str, str]:
    if not isinstance(task, Mapping):
        raise ValueError("task must be a mapping with id and brief")
    task_id = task.get("id")
    brief = task.get("brief")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("task.id must be a non-empty string")
    if not isinstance(brief, str) or not brief.strip():
        raise ValueError("task.brief must be a non-empty string")
    return task_id, brief


def _require_sources(sources: Any) -> List[Dict[str, Any]]:
    if isinstance(sources, (str, bytes)) or not isinstance(sources, Sequence):
        raise ValueError("sources must be a non-empty sequence of SourceArtifacts")
    records = list(sources)
    if not records:
        raise ValueError("sources must be a non-empty sequence of SourceArtifacts")
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("each source must be a mapping with id and family")
        source_id = record.get("id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("each source must carry a non-empty string id")
        for field_name in ("mechanism", "bridge_question"):
            value = record.get(field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"source {source_id!r} must carry non-empty {field_name}")
    return records


def _require_budget(budget: Any) -> llm.LlmBudget:
    if not isinstance(budget, llm.LlmBudget):
        raise ValueError("budget must be a core.llm.LlmBudget")
    return budget


def _branch_id(task_id: str, source_id: str) -> str:
    """A branch id that names both the task and the source, and is unique."""
    return f"{task_id}::{source_id}"


def _run_id(task_id: str, seed: Any, source_ids: Sequence[str]) -> str:
    """Deterministic from task id, seed, and the selected source ids in order."""
    payload = json.dumps(
        {"task_id": task_id, "seed": seed, "source_ids": list(source_ids)},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return "run-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _instructions_for(brief: str, source: Mapping[str, Any]) -> str:
    mechanism = source.get("mechanism", "")
    bridge_question = source.get("bridge_question", "")
    return INSTRUCTIONS_TEMPLATE.format(
        brief=brief,
        mechanism=mechanism,
        bridge_question=bridge_question,
    )


def _inputs_for(source: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """One branch's independent input blocks: its own source, nothing else."""
    return [
        {
            "type": "text",
            "text": (
                "Source artifact id: "
                + str(source.get("id", ""))
                + "\nMechanism: "
                + str(source.get("mechanism", ""))
                + "\nBridge question: "
                + str(source.get("bridge_question", ""))
            ),
        }
    ]


def _sum_usage(results: Sequence[BranchResult]) -> llm.Usage:
    """Sum actual usage; report cost only when every attempted branch reports it."""
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    attempted_results = [r for r in results if r.status != llm.BUDGET]
    for result in results:
        input_tokens += result.usage.input_tokens
        output_tokens += result.usage.output_tokens
        total_tokens += result.usage.total_tokens

    cost: Optional[float] = None
    if attempted_results and all(r.usage.cost_usd is not None for r in attempted_results):
        cost = float(sum(r.usage.cost_usd for r in attempted_results if r.usage.cost_usd is not None))

    return llm.Usage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cost_usd=cost,
    )


def _status_for(results: Sequence[BranchResult]) -> str:
    ok_count = sum(1 for r in results if r.ok)
    if ok_count == len(results) and results:
        return STATUS_OK
    if ok_count == 0:
        return STATUS_ERROR
    return STATUS_PARTIAL


# ------------------------------------------------------------------ the call

def branch_plan(
    task: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    *,
    seed: Any,
    count: int,
    strategy: str = "fresh",
    loved: Sequence[str] = (),
    liked: Sequence[str] = (),
) -> List[Dict[str, Any]]:
    """The exact branch requests ``orchestrate`` would send, without sending them.

    This exists so the offline evaluation runner cannot drift from production:
    condition F is meant to measure *this* branch construction, so it builds its
    requests here rather than re-deriving instruction and input shapes.
    """
    task_id, brief = _require_task(task)
    source_records = _require_sources(sources)
    selected = collider.select_sources(
        source_records,
        strategy=strategy,
        seed=seed,
        loved=list(loved) or None,
        liked=list(liked) or None,
        count=count,
    )
    return _branch_entries(task_id, brief, selected)


def _branch_entries(task_id: str, brief: str,
                    selected: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """The single place a branch's id, instruction, and inputs are built."""
    entries: List[Dict[str, Any]] = []
    for index, source in enumerate(selected):
        source_id = str(source["id"])
        entries.append({
            "branch_index": index,
            "branch_id": _branch_id(task_id, source_id),
            "source_id": source_id,
            "instruction": _instructions_for(brief, source),
            "inputs": _inputs_for(source),
        })
    return entries


async def orchestrate(
    host: Any,
    *,
    task: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    budget: llm.LlmBudget,
    seed: Any,
    purpose: Optional[str] = None,
    task_name: Optional[str] = None,
    strategy: str = "fresh",
    loved: Sequence[str] = (),
    liked: Sequence[str] = (),
) -> OrchestrationResult:
    """Run one independent branch per selected source and collect the results.

    Selection uses ``collider.select_sources`` with ``count=budget.max_calls``
    for execution. ``strategy`` defaults to ``fresh``; ``deepen`` and
    ``refresh`` filter families by the ids in ``loved``/``liked``, which is how
    a person's verdicts steer the next run. The remaining supplied sources are
    named as skipped branches; ``core.llm`` reports them as ``budget`` results,
    counting toward ``partial`` when any branch is ``ok``.

    Errors from source selection propagate as ``ValueError``.
    """
    task_id, brief = _require_task(task)
    source_records = _require_sources(sources)
    budget = _require_budget(budget)

    selected = collider.select_sources(
        source_records,
        strategy=strategy,
        seed=seed,
        loved=list(loved) or None,
        liked=list(liked) or None,
        count=budget.max_calls,
    )
    selected_ids = {artifact["id"] for artifact in selected}
    skipped = [artifact for artifact in source_records if artifact["id"] not in selected_ids]
    # Under ``fresh`` the unselected sources are deferred by the budget and are
    # named as skipped branches. Under ``deepen``/``refresh`` they were excluded
    # by the strategy itself, so calling them "skipped by budget" would be a lie.
    candidates = selected + skipped if strategy == "fresh" else list(selected)

    branch_ids: List[str] = []
    inputs: Dict[str, List[Dict[str, Any]]] = {}
    source_ids_by_branch: Dict[str, Tuple[str, ...]] = {}
    instructions_by_branch: Dict[str, str] = {}

    for entry in _branch_entries(task_id, brief, candidates):
        branch_id = entry["branch_id"]
        branch_ids.append(branch_id)
        inputs[branch_id] = entry["inputs"]
        source_ids_by_branch[branch_id] = (entry["source_id"],)
        instructions_by_branch[branch_id] = entry["instruction"]

    # Each branch receives its own source-specific instructions as well as its
    # own input blocks. The mapping keeps the mechanism and bridge question out
    # of every sibling branch while ``core.llm`` appends the branch marker.
    raw_results = await llm.generate_structured(
        host,
        instructions=instructions_by_branch,
        inputs=inputs,
        json_schema=CANDIDATE_SCHEMA,
        branches=branch_ids,
        budget=budget,
        purpose=purpose,
        task=task_name,
    )

    branches: List[BranchResult] = []
    for raw in raw_results:
        branches.append(
            BranchResult(
                branch_id=raw.branch_id,
                source_ids=source_ids_by_branch.get(raw.branch_id, ()),
                status=raw.status,
                parsed=raw.parsed,
                raw_text=raw.raw_text,
                usage=raw.usage,
                error=raw.error,
            )
        )

    selected_candidate_ids = tuple(b.branch_id for b in branches if b.ok)
    status = _status_for(branches)
    usage = _sum_usage(branches)
    run_id = _run_id(task_id, seed, [artifact["id"] for artifact in selected])

    return OrchestrationResult(
        run_id=run_id,
        task_id=task_id,
        seed=seed,
        status=status,
        branches=tuple(branches),
        selected_candidate_ids=selected_candidate_ids,
        selected_status=SELECTED_STATUS_UNJUDGED,
        usage=usage,
        error=None,
    )
