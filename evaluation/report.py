"""Coverage accounting for an evaluation grid.

The grid is the full product of tasks × conditions × models.  A cell is present
only when a record for that exact tuple exists.  Missing cells are reported,
never filled: coverage is not an effect, and a missing result is not a zero
result.  ``required_cells`` fails closed; ``summarize_coverage`` describes how
much of the grid was actually observed without estimating anything.

Every value produced here is JSON-compatible; ``to_json`` serializes strictly
with ``allow_nan=False`` so a stray NaN raises instead of emitting ``NaN``.
"""
from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

Cell = Tuple[str, str, str]  # (task_id, condition, model)


class CoverageError(ValueError):
    """Raised when declared grid cells have no record.

    ``missing`` holds every missing ``(task_id, condition, model)`` tuple, and
    the message lists all of them.
    """

    def __init__(self, missing: Iterable[Cell]):
        self.missing: List[Cell] = [
            (cell[0], cell[1], cell[2]) for cell in sorted(tuple(cell) for cell in missing)
        ]
        cells = ", ".join(f"{task}/{condition}/{model}" for task, condition, model in self.missing)
        super().__init__(
            f"coverage incomplete: {len(self.missing)} missing cell(s): {cells}")


def _declared(values: Sequence[str], *, name: str) -> List[str]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{name} must be a sequence of non-empty strings")
    out: List[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} contains an invalid value: {value!r}")
        out.append(value)
    if len(set(out)) != len(out):
        raise ValueError(f"{name} contains duplicates")
    if not out:
        raise ValueError(f"{name} must be non-empty")
    return out


def _cell(record: Mapping[str, Any], *, index: int) -> Cell:
    missing = [key for key in ("task_id", "condition", "model") if key not in record]
    if missing:
        raise ValueError(f"record {index} is missing fields: {', '.join(missing)}")
    cell: List[str] = []
    for key in ("task_id", "condition", "model"):
        value = record[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"record {index} {key} must be a non-empty string")
        cell.append(value)
    return (cell[0], cell[1], cell[2])


def _observed(records: Sequence[Mapping[str, Any]]) -> Counter:
    if isinstance(records, (str, bytes)) or not isinstance(records, Sequence):
        raise ValueError("records must be a sequence of mappings")
    counts: Counter = Counter()
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValueError(f"record {index} must be a mapping")
        counts[_cell(record, index=index)] += 1
    return counts


def _expected(conditions: Sequence[str], models: Sequence[str],
              tasks: Sequence[str]) -> List[Cell]:
    return [(task, condition, model)
            for task in tasks for condition in conditions for model in models]


def required_cells(records: Sequence[Mapping[str, Any]], conditions: Sequence[str],
                   models: Sequence[str], tasks: Sequence[str]) -> List[Cell]:
    """Return the missing grid cells, or ``[]`` when the grid is complete.

    Raises ``CoverageError`` listing every missing cell rather than returning a
    partial list the caller might ignore.  A record outside the declared grid is
    a ``ValueError``: it means the declaration and the data disagree.
    """
    conditions = _declared(conditions, name="conditions")
    models = _declared(models, name="models")
    tasks = _declared(tasks, name="tasks")
    counts = _observed(records)
    declared = set(_expected(conditions, models, tasks))
    undeclared = sorted(set(counts) - declared)
    if undeclared:
        preview = ", ".join(f"{t}/{c}/{m}" for t, c, m in undeclared[:5])
        raise ValueError(
            f"{len(undeclared)} record cell(s) are outside the declared grid: {preview}")
    missing = sorted(declared - set(counts))
    if missing:
        raise CoverageError(missing)
    return []


def summarize_coverage(records: Sequence[Mapping[str, Any]], conditions: Sequence[str],
                       models: Sequence[str], tasks: Sequence[str]) -> Dict[str, Any]:
    """Counts of observed vs expected cells, by condition and by model.

    Nothing is imputed: missing cells stay missing and are listed.  The summary
    deliberately contains no effect, delta, or score fields, so it cannot be
    read as a result.  Duplicate records for one cell are counted and named
    because they inflate a naive record count.
    """
    conditions = _declared(conditions, name="conditions")
    models = _declared(models, name="models")
    tasks = _declared(tasks, name="tasks")
    counts = _observed(records)
    expected = _expected(conditions, models, tasks)
    expected_set = set(expected)
    undeclared = sorted(set(counts) - expected_set)
    if undeclared:
        preview = ", ".join(f"{t}/{c}/{m}" for t, c, m in undeclared[:5])
        raise ValueError(
            f"{len(undeclared)} record cell(s) are outside the declared grid: {preview}")

    missing = sorted(expected_set - set(counts))
    duplicates = sorted(cell for cell, count in counts.items() if count > 1)

    by_condition: Dict[str, Dict[str, Any]] = {}
    for condition in conditions:
        cells = [cell for cell in expected if cell[1] == condition]
        seen = [cell for cell in cells if cell in counts]
        by_condition[condition] = {
            "expected": len(cells),
            "observed": len(seen),
            "missing": len(cells) - len(seen),
        }

    by_model: Dict[str, Dict[str, Any]] = {}
    for model in models:
        cells = [cell for cell in expected if cell[2] == model]
        seen = [cell for cell in cells if cell in counts]
        by_model[model] = {
            "expected": len(cells),
            "observed": len(seen),
            "missing": len(cells) - len(seen),
        }

    return {
        "expected_cells": len(expected),
        "observed_cells": len(expected_set & set(counts)),
        "missing_cells": len(missing),
        "missing": [{"task_id": t, "condition": c, "model": m} for t, c, m in missing],
        "duplicate_cells": [{"task_id": t, "condition": c, "model": m}
                            for t, c, m in duplicates],
        "records": sum(counts.values()),
        "complete": not missing,
        "by_condition": by_condition,
        "by_model": by_model,
    }


def to_json(value: Any, *, indent: int = 2) -> str:
    """Strict JSON: ``allow_nan=False``, sorted keys, no NaN/Infinity tokens."""
    return json.dumps(value, allow_nan=False, sort_keys=True, indent=indent)
