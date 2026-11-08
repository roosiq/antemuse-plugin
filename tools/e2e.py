#!/usr/bin/env python3
"""End-to-end check of the evidence pipeline: freeze → run → aggregate → refuse.

No network, no model: a deterministic transport stands in so the whole path can
be exercised in seconds and repeated in CI. It proves the plumbing, and it proves
the plumbing *fails*: a missing cell, a drifted fixture, and a duplicate record
are each required to be refused.

  env -u PYTHONPATH python3 tools/e2e.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN))

from evaluation import aggregate, report, run as runner, shards  # noqa: E402

MODEL = "e2e-model"
PROMPT_VERSION = "prompt-e2e"
SOURCE_VERSION = "collider-6ed948a"


class DeterministicTransport:
    """Answers every request identically, so any difference later is a bug."""

    def __init__(self):
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        return {"text": f"answer for {request['condition']} {request['task_id']}",
                "usage": {"input_tokens": 10, "output_tokens": 5}}


def _check(label: str, condition: bool, detail: str = "") -> None:
    print(f"{'PASS' if condition else 'FAIL'}  {label}{(' — ' + detail) if detail else ''}")
    if not condition:
        raise SystemExit(1)


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="antemuse-e2e-"))
    tasks = json.loads((PLUGIN / "evaluation" / "tasks" / "development.json")
                       .read_text(encoding="utf-8"))["tasks"]
    conditions = sorted(runner.CONDITIONS)

    print(f"root {root} · {len(tasks)} task(s) · conditions {''.join(conditions)}\n")

    # 1. freeze
    frozen = shards.freeze(root, kind="development", tasks=tasks, models=[MODEL],
                           conditions=conditions, prompt_version=PROMPT_VERSION,
                           source_version=SOURCE_VERSION)
    _check("shard frozen", frozen["frozen"] is True, frozen["id"][:16])
    again = shards.freeze(root, kind="development", tasks=tasks, models=[MODEL],
                          conditions=conditions, prompt_version=PROMPT_VERSION,
                          source_version=SOURCE_VERSION)
    _check("re-freeze is idempotent", again["frozen"] is False and again["id"] == frozen["id"])

    # 2. run every cell through the real runner
    results = shards.results_dir(root, frozen["id"])
    transport = DeterministicTransport()
    calls = 0
    for task in tasks:
        for condition in conditions:
            record = runner.run_condition(
                condition, task, model=MODEL, prompt_version=PROMPT_VERSION,
                source_version=SOURCE_VERSION, seed=13, transport=transport,
                cache_path=results / "cache.jsonl", selector=None,
            )
            _check(f"{task['id']}/{condition} answered",
                   record["status"] == "ok", record["status"])
            calls += record["transport_calls"]
            (results / f"{task['id']}--{condition}.json").write_text(
                json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")

    cells = len(tasks) * len(conditions)
    print(f"\n{cells} cells · {calls} model call(s) · {len(transport.requests)} request(s)")

    # 3. aggregate: complete, and byte-identical twice
    first = aggregate.to_json(aggregate.aggregate(root, [frozen["id"]]))
    second = aggregate.to_json(aggregate.aggregate(root, [frozen["id"]]))
    payload = json.loads(first)
    _check("aggregate is complete", payload["complete"] is True)
    _check("aggregate is deterministic", first == second)
    _check("aggregate counts every cell", payload["totals"]["cells"] == cells)

    # 4. a missing cell must be refused, by name
    victim = results / f"{tasks[-1]['id']}--E.json"
    saved = victim.read_text(encoding="utf-8")
    victim.unlink()
    try:
        aggregate.aggregate(root, [frozen["id"]])
        _check("a missing cell is refused", False, "aggregate passed anyway")
    except report.CoverageError as exc:
        named = f"{tasks[-1]['id']}/E/{MODEL}" in str(exc)
        _check("a missing cell is refused and named", named, str(exc).split(":")[0])
    victim.write_text(saved, encoding="utf-8")

    # 5. a drifted fixture must be caught
    drifted = [dict(tasks[0], brief="a different brief"), *tasks[1:]]
    try:
        shards.verify(root, frozen["id"], drifted)
        _check("a drifted fixture is caught", False, "verify passed anyway")
    except shards.ShardDrift as exc:
        _check("a drifted fixture is caught", True, str(exc)[:60])

    # 6. a duplicate must not inflate the count
    extra = results / "duplicate.json"
    extra.write_text(saved, encoding="utf-8")
    try:
        aggregate.aggregate(root, [frozen["id"]])
        _check("a duplicate is refused", False, "aggregate passed anyway")
    except aggregate.AggregateError as exc:
        _check("a duplicate is refused", True, str(exc)[:60])
    extra.unlink()

    # 7. and the grid is whole again
    healed = json.loads(aggregate.to_json(aggregate.aggregate(root, [frozen["id"]])))
    _check("the repaired grid aggregates again", healed["complete"] is True)

    print(f"\nend to end: OK · artifacts kept at {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
