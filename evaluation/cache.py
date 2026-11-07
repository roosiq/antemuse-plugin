"""Experiment evaluation cache: keys bind every condition, records are append-only.

A cached response is only valid for the exact experiment condition that produced
it. The key covers model, condition, task, prompt version, source version, and
seed; JSONL shards keep one record per line so independent shards can be written
by independent workers without a shared index. There is no cross-process locking:
callers that share a shard must serialize their writes.

Both directions fail closed. A shard line that is not a JSON object holding a
``record`` object and a string ``key`` raises ``ValueError`` naming the file and
line rather than being skipped, so a truncated write can never masquerade as an
absent key. Writes are strict JSON: records must be JSON-native values (string
object keys only), NaN and Infinity raise, and a shard whose last byte is not a
newline is refused instead of having a new record fused onto its truncated tail.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

__all__ = ["condition_cache_key", "JsonlCache"]

_FIELDS = ("model", "condition", "task_id", "prompt_version", "source_version", "seed")


def _check_json_value(value: Any, path: str) -> None:
    """Reject values that JSON cannot round-trip exactly, naming their path.

    ``json.dumps`` silently rewrites some Python values - integer dict keys
    become strings, tuples become lists - which would break the "get returns the
    exact record that was put" contract without any error at all. Validation
    here runs before the shard is opened, so a rejected record writes nothing.

    Non-finite floats raise ``ValueError`` for the same reason the encoder's
    ``allow_nan=False`` does: NaN and Infinity have no JSON representation.
    """
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path}: {value!r} is not a finite JSON number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"{path}: object key {key!r} is not a string; "
                    "JSON object keys must be strings"
                )
            _check_json_value(item, f"{path}[{key!r}]")
        return
    raise TypeError(f"{path}: {type(value).__name__} is not a JSON value")


def condition_cache_key(
    *,
    model: str,
    condition: str,
    task_id: str,
    prompt_version: str,
    source_version: str,
    seed: int,
) -> str:
    """Return a deterministic SHA-256 hex digest naming one experiment condition.

    The digest is taken over canonical JSON (sorted keys, explicit field names,
    no whitespace) so reordering or formatting cannot change it. Only the
    condition identifiers are hashed; prompt and response text never enter the
    key.

    Every string field must be a non-empty identifier. An empty or
    whitespace-only value raises ``ValueError``: it would otherwise collapse two
    experiments that forgot to set a condition onto one key, which is exactly the
    cross-condition reuse this function exists to prevent.
    """
    payload: Dict[str, Any] = {
        "model": model,
        "condition": condition,
        "task_id": task_id,
        "prompt_version": prompt_version,
        "source_version": source_version,
        "seed": seed,
    }
    for field in _FIELDS[:-1]:
        value = payload[field]
        if not isinstance(value, str):
            raise TypeError(f"{field} must be a string, got {type(value).__name__}")
        if not value.strip():
            raise ValueError(f"{field} must be a non-empty identifier, got {value!r}")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError(f"seed must be an int, got {type(seed).__name__}")

    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class JsonlCache:
    """An append-only JSONL shard of ``{"key": ..., "record": ...}`` lines.

    ``get`` returns ``None`` when the key is absent and the stored object on an
    exact key match. Re-putting a key appends a new line, and the last record
    for that key wins, so a shard can be replayed in order.

    ``get`` raises ``ValueError`` on any line that is not a JSON object carrying
    a ``record`` object, naming the file and line. Skipping such a line would
    report a miss — or return stale data — for a key whose newer record was
    truncated, which is indistinguishable from an empty cache.
    """

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if not self.path.exists():
            return None
        found: Optional[Dict[str, Any]] = None
        with self.path.open("r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"{self.path}:{lineno}: malformed JSON: {exc.msg}"
                    ) from exc
                if not isinstance(entry, dict):
                    raise ValueError(
                        f"{self.path}:{lineno}: cache entry is not a JSON object"
                    )
                record = entry.get("record")
                if not isinstance(record, dict):
                    raise ValueError(
                        f"{self.path}:{lineno}: cache record is not a JSON object"
                    )
                stored_key = entry.get("key")
                if not isinstance(stored_key, str):
                    raise ValueError(
                        f"{self.path}:{lineno}: cache entry has no string key "
                        f"(got {type(stored_key).__name__})"
                    )
                if stored_key == key:
                    found = record
        return found

    def put(self, key: str, record: Dict[str, Any]) -> None:
        if not isinstance(key, str):
            raise TypeError(f"key must be a string, got {type(key).__name__}")
        if not isinstance(record, dict):
            raise TypeError(f"record must be a dict, got {type(record).__name__}")
        # Reject values JSON would rewrite (int keys, tuples, ...) before the
        # shard is opened, so a rejected record appends nothing.
        _check_json_value(record, "record")
        # Serialize first, with allow_nan=False: a record holding NaN/Infinity is
        # not JSON, and the write must fail before any byte reaches the shard.
        line = json.dumps(
            {"key": key, "record": record},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        # A non-empty shard must end with a newline. Appending to a truncated
        # tail (what a killed write leaves) would fuse two JSON objects onto one
        # line and make every key in the shard unreadable, so refuse instead.
        if self.path.exists() and self.path.stat().st_size:
            with self.path.open("rb") as fh:
                fh.seek(-1, os.SEEK_END)
                last = fh.read(1)
            if last != b"\n":
                raise ValueError(
                    f"{self.path}: refusing to append: shard does not end with a "
                    "newline, so the last line is truncated"
                )
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
