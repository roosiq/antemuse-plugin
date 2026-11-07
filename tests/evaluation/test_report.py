"""Grid coverage tests: missing cells fail closed, counts never impute effects."""
from __future__ import annotations

import json

import pytest

from . import load

report = load("report")

CONDITIONS = ["A", "F"]
MODELS = ["m1", "m2"]
TASKS = ["t1", "t2"]


def full_records():
    return [
        {"task_id": task, "condition": condition, "model": model, "quality": 0.5}
        for task in TASKS for condition in CONDITIONS for model in MODELS
    ]


# --------------------------------------------------------------- required cells

def test_complete_grid_has_no_missing_cells():
    assert report.required_cells(full_records(), CONDITIONS, MODELS, TASKS) == []


def test_missing_cell_raises_and_lists_every_cell():
    records = [r for r in full_records()
               if not (r["task_id"] == "t2" and r["condition"] == "F" and r["model"] == "m2")]
    with pytest.raises(report.CoverageError) as excinfo:
        report.required_cells(records, CONDITIONS, MODELS, TASKS)
    assert excinfo.value.missing == [("t2", "F", "m2")]
    assert "t2/F/m2" in str(excinfo.value)
    assert "1 missing cell(s)" in str(excinfo.value)


def test_every_missing_cell_appears_in_the_error():
    records = [r for r in full_records() if r["model"] == "m1"]
    with pytest.raises(report.CoverageError) as excinfo:
        report.required_cells(records, CONDITIONS, MODELS, TASKS)
    expected = sorted((task, condition, "m2")
                      for task in TASKS for condition in CONDITIONS)
    assert excinfo.value.missing == expected
    for task, condition, model in expected:
        assert f"{task}/{condition}/{model}" in str(excinfo.value)


def test_all_cells_missing_from_empty_records():
    with pytest.raises(report.CoverageError) as excinfo:
        report.required_cells([], CONDITIONS, MODELS, TASKS)
    assert len(excinfo.value.missing) == 8


def test_undeclared_record_cell_is_an_error():
    records = full_records() + [{"task_id": "t9", "condition": "A", "model": "m1"}]
    with pytest.raises(ValueError, match="outside the declared grid"):
        report.required_cells(records, CONDITIONS, MODELS, TASKS)


def test_declarations_must_be_nonempty_and_unique():
    with pytest.raises(ValueError, match="duplicates"):
        report.required_cells(full_records(), ["A", "A"], MODELS, TASKS)
    with pytest.raises(ValueError, match="non-empty"):
        report.required_cells(full_records(), [], MODELS, TASKS)


def test_record_without_grid_fields_is_an_error():
    with pytest.raises(ValueError, match="missing fields"):
        report.required_cells([{"task_id": "t1", "condition": "A"}], CONDITIONS, MODELS, TASKS)


# ------------------------------------------------------------ summarize coverage

def test_complete_summary_counts_every_cell():
    summary = report.summarize_coverage(full_records(), CONDITIONS, MODELS, TASKS)
    assert summary["complete"] is True
    assert summary["expected_cells"] == 8
    assert summary["observed_cells"] == 8
    assert summary["missing_cells"] == 0
    assert summary["missing"] == []
    assert summary["records"] == 8
    assert summary["by_condition"]["A"] == {"expected": 4, "observed": 4, "missing": 0}
    assert summary["by_model"]["m2"] == {"expected": 4, "observed": 4, "missing": 0}


def test_missing_cells_are_reported_not_filled_with_zero():
    records = [r for r in full_records() if not (r["task_id"] == "t1" and r["condition"] == "F")]
    summary = report.summarize_coverage(records, CONDITIONS, MODELS, TASKS)
    assert summary["complete"] is False
    assert summary["missing_cells"] == 2
    assert {"task_id": "t1", "condition": "F", "model": "m1"} in summary["missing"]
    assert {"task_id": "t1", "condition": "F", "model": "m2"} in summary["missing"]
    assert summary["by_condition"]["F"] == {"expected": 4, "observed": 2, "missing": 2}
    # Coverage accounting only: no effect/delta fields exist to mistake for results.
    assert "effect" not in summary
    assert "delta" not in summary
    assert "score" not in summary


def test_duplicate_records_are_counted_and_named():
    records = full_records() + [{"task_id": "t1", "condition": "A", "model": "m1"}]
    summary = report.summarize_coverage(records, CONDITIONS, MODELS, TASKS)
    assert summary["records"] == 9
    assert summary["observed_cells"] == 8
    assert summary["duplicate_cells"] == [
        {"task_id": "t1", "condition": "A", "model": "m1"}
    ]


def test_summary_rejects_undeclared_cells():
    records = full_records() + [{"task_id": "t9", "condition": "A", "model": "m1"}]
    with pytest.raises(ValueError, match="outside the declared grid"):
        report.summarize_coverage(records, CONDITIONS, MODELS, TASKS)


# ------------------------------------------------------------------- JSON strictness

def test_summary_is_strict_json_serializable():
    summary = report.summarize_coverage(full_records(), CONDITIONS, MODELS, TASKS)
    payload = report.to_json(summary)
    assert json.loads(payload) == summary
    assert "NaN" not in payload and "Infinity" not in payload
    # The same summary must also survive the stdlib walk with allow_nan=False.
    json.dumps(summary, allow_nan=False)


def test_to_json_refuses_non_finite_numbers():
    with pytest.raises(ValueError):
        report.to_json({"effect": float("nan")})
    with pytest.raises(ValueError):
        report.to_json({"effect": float("inf")})
