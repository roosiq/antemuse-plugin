"""Blind pairwise judge records.

A judge sees two responses for the same task and says which is better on one
axis.  The condition that produced each response is hidden from the judge; the
mapping from pseudonymous slot to condition is kept in a separate structure so
that blindness is auditable rather than assumed.  The bookkeeping record still
carries condition names for auditing; ``to_judge_dict()`` is the projection that
contains no condition names and is safe to hand to a judge.

No model is called here.  A judge is external (human or model) and its verdict
is recorded as data.  The pseudonym is a SHA-256 digest, so the identifier does
not spell out a condition name; that is pseudonymity, not a guarantee against
brute force if the condition vocabulary is tiny.

Python's ``hash()`` is deliberately not used anywhere: it is salted per process
and would make pair ids differ between runs.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

WINNERS = ("left", "right", "tie")
_PAIR_SALT = "antemuse-blind-pair/v1"
_ORDER_SALT = "antemuse-blind-order/v1"


def _require_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _digest(*parts: str) -> str:
    material = "\x1f".join(parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PairwiseVerdict:
    """One judge's comparison of two responses on one axis.

    ``winner`` is the slot that won, not a condition.  ``left_condition`` and
    ``right_condition`` say which condition occupied each slot at comparison
    time.  ``blind_pair_id`` is set only on blinded records.
    """

    task_id: str
    left_condition: str
    right_condition: str
    winner: str
    axis: str
    judge_id: str
    blind_pair_id: Optional[str] = None

    def __post_init__(self) -> None:
        for field in ("task_id", "left_condition", "right_condition", "axis", "judge_id"):
            _require_text(getattr(self, field), field=field)
        if self.winner not in WINNERS:
            raise ValueError(f"winner must be one of {WINNERS}, got {self.winner!r}")
        if self.left_condition == self.right_condition:
            raise ValueError("left_condition and right_condition must differ")
        if self.blind_pair_id is not None:
            _require_text(self.blind_pair_id, field="blind_pair_id")

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable view (``blind_pair_id`` omitted when absent)."""
        out: Dict[str, Any] = {
            "task_id": self.task_id,
            "left_condition": self.left_condition,
            "right_condition": self.right_condition,
            "winner": self.winner,
            "axis": self.axis,
            "judge_id": self.judge_id,
        }
        if self.blind_pair_id is not None:
            out["blind_pair_id"] = self.blind_pair_id
        return out

    def to_judge_dict(self) -> Dict[str, Any]:
        """Judge-facing projection with pseudonymous slots and no condition names."""
        out: Dict[str, Any] = {
            "task_id": self.task_id,
            "left_response_slot": "left",
            "right_response_slot": "right",
            "winner": self.winner,
            "axis": self.axis,
            "judge_id": self.judge_id,
        }
        if self.blind_pair_id is not None:
            out["blind_pair_id"] = self.blind_pair_id
        return out


def randomized_pair_id(task_id: str, left_condition: str, right_condition: str,
                       seed: int = 0) -> str:
    """Deterministic pseudonym for a task/condition pair.

    The id depends on the task, both condition names, and the seed, but the
    names themselves never appear in it.  The two condition names are sorted
    before hashing, so swapping left/right yields the same pair id.
    """
    task_id = _require_text(task_id, field="task_id")
    left_condition = _require_text(left_condition, field="left_condition")
    right_condition = _require_text(right_condition, field="right_condition")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    conditions = sorted((left_condition, right_condition))
    return "pair-" + _digest(_PAIR_SALT, str(seed), task_id, conditions[0], conditions[1])[:24]


def _swap_coin(seed: int, pair_id: str) -> bool:
    """Deterministic 50/50 coin, stable across processes and call order."""
    return int(_digest(_ORDER_SALT, str(seed), pair_id)[:8], 16) % 2 == 1


def _coerce(record: Any) -> PairwiseVerdict:
    if isinstance(record, PairwiseVerdict):
        verdict = record
    elif isinstance(record, Mapping):
        missing = [key for key in ("task_id", "left_condition", "right_condition",
                                   "winner", "axis", "judge_id") if key not in record]
        if missing:
            raise ValueError(f"judge record is missing fields: {', '.join(missing)}")
        verdict = PairwiseVerdict(
            task_id=record["task_id"],
            left_condition=record["left_condition"],
            right_condition=record["right_condition"],
            winner=record["winner"],
            axis=record["axis"],
            judge_id=record["judge_id"],
            blind_pair_id=record.get("blind_pair_id"),
        )
    else:
        raise ValueError(f"judge record must be a PairwiseVerdict or mapping, got {type(record).__name__}")
    if verdict.blind_pair_id is not None:
        raise ValueError("record is already blinded; blind each verdict once")
    return verdict


def blind_pairs(records: Iterable[Any], seed: int = 0
                ) -> Tuple[List[PairwiseVerdict], Dict[str, Dict[str, Any]]]:
    """Return ``(blinded_records, mapping)``.

    Each verdict's left/right slots are swapped or kept according to a
    deterministic coin derived from ``seed`` and the pair id, and a winning
    side is flipped with its slot (a tie stays a tie).  Use ``to_judge_dict()``
    for the judge-facing projection that omits original condition names.

    ``mapping`` is kept separately and maps ``blind_pair_id`` to the original
    ``task_id``, condition→slot assignment, and whether the slots were swapped.
    It is the only structure that can unblind a verdict, and callers must not
    share it with a judge.
    """
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    blinded: List[PairwiseVerdict] = []
    mapping: Dict[str, Dict[str, Any]] = {}
    for index, record in enumerate(records):
        verdict = _coerce(record)
        base_id = randomized_pair_id(
            verdict.task_id, verdict.left_condition, verdict.right_condition, seed)
        pair_id = base_id
        if pair_id in mapping:
            # Two records for the same task/pair: suffix the position so both
            # remain addressable.  Deterministic given the input order.
            pair_id = f"{base_id}-{index}"
        if pair_id in mapping:
            raise ValueError(f"duplicate blind pair id at record {index}: {pair_id}")

        swapped = _swap_coin(seed, pair_id)
        winner = verdict.winner
        if swapped:
            left_condition, right_condition = verdict.right_condition, verdict.left_condition
            if winner == "left":
                winner = "right"
            elif winner == "right":
                winner = "left"
        else:
            left_condition, right_condition = verdict.left_condition, verdict.right_condition

        blinded.append(PairwiseVerdict(
            task_id=verdict.task_id,
            left_condition=left_condition,
            right_condition=right_condition,
            winner=winner,
            axis=verdict.axis,
            judge_id=verdict.judge_id,
            blind_pair_id=pair_id,
        ))
        mapping[pair_id] = {
            "blind_pair_id": pair_id,
            "task_id": verdict.task_id,
            "left_condition": verdict.left_condition,
            "right_condition": verdict.right_condition,
            "swapped": swapped,
            "axis": verdict.axis,
            "judge_id": verdict.judge_id,
        }
    return blinded, mapping


def unblind_winner(blinded: PairwiseVerdict, mapping: Mapping[str, Mapping[str, Any]]) -> str:
    """Translate a blinded winning slot back into a condition (or ``'tie'``)."""
    if not isinstance(blinded, PairwiseVerdict):
        raise ValueError("blinded must be a PairwiseVerdict")
    if blinded.blind_pair_id is None:
        raise ValueError("verdict is not blinded; it has no blind_pair_id")
    entry = mapping.get(blinded.blind_pair_id)
    if entry is None:
        raise ValueError(f"no mapping for blind_pair_id {blinded.blind_pair_id!r}")
    if entry["task_id"] != blinded.task_id:
        raise ValueError("mapping task_id does not match the blinded verdict")
    if blinded.winner == "tie":
        return "tie"
    original_left = entry["left_condition"]
    original_right = entry["right_condition"]
    if bool(entry["swapped"]):
        expected_left = original_right
        expected_right = original_left
    else:
        expected_left = original_left
        expected_right = original_right
    if (blinded.left_condition, blinded.right_condition) != (expected_left, expected_right):
        raise ValueError("blinded slots do not match the recorded mapping")
    if bool(entry["swapped"]):
        return original_right if blinded.winner == "left" else original_left
    return original_left if blinded.winner == "left" else original_right
