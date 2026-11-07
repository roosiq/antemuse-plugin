"""Typed Collider source artifacts.

A collider example is an imported piece of another discipline's real thinking. The
source entry is preserved verbatim in ``body`` — that field is the one carried
over unchanged — while ``mechanism`` is a faithful condensation of the entry and
``bridge_question`` restates its question. The provenance record says exactly
where the entry came from and what its licence status is, so a reader can check
the import against the source and see which parts were condensed.

Nothing here resolves the source over the network. Loading is offline and strict:
missing fields, a wrong kind, a status that implies more verification than the
import has, an incomplete provenance record, a bridge question that does not appear
in the source entry, or a hash that no longer matches the mechanism and question all
fail loudly with the field name. The content hash covers only ``mechanism`` and
``bridge_question``, not the whole record: ``body``, ``title``, ``family``, and the
provenance values sit outside the digest and are pinned by callers instead.

Selection is a separate, deterministic layer. ``select_sources`` picks sources for a
new walk from three declared strategies — fresh, deepen, refresh — using a local
``random.Random(seed)``; the policy is documented at the function because it is a
sampling rule, not a judgement about how good a source is. Nothing in this module
scores, ranks, or filters artifacts by quality, and nothing extracts mechanisms with
a model: deepen and refresh identify families from the ids of sources the walker
already loved or liked.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

REQUIRED_FIELDS: Tuple[str, ...] = (
    "id",
    "kind",
    "family",
    "title",
    "mechanism",
    "bridge_question",
    "body",
    "provenance",
    "verification_status",
    "content_hash",
)

PROVENANCE_FIELDS: Tuple[str, ...] = (
    "repository",
    "pinned_commit",
    "path",
    "license",
)

KIND = "collider_example"
VERIFICATION_STATUS = "generated_example"

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}\Z")


def content_hash(mechanism: str, bridge_question: str) -> str:
    """The hash an artifact must carry: mechanism, newline, bridging question."""
    digest = hashlib.sha256(
        (mechanism + "\n" + bridge_question).encode("utf-8")
    ).hexdigest()
    return "sha256:" + digest


def _require_text(record: Dict[str, Any], field: str, where: str) -> str:
    value = record[field]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}{field} must be a non-empty string")
    return value


def _normalized(text: str) -> str:
    """Whitespace-normalized text, so line wrapping does not defeat a substring check."""
    return " ".join(text.split())


def _check_provenance(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("provenance must be an object")
    for field in PROVENANCE_FIELDS:
        if field not in value:
            raise ValueError(f"provenance.{field} is missing")
        _require_text(value, field, "provenance.")
    return value


def load_artifact(path: Any) -> Dict[str, Any]:
    """Load one collider artifact, validating every field it promises to carry.

    Raises ValueError naming the offending field on invalid data.
    """
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source.name}: not valid JSON ({exc})") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{source.name}: artifact must be a JSON object")

    for field in REQUIRED_FIELDS:
        if field not in data:
            raise ValueError(f"missing required field: {field}")

    for field in ("id", "family", "title", "mechanism", "bridge_question", "body"):
        _require_text(data, field, "")

    if data["kind"] != KIND:
        raise ValueError(f"kind must be {KIND!r}, got {data['kind']!r}")

    if data["verification_status"] != VERIFICATION_STATUS:
        raise ValueError(
            "verification_status must be "
            f"{VERIFICATION_STATUS!r}, got {data['verification_status']!r}"
        )

    _check_provenance(data["provenance"])

    stored = data["content_hash"]
    if not isinstance(stored, str) or not _HASH_RE.match(stored):
        raise ValueError("content_hash must be 'sha256:' followed by 64 lowercase hex digits")

    expected = content_hash(data["mechanism"], data["bridge_question"])
    if stored != expected:
        raise ValueError(
            "content_hash does not match mechanism + newline + bridge_question "
            f"(stored {stored}, computed {expected})"
        )

    if _normalized(data["bridge_question"]) not in _normalized(data["body"]):
        raise ValueError(
            "bridge_question must appear in body after whitespace normalization: "
            f"{data['bridge_question']!r} is not in the recorded source entry"
        )

    return data


BANK_DIR = Path(__file__).resolve().parents[1] / "data" / "collider"

STRATEGIES: Tuple[str, ...] = ("fresh", "deepen", "refresh")


def load_bank(directory: Any = None) -> List[Dict[str, Any]]:
    """Load every artifact in the bundled bank, in filename order.

    Each file goes through ``load_artifact``, so a drifted artifact fails here with
    the same field-name error it would raise on its own. Ids must be unique across
    the bank; a repeated id would make family lookup for deepen/refresh ambiguous.
    """
    root = Path(directory) if directory is not None else BANK_DIR
    paths = sorted(root.glob("*.json"))
    if not paths:
        raise ValueError(f"no collider artifacts found in {root}")

    artifacts = [load_artifact(path) for path in paths]
    seen: Dict[str, Path] = {}
    for path, artifact in zip(paths, artifacts):
        if artifact["id"] in seen:
            raise ValueError(
                f"duplicate artifact id {artifact['id']!r} in "
                f"{seen[artifact['id']].name} and {path.name}"
            )
        seen[artifact["id"]] = path
    return artifacts


def _string_set(value: Optional[Iterable[str]], name: str) -> frozenset:
    """Copy an argument's strings into a frozenset, so the caller's value is untouched."""
    if value is None:
        return frozenset()
    if isinstance(value, str):
        raise ValueError(f"{name} must be a set of strings, not a single string")
    try:
        items = list(value)
    except TypeError as exc:
        raise ValueError(f"{name} must be a set of strings") from exc
    for item in items:
        if not isinstance(item, str):
            raise ValueError(f"{name} must contain only strings, got {item!r}")
    return frozenset(items)


def _count(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"count must be a non-negative integer or None, got {value!r}")
    if value < 0:
        raise ValueError(f"count must be a non-negative integer or None, got {value!r}")
    return value


def _ids_to_families(
    ids: frozenset, families_by_id: Dict[str, str], name: str
) -> frozenset:
    if not ids:
        raise ValueError(f"{name} is empty; it must contain ids the walker responded to")
    resolved = {families_by_id[i] for i in ids if i in families_by_id}
    if not resolved:
        raise ValueError(
            f"none of the ids in {name} appear in artifacts, so no family can be "
            f"deepened or refreshed from them: {sorted(ids)!r}"
        )
    return frozenset(resolved)


def select_sources(
    artifacts: Sequence[Dict[str, Any]],
    *,
    strategy: str,
    seed: Any,
    previous_families: Optional[Iterable[str]] = None,
    loved: Optional[Iterable[str]] = None,
    liked: Optional[Iterable[str]] = None,
    count: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Pick sources for the next walk from a loaded bank.

    Policy, in order:

    * ``strategy`` must be ``fresh``, ``deepen``, or ``refresh``; ``artifacts`` must be
      non-empty. Both are checked before any selection happens.
    * ``fresh`` drops every artifact whose family is in ``previous_families``.
      ``deepen`` keeps only families that some id in ``loved`` belongs to.
      ``refresh`` keeps only families that some id in ``loved`` or ``liked`` belongs
      to. Ids that are not in the bank contribute nothing; a strategy whose filter
      resolves to no family raises ``ValueError`` naming the constraint, and so does
      a filter that leaves no artifacts at all.
    * Candidates are shuffled with a local ``random.Random(seed)`` — never the global
      RNG, and the seed is not advanced between calls — then truncated to ``count``
      (``None`` means all; ``0`` legitimately selects nothing). The selected set is
      put back in the bank's own order before it is returned, so the result reads in
      source order and a re-run with the same seed reproduces it exactly. When
      ``count`` covers every candidate, the shuffle cannot reorder the result: it is
      the full candidate list in source order.
    * The shuffle is over artifacts, not families, so a selected set may contain two
      sources from one family. Fresh only promises that excluded families do not
      appear.
    * Every artifact is returned as the loaded record, provenance included. Nothing
      is re-ranked: the seed chooses among equally acceptable sources, and a
      different seed is a different draw, not a better one.

    ``previous_families``, ``loved``, and ``liked`` are copied and never mutated.
    """
    if strategy not in STRATEGIES:
        raise ValueError(
            f"strategy must be one of {', '.join(repr(s) for s in STRATEGIES)}, "
            f"got {strategy!r}"
        )

    records = list(artifacts)
    if not records:
        raise ValueError("artifacts must be a non-empty sequence of collider artifacts")

    families_by_id: Dict[str, str] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each artifact must be a mapping with id and family")
        artifact_id = record.get("id")
        family = record.get("family")
        if not isinstance(artifact_id, str) or not artifact_id:
            raise ValueError("each artifact must carry a non-empty string id")
        if not isinstance(family, str) or not family:
            raise ValueError(f"artifact {artifact_id!r} must carry a non-empty family")
        if artifact_id in families_by_id:
            raise ValueError(f"duplicate artifact id: {artifact_id!r}")
        families_by_id[artifact_id] = family

    limit = _count(count)
    excluded = _string_set(previous_families, "previous_families")
    loved_ids = _string_set(loved, "loved")
    liked_ids = _string_set(liked, "liked")

    if strategy == "fresh":
        candidates = [r for r in records if r["family"] not in excluded]
        if not candidates:
            raise ValueError(
                "fresh selected no artifacts: previous_families excludes every family "
                f"in the bank ({sorted(excluded)!r})"
            )
    elif strategy == "deepen":
        wanted = _ids_to_families(loved_ids, families_by_id, "loved")
        candidates = [r for r in records if r["family"] in wanted]
        if not candidates:
            raise ValueError(
                "deepen selected no artifacts: no artifact family is in "
                f"{sorted(wanted)!r}"
            )
    else:
        wanted = _ids_to_families(loved_ids | liked_ids, families_by_id, "loved or liked")
        candidates = [r for r in records if r["family"] in wanted]
        if not candidates:
            raise ValueError(
                "refresh selected no artifacts: no artifact family is in "
                f"{sorted(wanted)!r}"
            )

    rng = random.Random(seed)
    order = list(range(len(candidates)))
    rng.shuffle(order)
    chosen = order if limit is None else order[:limit]
    return [candidates[index] for index in sorted(chosen)]
