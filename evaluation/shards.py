"""Immutable evaluation shards.

A shard is the smallest unit of evidence this project will accept: a named task
set, a named model set, the conditions to run, and the versions of the prompt
and source bank that were in force. Freezing one writes a manifest whose id is a
digest of exactly those things, so:

* two different declarations can never share an id;
* the same declaration frozen twice is idempotent, not a second shard;
* a fixture that changes after freezing is caught by :func:`verify`, because the
  task hash is re-computed from disk and compared.

Nothing here runs a model, reads a clock, or writes outside the directory it is
given. Results live beside the manifest in their own directory — one directory
per shard, so a rerun cannot overwrite another shard's evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

SHARD_SCHEMA = "antemuse-shard-1"
KINDS = ("development", "calibration", "protected")


class ShardError(ValueError):
    """A shard declaration or file is not usable."""


class ShardConflict(ShardError):
    """A shard id already exists on disk with different content."""


class ShardDrift(ShardError):
    """A shard's tasks no longer hash to what was frozen."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _declared(values: Sequence[str], *, name: str) -> List[str]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ShardError(f"{name} must be a sequence of non-empty strings")
    out: List[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ShardError(f"{name} contains an invalid value: {value!r}")
        out.append(value.strip())
    if not out:
        raise ShardError(f"{name} must be non-empty")
    if len(set(out)) != len(out):
        raise ShardError(f"{name} contains duplicates")
    return out


def tasks_hash(tasks: Iterable[Mapping[str, Any]]) -> str:
    """A digest of the task set's content, not its file name or mtime."""
    items = sorted(
        ({"id": str(task.get("id") or ""), "brief": str(task.get("brief") or ""),
          "reference_text": str(task.get("reference_text") or "")} for task in tasks),
        key=lambda task: task["id"],
    )
    if not items:
        raise ShardError("a shard needs at least one task")
    for task in items:
        if not task["id"]:
            raise ShardError("every task needs an id")
    if len({task["id"] for task in items}) != len(items):
        raise ShardError("task ids must be unique")
    return _digest(items)


def declaration(*, kind: str, tasks: Sequence[Mapping[str, Any]], models: Sequence[str],
                conditions: Sequence[str], prompt_version: str,
                source_version: str) -> Dict[str, Any]:
    """The canonical manifest body for a shard. Pure: no I/O, no clock."""
    if kind not in KINDS:
        raise ShardError(f"kind must be one of {KINDS}, got {kind!r}")
    if not isinstance(prompt_version, str) or not prompt_version.strip():
        raise ShardError("prompt_version must be a non-empty string")
    if not isinstance(source_version, str) or not source_version.strip():
        raise ShardError("source_version must be a non-empty string")
    body = {
        "schema": SHARD_SCHEMA,
        "kind": kind,
        "tasks": sorted(str(task.get("id") or "") for task in tasks),
        "tasks_hash": tasks_hash(tasks),
        "models": sorted(_declared(models, name="models")),
        "conditions": sorted(_declared(conditions, name="conditions")),
        "prompt_version": prompt_version.strip(),
        "source_version": source_version.strip(),
    }
    body["id"] = _digest(body)
    return body


def shard_dir(root: Path | str) -> Path:
    return Path(root) / "shards"


def results_dir(root: Path | str, shard_id: str) -> Path:
    """Each shard gets its own results directory so evidence cannot collide."""
    if not isinstance(shard_id, str) or not shard_id.strip():
        raise ShardError("shard_id must be a non-empty string")
    return Path(root) / "results" / shard_id.strip()


def freeze(root: Path | str, *, kind: str, tasks: Sequence[Mapping[str, Any]],
           models: Sequence[str], conditions: Sequence[str], prompt_version: str,
           source_version: str) -> Dict[str, Any]:
    """Write a shard manifest, once.

    Returns the manifest with an extra ``frozen`` flag: ``True`` when this call
    wrote it, ``False`` when an identical manifest was already on disk. A
    different manifest under the same id is impossible unless the id was
    mangled, so that case raises instead of overwriting.
    """
    body = declaration(kind=kind, tasks=tasks, models=models, conditions=conditions,
                       prompt_version=prompt_version, source_version=source_version)
    directory = shard_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{body['id']}.json"
    text = json.dumps(body, sort_keys=True, indent=2) + "\n"

    try:
        with open(path, "x", encoding="utf-8") as handle:      # write-once
            handle.write(text)
        written = True
    except FileExistsError:
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != body:
            raise ShardConflict(
                f"shard {body['id']} already exists with different content; "
                "a shard is immutable, so declare a different one"
            ) from None
        written = False

    results_dir(root, body["id"]).mkdir(parents=True, exist_ok=True)
    return {**body, "frozen": written, "path": str(path)}


def load(root: Path | str, shard_id: str) -> Dict[str, Any]:
    path = shard_dir(root) / f"{shard_id.strip()}.json"
    if not path.is_file():
        raise ShardError(f"no shard {shard_id!r} in {shard_dir(root)}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SHARD_SCHEMA:
        raise ShardError(f"shard {shard_id!r} has schema {data.get('schema')!r}, expected {SHARD_SCHEMA!r}")
    body = {key: value for key, value in data.items() if key != "id"}
    if _digest(body) != data.get("id"):
        raise ShardError(f"shard {shard_id!r} does not match its own id; the file was edited")
    return data


def verify(root: Path | str, shard_id: str, tasks: Sequence[Mapping[str, Any]]) -> None:
    """Fail when today's task content is not what this shard was frozen on."""
    data = load(root, shard_id)
    current = tasks_hash(tasks)
    if current != data["tasks_hash"]:
        raise ShardDrift(
            f"shard {shard_id} was frozen on tasks_hash {data['tasks_hash'][:12]}, "
            f"the tasks on disk hash to {current[:12]}; the fixture changed after freezing"
        )
    if sorted(str(task.get("id") or "") for task in tasks) != data["tasks"]:
        raise ShardDrift(f"shard {shard_id} declares a different task list than the fixture")
