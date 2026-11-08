#!/usr/bin/env python3
"""Run every cell of a frozen shard, resumably.

A cell is one (task, model, condition). The runner skips cells that already have
a successful record on disk, so an interrupted run or a few flaky calls can be
retried without re-paying for the whole shard and without ever editing a record
that already succeeded.

  env -u PYTHONPATH python3 tools/run_shard.py --root evaluation --shard <id> \
      --endpoint http://127.0.0.1:8645/v1 --max-tokens 2500

It writes into the shard's own results directory and never touches the manifest.
When it finishes it prints a coverage line; it does not aggregate (that is
`tools/shards.py aggregate`, which fails closed).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN))

from evaluation import run as runner, shards  # noqa: E402


def _load_pilot_transport():
    spec = importlib.util.spec_from_file_location("antemuse_pilot", PLUGIN / "tools" / "pilot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)          # type: ignore[union-attr]
    return module.transport_for


def cell_path(results: Path, task_id: str, model: str, condition: str) -> Path:
    safe_model = model.replace("/", "_")
    return results / f"{task_id}--{safe_model}--{condition}.json"


def existing_status(path: Path) -> str:
    if not path.is_file():
        return "missing"
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("status") or "unknown")
    except (OSError, json.JSONDecodeError):
        return "unreadable"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(PLUGIN / "evaluation"))
    parser.add_argument("--shard", required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8645/v1")
    parser.add_argument("--max-tokens", type=int, default=2500)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--only", default="", help="comma-separated conditions")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root)
    manifest = shards.load(root, args.shard)
    results = shards.results_dir(root, args.shard)
    results.mkdir(parents=True, exist_ok=True)

    tasks = json.loads((PLUGIN / "evaluation" / "tasks" / "development.json")
                       .read_text(encoding="utf-8"))["tasks"]
    by_id = {task["id"]: task for task in tasks}
    wanted = {c.strip() for c in args.only.split(",") if c.strip()} or set(manifest["conditions"])

    # The manifest names tasks by id; the runner needs the fixtures themselves.
    missing_tasks = [tid for tid in manifest["tasks"] if tid not in by_id]
    if missing_tasks:
        print(f"refused: the fixture has no task(s) {missing_tasks}", file=sys.stderr)
        return 3

    plan = [(tid, model, condition)
            for tid in manifest["tasks"]
            for model in manifest["models"]
            for condition in sorted(wanted)]
    todo = [cell for cell in plan if existing_status(cell_path(results, *cell)) != "ok"]

    print(f"shard {args.shard} · {len(plan)} cell(s) · {len(todo)} to run")
    if args.dry_run:
        for cell in todo:
            print("  would run", "/".join(cell))
        return 0

    for task_id, model, condition in todo:
        path = cell_path(results, task_id, model, condition)
        ok = False
        for attempt in range(1, args.retries + 2):
            transport = _load_pilot_transport()(model, args.endpoint, max_tokens=args.max_tokens)
            started = time.monotonic()
            record = runner.run_condition(
                condition, by_id[task_id], model=model,
                prompt_version=manifest["prompt_version"],
                source_version=manifest["source_version"],
                seed=7, transport=transport,
                cache_path=results / "cache.jsonl", selector=None,
            )
            elapsed = time.monotonic() - started
            if record["status"] == "ok":
                path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                                encoding="utf-8")
                usage = record.get("usage") or {}
                print(f"  ok   {task_id}/{model}/{condition} "
                      f"{record['transport_calls']} call(s) {elapsed:.0f}s "
                      f"{usage.get('output_tokens')} out-tokens")
                ok = True
                break
            print(f"  fail {task_id}/{model}/{condition} attempt {attempt}: "
                  f"{record['status']} {str(record.get('error'))[:120]}")
            time.sleep(2 * attempt)
        if not ok:
            print(f"  gave up on {task_id}/{model}/{condition}")

    counts = {}
    for task_id, model, condition in plan:
        status = existing_status(cell_path(results, task_id, model, condition))
        counts[status] = counts.get(status, 0) + 1
    print("coverage:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0 if counts.get("ok", 0) == len(plan) else 2


if __name__ == "__main__":
    raise SystemExit(main())
