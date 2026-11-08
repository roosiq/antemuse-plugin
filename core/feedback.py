"""Love/like/trash feedback and strategy routing.

Feedback is a small, append-only record of how a walker responded to a candidate.
``love`` and ``like`` are positive signals; ``trash`` is neither. Notes are stored
verbatim and never parsed for sentiment. ``strategies`` routes to the collider's
``deepen`` strategy when anything was loved, otherwise to ``refresh`` over loved and
liked ids; an empty positive set raises ``ValueError`` rather than guessing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Set

from . import collider

VERDICTS = ("love", "like", "trash")


def _utc_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Feedback:
    candidate_id: str
    verdict: str
    note: str = ""
    at: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise ValueError("candidate_id must be a non-empty string")
        if self.verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS!r}, got {self.verdict!r}")
        if not isinstance(self.note, str):
            raise ValueError("note must be a string")
        if self.at is None:
            self.at = _utc_z()
        elif not isinstance(self.at, str) or not self.at:
            raise ValueError("at must be a non-empty UTC Z string")


class FeedbackStore:
    """Append-only feedback history preserving insertion order."""

    def __init__(self) -> None:
        self._records: List[Feedback] = []

    def record(self, candidate_id: str, verdict: str, note: str = "") -> Feedback:
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            raise ValueError("candidate_id must be a non-empty string")
        entry = Feedback(candidate_id=candidate_id, verdict=verdict, note=note)
        self._records.append(entry)
        return entry

    def list(self, candidate_id: Optional[str] = None) -> List[Feedback]:
        if candidate_id is None:
            return list(self._records)
        return [entry for entry in self._records if entry.candidate_id == candidate_id]

    def ids(self, *, loved: bool = False, liked: bool = False) -> Set[str]:
        """Return ids by positive signal.

        ``loved`` selects ids with a ``love`` record; ``liked`` selects ids with a
        ``like`` record. ``trash`` contributes to neither. Both flags may be set to
        get the union.
        """
        result: Set[str] = set()
        for entry in self._records:
            if loved and entry.verdict == "love":
                result.add(entry.candidate_id)
            if liked and entry.verdict == "like":
                result.add(entry.candidate_id)
        return result


def strategies(
    store: FeedbackStore,
    artifacts: Sequence[Dict[str, Any]],
    *,
    seed: Any,
    count: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Route to a collider strategy from positive feedback.

    Loved ids route to ``deepen``; otherwise loved and liked ids route to
    ``refresh``. If neither set is non-empty, raise ``ValueError``. Notes are never
    inspected.
    """
    loved = store.ids(loved=True)
    liked = store.ids(liked=True)
    if loved:
        return collider.select_sources(
            artifacts, strategy="deepen", seed=seed, loved=loved, count=count
        )
    if liked:
        return collider.select_sources(
            artifacts, strategy="refresh", seed=seed, loved=loved, liked=liked, count=count
        )
    raise ValueError("no loved or liked feedback to route a strategy from")
