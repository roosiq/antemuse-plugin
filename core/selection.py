"""Deterministic candidate cleanup and optional selection-only judging.

This module is deliberately small and offline. ``cleanup_candidates`` removes exact
normalized duplicates and forbidden-topic candidates while preserving first
occurrence order; ``channel_for`` derives the channel from whether a candidate
collided with a source; ``select_for_synthesis`` returns the first unique valid
candidates by default, or, when a judge is injected, sorts by the mean of five
numeric axes. Judge scores are selection aids only: they are recorded, never
presented as evidence of quality, and a judge failure falls back to the
deterministic unjudged selection with an error field rather than fabricated
scores.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

AXES = ("novelty", "usefulness", "coherence", "surprise", "potential")
THRESHOLD = 4.0
CHANNEL_COLLIDED = "collided"
CHANNEL_INSIGHT = "insights_without_collision"
CHANNELS = (CHANNEL_COLLIDED, CHANNEL_INSIGHT)


def normalize_text(text: str) -> str:
    """Lowercase, collapse whitespace, and strip."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    return " ".join(text.lower().split())


def channel_for(candidate: Mapping[str, Any]) -> str:
    """Return the channel implied by ``source_ids`` and validate any declared one."""
    source_ids = candidate.get("source_ids")
    if not isinstance(source_ids, list):
        raise ValueError("candidate source_ids must be a list")
    implied = CHANNEL_COLLIDED if source_ids else CHANNEL_INSIGHT
    declared = candidate.get("channel")
    if declared is not None:
        if declared not in CHANNELS:
            raise ValueError(f"candidate channel must be one of {CHANNELS!r}, got {declared!r}")
        if declared != implied:
            raise ValueError(
                f"candidate channel {declared!r} is inconsistent with source_ids "
                f"(implied {implied!r})"
            )
    return implied


def _validate_candidate(candidate: Any, index: int) -> Dict[str, Any]:
    if not isinstance(candidate, Mapping):
        raise ValueError(f"candidate at index {index} must be a mapping")
    candidate_id = candidate.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        raise ValueError(f"candidate at index {index} must carry a non-empty string candidate_id")
    for field in ("thesis", "application"):
        value = candidate.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"candidate {candidate_id!r} must carry a non-empty string {field}")
    source_ids = candidate.get("source_ids")
    if not isinstance(source_ids, list):
        raise ValueError(f"candidate {candidate_id!r} source_ids must be a list")
    for source_id in source_ids:
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError(f"candidate {candidate_id!r} source_ids must contain non-empty strings")
    channel_for(candidate)
    return dict(candidate)


def cleanup_candidates(
    candidates: Sequence[Mapping[str, Any]],
    *,
    forbidden_topics: Iterable[str] = (),
) -> List[Dict[str, Any]]:
    """Validate, deduplicate, and filter candidates deterministically.

    Exact normalized duplicates (by thesis + application) are removed, keeping the
    first occurrence. Candidates whose thesis or application contains any forbidden
    topic substring (case-insensitive) are removed. Inputs are never mutated.
    """
    if isinstance(forbidden_topics, str):
        raise ValueError("forbidden_topics must be an iterable of strings, not a single string")
    topics = []
    for topic in forbidden_topics:
        if not isinstance(topic, str):
            raise ValueError(f"forbidden_topics must contain only strings, got {topic!r}")
        normalized = normalize_text(topic)
        if normalized:
            topics.append(normalized)

    validated = [_validate_candidate(candidate, index) for index, candidate in enumerate(candidates)]

    seen_ids: Dict[str, int] = {}
    for index, candidate in enumerate(validated):
        candidate_id = candidate["candidate_id"]
        if candidate_id in seen_ids:
            raise ValueError(
                f"duplicate candidate_id {candidate_id!r} at indices "
                f"{seen_ids[candidate_id]} and {index}"
            )
        seen_ids[candidate_id] = index

    result: List[Dict[str, Any]] = []
    seen_keys = set()
    for candidate in validated:
        key = (normalize_text(candidate["thesis"]), normalize_text(candidate["application"]))
        if key in seen_keys:
            continue
        haystack = key[0] + " " + key[1]
        if any(topic in haystack for topic in topics):
            continue
        seen_keys.add(key)
        result.append(candidate)
    return result


def _judge_scores(candidate: Mapping[str, Any], judge: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> Dict[str, float]:
    raw = judge(candidate)
    if not isinstance(raw, Mapping):
        raise ValueError("judge must return a mapping of axis scores")
    scores: Dict[str, float] = {}
    for axis in AXES:
        if axis not in raw:
            raise ValueError(f"judge result missing axis {axis!r}")
        value = raw[axis]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"judge axis {axis!r} must be numeric, got {value!r}")
        scores[axis] = float(value)
    return scores


def select_for_synthesis(
    candidates: Sequence[Mapping[str, Any]],
    *,
    judge: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None,
    count: int = 2,
) -> Dict[str, Any]:
    """Select candidates for synthesis, deterministically unless a judge is injected.

    Without a judge, the first ``count`` unique valid candidates are returned in
    input order with ``selection_status='unjudged'``. With a judge, each candidate is
    scored on the five axes, sorted by mean descending with stable ties by original
    order, and the top ``count`` are returned with ``selection_status='judged'``,
    ``threshold_used=4.0``, and per-candidate axis scores. A judge failure returns
    the deterministic unjudged selection plus an ``error`` field; no scores are
    fabricated.
    """
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError(f"count must be a non-negative integer, got {count!r}")

    cleaned = cleanup_candidates(candidates)

    def unjudged(error: Optional[str] = None) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "selected": cleaned[:count],
            "selection_status": "unjudged",
        }
        if error is not None:
            result["error"] = error
        return result

    if judge is None:
        return unjudged()

    scored: List[Dict[str, Any]] = []
    try:
        for index, candidate in enumerate(cleaned):
            scores = _judge_scores(candidate, judge)
            mean = sum(scores[axis] for axis in AXES) / len(AXES)
            scored.append({"index": index, "candidate": candidate, "scores": scores, "mean": mean})
    except Exception as exc:  # noqa: BLE001 - any judge failure falls back deterministically
        return unjudged(error=f"judge failed: {exc}")

    scored.sort(key=lambda entry: (-entry["mean"], entry["index"]))
    selected = []
    for entry in scored[:count]:
        record = dict(entry["candidate"])
        record["axis_scores"] = dict(entry["scores"])
        record["mean_score"] = entry["mean"]
        selected.append(record)
    return {
        "selected": selected,
        "selection_status": "judged",
        "threshold_used": THRESHOLD,
    }
