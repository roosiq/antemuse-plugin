#!/usr/bin/env python3
"""Freeze, verify, and aggregate evaluation shards.

  python3 tools/shards.py freeze --root evaluation --kind development \
      --tasks evaluation/tasks/development.json \
      --models m1,m2 --conditions A,B,C \
      --prompt-version prompt-1 --source-version collider-6ed948a

  python3 tools/shards.py verify  --root evaluation --shard <id> \
      --tasks evaluation/tasks/development.json

  python3 tools/shards.py aggregate --root evaluation --shard <id> [--shard <id2>]

`freeze` is idempotent for an identical declaration and refuses a shard that
already exists with different content. `aggregate` exits non-zero when the grid
is incomplete, naming every missing cell.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN))

from evaluation import aggregate as aggregate_module  # noqa: E402
from evaluation import report, shards  # noqa: E402


def _tasks(path: Path) -> list:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tasks = payload.get("tasks") if isinstance(payload, dict) else payload
    if not isinstance(tasks, list) or not tasks:
        raise SystemExit(f"{path} has no tasks")
    return tasks


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "verify", "aggregate"))
    parser.add_argument("--root", default=str(PLUGIN / "evaluation"))
    parser.add_argument("--tasks", help="task fixture JSON")
    parser.add_argument("--kind", default="development", choices=shards.KINDS)
    parser.add_argument("--models", default="", help="comma-separated model ids")
    parser.add_argument("--conditions", default="", help="comma-separated conditions")
    parser.add_argument("--prompt-version", default="")
    parser.add_argument("--source-version", default="")
    parser.add_argument("--shard", action="append", default=[])
    parser.add_argument("--allow-duplicates", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root)

    try:
        if args.command == "freeze":
            if not args.tasks:
                raise SystemExit("freeze needs --tasks")
            manifest = shards.freeze(
                root,
                kind=args.kind,
                tasks=_tasks(Path(args.tasks)),
                models=[part for part in args.models.split(",") if part.strip()],
                conditions=[part for part in args.conditions.split(",") if part.strip()],
                prompt_version=args.prompt_version,
                source_version=args.source_version,
            )
            print(json.dumps(manifest, sort_keys=True, indent=2))
            return 0

        if args.command == "verify":
            if not args.shard or not args.tasks:
                raise SystemExit("verify needs --shard and --tasks")
            for shard_id in args.shard:
                shards.verify(root, shard_id, _tasks(Path(args.tasks)))
                print(f"{shard_id}: tasks match the frozen hash")
            return 0

        if not args.shard:
            raise SystemExit("aggregate needs at least one --shard")
        result = aggregate_module.aggregate(root, args.shard,
                                            allow_duplicates=args.allow_duplicates)
        sys.stdout.write(aggregate_module.to_json(result))
        return 0
    except report.CoverageError as exc:
        print(f"incomplete: {exc}", file=sys.stderr)
        return 2
    except (shards.ShardError, aggregate_module.AggregateError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
