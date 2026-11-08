"""Deterministic collision planning over collider source artifacts.

This module turns a task and a set of loaded collider artifacts into a
``CollisionResult``: one ``Candidate`` per selected source, plus an optional
``insights_without_collision`` candidate when the task supplies its own
independent insight text. Everything here is template-driven and deterministic.
There is no model call, no network access, and no runtime registration; the
``run_id`` is a SHA-256 over canonical JSON of the task id, seed, and selected
source ids, so the same inputs always produce the same result.

The ``ablation`` field on each candidate is metadata, not a second evaluation:
it records which source was removed and which fields would change, with a short
factual explanation. Nothing here scores or ranks candidates, and nothing claims
creative quality.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

try:
    from . import collider          # loaded as a package, which is what the host does
except ImportError:  # flat-module load in tests
    from core import collider  # type: ignore[no-redef]

CHANNEL_COLLIDED = "collided"
CHANNEL_INSIGHTS = "insights_without_collision"
CANDIDATE_TYPE = "template_probe"
STATUS = "template_only"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _require_task(task: Any) -> Tuple[str, str]:
    if not isinstance(task, Mapping):
        raise ValueError("task must be a mapping with non-empty id and brief")
    task_id = task.get("id")
    brief = task.get("brief")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("task.id must be a non-empty string")
    if not isinstance(brief, str) or not brief.strip():
        raise ValueError("task.brief must be a non-empty string")
    return task_id, brief


def _require_sources(sources: Any) -> List[Dict[str, Any]]:
    if isinstance(sources, (str, bytes)) or not isinstance(sources, Sequence):
        raise ValueError("sources must be a non-empty sequence of collider artifacts")
    records = list(sources)
    if not records:
        raise ValueError("sources must be a non-empty sequence of collider artifacts")
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("each source must be a mapping with id and family")
        artifact_id = record.get("id")
        family = record.get("family")
        if not isinstance(artifact_id, str) or not artifact_id:
            raise ValueError("each source must carry a non-empty string id")
        if not isinstance(family, str) or not family:
            raise ValueError(f"source {artifact_id!r} must carry a non-empty family")
        for field_name in ("title", "mechanism", "bridge_question"):
            value = record.get(field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"source {artifact_id!r} must carry non-empty {field_name}")
    return records


def _require_count(count: Any) -> int:
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError(f"count must be an integer >= 1, got {count!r}")
    if count < 1:
        raise ValueError(f"count must be an integer >= 1, got {count!r}")
    return count


def _run_id(task_id: str, seed: Any, source_ids: Sequence[str]) -> str:
    payload = {
        "task_id": task_id,
        "seed": seed,
        "selected_source_ids": list(source_ids),
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return "collision-" + digest


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    channel: str
    thesis: str
    mechanism: str
    application: str
    first_step: str
    source_ids: Tuple[str, ...]
    candidate_type: str
    ablation: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "channel": self.channel,
            "thesis": self.thesis,
            "mechanism": self.mechanism,
            "application": self.application,
            "first_step": self.first_step,
            "source_ids": list(self.source_ids),
            "candidate_type": self.candidate_type,
            "ablation": dict(self.ablation),
        }


@dataclass(frozen=True)
class CollisionResult:
    run_id: str
    task_id: str
    seed: Any
    candidates: Tuple[Candidate, ...]
    source_ids: Tuple[str, ...]
    status: str
    usage: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "seed": self.seed,
            "candidates": [c.to_dict() for c in self.candidates],
            "source_ids": list(self.source_ids),
            "status": self.status,
            "usage": dict(self.usage),
        }


def _collided_candidate(
    run_id: str, task_id: str, brief: str, source: Mapping[str, Any]
) -> Candidate:
    source_id = source["id"]
    title = source["title"]
    mechanism = source["mechanism"]
    bridge_question = source["bridge_question"]

    thesis = f"Apply {title!r} to the task {task_id!r}."
    application = (
        f"Use the source's bridge question ({bridge_question}) to reframe the "
        f"task brief: {brief}"
    )
    first_step = (
        f"Write one sentence that applies the mechanism ({mechanism}) directly "
        f"to the task brief: {brief}"
    )
    ablation = {
        "removed_source_ids": [source_id],
        "changed_fields": ["thesis", "mechanism", "application", "first_step"],
        "explanation": (
            f"Removing source {source_id!r} removes its mechanism and its "
            "bridge-derived application, so this candidate would not exist."
        ),
    }
    return Candidate(
        candidate_id=f"{run_id}:{source_id}",
        channel=CHANNEL_COLLIDED,
        thesis=thesis,
        mechanism=mechanism,
        application=application,
        first_step=first_step,
        source_ids=(source_id,),
        candidate_type=CANDIDATE_TYPE,
        ablation=ablation,
    )


def _insights_candidate(run_id: str, independent_insight: str) -> Candidate:
    ablation = {
        "removed_source_ids": [],
        "changed_fields": [],
        "explanation": (
            "This insight comes from the task's own independent_insight text and "
            "does not depend on a collision with any source."
        ),
    }
    return Candidate(
        candidate_id=f"{run_id}:independent",
        channel=CHANNEL_INSIGHTS,
        thesis="Record the task's independent insight without a collision.",
        mechanism="independent_task_observation",
        application=independent_insight,
        first_step=(
            "Write down the independent insight verbatim and note that it was "
            "supplied by the task, not derived from a source."
        ),
        source_ids=(),
        candidate_type=CANDIDATE_TYPE,
        ablation=ablation,
    )


def collide(
    task: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    *,
    seed: Any,
    count: int = 2,
    strategy: str = "fresh",
    loved: Sequence[str] = (),
    liked: Sequence[str] = (),
) -> CollisionResult:
    """Plan deterministic collisions between a task and collider sources.

    ``strategy`` is ``fresh`` (the default), ``deepen``, or ``refresh``;
    ``loved``/``liked`` are the candidate ids the person has backed, which the
    last two strategies filter families by. The default reproduces the original
    behaviour exactly.
    """
    task_id, brief = _require_task(task)
    records = _require_sources(sources)
    limit = _require_count(count)

    selected = collider.select_sources(
        records,
        strategy=strategy,
        seed=seed,
        loved=list(loved) or None,
        liked=list(liked) or None,
        count=limit,
    )
    selected_ids = tuple(record["id"] for record in selected)
    run_id = _run_id(task_id, seed, selected_ids)

    candidates: List[Candidate] = [
        _collided_candidate(run_id, task_id, brief, record) for record in selected
    ]

    independent = task.get("independent_insight")
    if isinstance(independent, str) and independent.strip():
        candidates.append(_insights_candidate(run_id, independent))

    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return CollisionResult(
        run_id=run_id,
        task_id=task_id,
        seed=seed,
        candidates=tuple(candidates),
        source_ids=selected_ids,
        status=STATUS,
        usage=usage,
    )
