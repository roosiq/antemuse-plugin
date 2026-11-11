"""K1/K2 — immutable shards and deterministic aggregation.

The point of these tests is that evidence cannot silently change: a shard is
frozen once, a fixture that moves afterwards is caught, and an incomplete grid
produces a named failure instead of a partial report.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ANTEMUSE_STATES_HOME", tempfile.mkdtemp(prefix="shards-test-"))

import pytest  # noqa: E402

# `evaluation/` is research evidence and is not packed into the installable tree, so these tests
# are repo-only by construction. The import must skip, not raise: a collection error means
# `pytest tests` cannot run at all from the shipped package.
pytest.importorskip("evaluation", reason="evaluation/ is not part of the package")

from evaluation import aggregate, report, shards  # noqa: E402

TASKS = [
    {"id": "t-alpha", "brief": "write about a door", "reference_text": "a door"},
    {"id": "t-beta", "brief": "write about a lamp", "reference_text": "a lamp"},
]
MODELS = ["model-one", "model-two"]
CONDITIONS = ["A", "B", "F"]


def _freeze(root, **over):
    kwargs = dict(kind="development", tasks=TASKS, models=MODELS, conditions=CONDITIONS,
                  prompt_version="prompt-1", source_version="collider-6ed948a")
    kwargs.update(over)
    return shards.freeze(root, **kwargs)


def _records(shard, *, skip=None, duplicate=False):
    out = []
    for task in shard["tasks"]:
        for condition in shard["conditions"]:
            for model in shard["models"]:
                cell = (task, condition, model)
                if skip and cell in skip:
                    continue
                out.append({"task_id": task, "condition": condition, "model": model,
                            "response": "x", "cache_status": "miss"})
                if duplicate:
                    out.append({"task_id": task, "condition": condition, "model": model,
                                "response": "x", "cache_status": "miss"})
    return out


def test_freezing_writes_a_manifest_once_and_is_idempotent(tmp_path):
    first = _freeze(tmp_path)
    assert first["frozen"] is True
    second = _freeze(tmp_path)
    assert second["frozen"] is False, "the same declaration must not create a second shard"
    assert second["id"] == first["id"]


def test_a_different_declaration_gets_a_different_id(tmp_path):
    base = _freeze(tmp_path)["id"]
    assert _freeze(tmp_path, models=["model-one"])["id"] != base
    assert _freeze(tmp_path, prompt_version="prompt-2")["id"] != base
    assert _freeze(tmp_path, source_version="other-bank")["id"] != base
    assert _freeze(tmp_path, conditions=["A"])["id"] != base
    assert _freeze(tmp_path, kind="calibration")["id"] != base


def test_task_order_does_not_change_the_id(tmp_path):
    a = _freeze(tmp_path)
    b = shards.freeze(tmp_path, kind="development", tasks=list(reversed(TASKS)),
                      models=MODELS, conditions=CONDITIONS,
                      prompt_version="prompt-1", source_version="collider-6ed948a")
    assert a["id"] == b["id"], "the id is over content, not file order"


def test_a_shard_that_changed_is_caught(tmp_path):
    frozen = _freeze(tmp_path)
    shards.verify(tmp_path, frozen["id"], TASKS)          # unchanged: fine
    drifted = [dict(TASKS[0], brief="write about a different door"), TASKS[1]]
    with pytest.raises(shards.ShardDrift):
        shards.verify(tmp_path, frozen["id"], drifted)


def test_a_tampered_manifest_is_refused(tmp_path):
    frozen = _freeze(tmp_path)
    path = tmp_path / "shards" / f"{frozen['id']}.json"
    data = json.loads(path.read_text())
    data["models"] = ["model-three"]
    path.write_text(json.dumps(data))
    with pytest.raises(shards.ShardError):
        shards.load(tmp_path, frozen["id"])


def test_each_shard_owns_its_results_directory(tmp_path):
    one = _freeze(tmp_path)
    two = _freeze(tmp_path, kind="calibration")
    a = shards.results_dir(tmp_path, one["id"])
    b = shards.results_dir(tmp_path, two["id"])
    assert a != b and a.is_dir() and b.is_dir()


def test_declarations_are_validated(tmp_path):
    with pytest.raises(shards.ShardError):
        _freeze(tmp_path, kind="final")
    with pytest.raises(shards.ShardError):
        _freeze(tmp_path, models=[])
    with pytest.raises(shards.ShardError):
        _freeze(tmp_path, models=["a", "a"])
    with pytest.raises(shards.ShardError):
        _freeze(tmp_path, prompt_version="  ")
    with pytest.raises(shards.ShardError):
        _freeze(tmp_path, tasks=[])


# ------------------------------------------------------------------ K2
def _write_results(root, shard, records, name="run.json"):
    directory = shards.results_dir(root, shard["id"])
    (directory / name).write_text(json.dumps(records))


def test_a_complete_grid_aggregates_deterministically(tmp_path):
    shard = _freeze(tmp_path)
    _write_results(tmp_path, shard, _records(shard))
    first = aggregate.to_json(aggregate.aggregate(tmp_path, [shard["id"]]))
    second = aggregate.to_json(aggregate.aggregate(tmp_path, [shard["id"]]))
    assert first == second, "aggregation must not depend on file order or time"
    payload = json.loads(first)
    assert payload["complete"] is True
    assert payload["totals"]["cells"] == 2 * 2 * 3


def test_a_missing_cell_fails_and_names_every_gap(tmp_path):
    shard = _freeze(tmp_path)
    missing = {("t-alpha", "B", "model-one"), ("t-beta", "F", "model-two")}
    _write_results(tmp_path, shard, _records(shard, skip=missing))
    with pytest.raises(report.CoverageError) as excinfo:
        aggregate.aggregate(tmp_path, [shard["id"]])
    assert set(excinfo.value.missing) == missing
    assert "t-alpha/B/model-one" in str(excinfo.value)


def test_duplicates_are_refused_by_default_and_reported_when_allowed(tmp_path):
    shard = _freeze(tmp_path)
    _write_results(tmp_path, shard, _records(shard, duplicate=True))
    with pytest.raises(aggregate.AggregateError):
        aggregate.aggregate(tmp_path, [shard["id"]])
    allowed = aggregate.aggregate(tmp_path, [shard["id"]], allow_duplicates=True)
    assert allowed["totals"]["duplicates"] == 2 * 2 * 3


def test_a_record_outside_the_grid_is_not_ignored(tmp_path):
    shard = _freeze(tmp_path)
    records = _records(shard) + [{"task_id": "t-alpha", "condition": "Z", "model": "model-one"}]
    _write_results(tmp_path, shard, records)
    with pytest.raises(ValueError):
        aggregate.aggregate(tmp_path, [shard["id"]])


def test_a_malformed_result_file_is_named_not_skipped(tmp_path):
    shard = _freeze(tmp_path)
    directory = shards.results_dir(tmp_path, shard["id"])
    (directory / "broken.json").write_text("{not json")
    with pytest.raises(aggregate.AggregateError) as excinfo:
        aggregate.aggregate(tmp_path, [shard["id"]])
    assert "broken.json" in str(excinfo.value)


def test_aggregating_nothing_is_refused(tmp_path):
    with pytest.raises(aggregate.AggregateError):
        aggregate.aggregate(tmp_path, [])
