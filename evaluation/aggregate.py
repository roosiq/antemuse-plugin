"""Deterministic aggregation over one or more frozen shards.

The rule this module enforces is the one that matters for evidence: a grid that
is declared must be complete, or nothing is reported at all. Missing cells raise
:class:`evaluation.report.CoverageError` listing every one of them; records
outside the declared grid raise ``ValueError``; duplicate records are counted and
named because they inflate a naive record count.

Nothing here imputes a value, invents a row, averages anything into a score, or
reads a clock. The output of two runs over the same files is byte-identical:
files are read in sorted order and every mapping is emitted with sorted keys.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from . import report, shards


class AggregateError(ValueError):
    """A shard's results directory cannot be aggregated as declared."""


def _record_files(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.iterdir()
                  if path.is_file() and path.suffix == ".json")


def load_records(directory: Path | str) -> List[Dict[str, Any]]:
    """Read every record file in a shard's results directory, in sorted order.

    A file may hold one record object or a list of them. Anything else is a
    named failure rather than a skipped file: silently ignoring a malformed
    result is how a gap becomes an opinion.
    """
    out: List[Dict[str, Any]] = []
    for path in _record_files(Path(directory)):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AggregateError(f"{path.name} is not readable JSON: {exc}") from None
        items = payload if isinstance(payload, list) else [payload]
        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                raise AggregateError(f"{path.name} entry {index} is not an object")
            out.append(dict(item))
    return out


def aggregate(root: Path | str, shard_ids: Sequence[str], *,
              allow_duplicates: bool = False) -> Dict[str, Any]:
    """Aggregate frozen shards into a coverage report.

    Every declared cell must be present exactly once. ``allow_duplicates``
    exists for diagnosing a bad run, never for publishing: duplicates are
    reported either way.
    """
    if isinstance(shard_ids, (str, bytes)) or not isinstance(shard_ids, Sequence):
        raise AggregateError("shard_ids must be a sequence of shard ids")
    if not shard_ids:
        raise AggregateError("no shards were named; there is nothing to aggregate")

    per_shard: List[Dict[str, Any]] = []
    totals = {"records": 0, "cells": 0, "duplicates": 0}

    for shard_id in shard_ids:
        manifest = shards.load(root, shard_id)
        directory = shards.results_dir(root, shard_id)
        records = load_records(directory)
        # Raises CoverageError listing every missing cell, or ValueError for a
        # record outside the declared grid.
        report.required_cells(records, manifest["conditions"], manifest["models"],
                              manifest["tasks"])
        coverage = report.summarize_coverage(records, manifest["conditions"],
                                             manifest["models"], manifest["tasks"])
        duplicates = len(coverage.get("duplicate_cells") or [])
        if duplicates and not allow_duplicates:
            raise AggregateError(
                f"shard {shard_id} has {duplicates} duplicate cell(s); "
                "fix the run before aggregating it"
            )
        per_shard.append({
            "shard": shard_id,
            "kind": manifest["kind"],
            "models": list(manifest["models"]),
            "conditions": list(manifest["conditions"]),
            "tasks": len(manifest["tasks"]),
            "records": len(records),
            "duplicates": duplicates,
            "coverage": coverage,
        })
        totals["records"] += len(records)
        totals["cells"] += len(manifest["tasks"]) * len(manifest["models"]) * len(manifest["conditions"])
        totals["duplicates"] += duplicates

    return {
        "shards": per_shard,
        "totals": totals,
        "complete": True,
    }


def to_json(value: Mapping[str, Any]) -> str:
    """Stable text form: sorted keys, fixed separators, trailing newline."""
    return json.dumps(value, sort_keys=True, indent=2) + "\n"
