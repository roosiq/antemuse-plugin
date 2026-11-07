"""Typed run events become operations a surface can show, and nothing else.

The run knows more than any surface is allowed to publish: the prompt it was
given, the messages it exchanged, the text it produced, why it chose a branch,
what it privately remembers, and the credentials it used. Those channels are
not filtered here; they are never read. A projection is assembled from a fixed
allowlist of scalar fields plus source/candidate identifiers, so an unknown
field cannot ride along and a nested one cannot climb out.

  project_event(event, surface=...)  one operation, or None if inadmissible
  normalize_events(events, surface)  the same operations, run/seq ordered
  serialize(op)                      strict JSON (no NaN, no Infinity)

No rendering, no wall clock, no model calls. Two calls with the same event
return byte-identical JSON.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

SURFACES = ("terminal", "chat", "dashboard")

TOKENS = ("SOURCE", "BRANCH", "SELECT", "REJECT", "FEEDBACK", "DONE", "FAIL", "USAGE", "START")

# event type -> (glyph token, lifecycle state, dashboard's factual phrase)
OPERATIONS: Dict[str, tuple] = {
    "run_started": ("START", "started", "run started"),
    "source_selected": ("SOURCE", "running", "source selected"),
    "branch_started": ("BRANCH", "running", "branch started"),
    "branch_completed": ("BRANCH", "running", "branch completed"),
    "branch_failed": ("FAIL", "running", "branch failed"),
    "candidate_selected": ("SELECT", "running", "candidate selected"),
    "candidate_rejected": ("REJECT", "running", "candidate rejected"),
    "feedback_recorded": ("FEEDBACK", "running", "feedback recorded"),
    "run_completed": ("DONE", "completed", "run completed"),
    "run_failed": ("FAIL", "failed", "run failed"),
    "usage_recorded": ("USAGE", "recorded", "usage recorded"),
}

# The four numbers a surface may account for. Everything else in usage is
# provider-side and stays with the provider.
USAGE_FIELDS = ("input_tokens", "output_tokens", "total_tokens", "cost_usd")

# Channels that must never be projected, at any depth.
BANNED_KEYS = (
    "prompt", "messages", "response_text", "reasoning", "chain_of_thought",
    "private_memory", "api_key", "authorization",
)

# Allowlisted scalars that are still text: refuse them if they carry a banned
# channel name or credential shape rather than passing it through escaped.
_BANNED_TEXT = BANNED_KEYS + ("bearer ", "password", "secret", "credential")

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9 ._:/@+-]{1,128}$")
_SAFE_STATUS_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_MAX_TEXT = 64

FIELDS = (
    "type", "operation", "state", "run_id", "seq", "at",
    "source_ids", "candidate_ids", "status", "usage",
)

TERMINAL_STATUSES = ("completed", "failed")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _finite(value: Any) -> bool:
    return _is_number(value) and math.isfinite(value)


def _clean_text(value: Any, limit: int = _MAX_TEXT) -> Optional[str]:
    """A short factual string, or None when it could carry a private channel."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > limit:
        return None
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in text):
        return None
    lowered = text.lower()
    if any(bad in lowered for bad in _BANNED_TEXT) or lowered.startswith("sk-"):
        return None
    return text


def _safe_id(value: Any) -> Optional[str]:
    """Identifiers are opaque and shallow: scalars only, never a secret."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        value = str(value)
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or not _SAFE_ID_RE.match(text):
        return None
    lowered = text.lower()
    if any(bad in lowered for bad in _BANNED_TEXT) or lowered.startswith("sk-"):
        return None
    return text


def _collect_ids(event: Dict[str, Any], plural: str, singular: str, nested: str) -> List[str]:
    """Read id lists only. Nested dicts contribute their id and nothing else."""
    found: List[Optional[str]] = []
    for key in (plural, nested):
        raw = event.get(key)
        if isinstance(raw, (list, tuple)):
            for item in raw:
                if isinstance(item, dict):
                    found.append(_safe_id(item.get("id")))
                else:
                    found.append(_safe_id(item))
        elif isinstance(raw, dict):
            found.append(_safe_id(raw.get("id")))
        elif raw is not None:
            found.append(_safe_id(raw))

    single = event.get(singular)
    if isinstance(single, dict):
        found.append(_safe_id(single.get("id")))
    else:
        found.append(_safe_id(single))

    out: List[str] = []
    for value in found:
        if value is not None and value not in out:
            out.append(value)
    return out


def _project_usage(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    usage: Dict[str, Any] = {}
    for key in USAGE_FIELDS:
        if key not in value:
            continue
        number = value[key]
        if not _finite(number):
            continue
        if key != "cost_usd" and number < 0:
            # Negative token counts are not accounting; they are noise.
            continue
        usage[key] = number
    return usage


def _project_at(value: Any) -> Any:
    """A supplied instant is copied; no clock is read to make one up."""
    if _finite(value):
        return value
    return _clean_text(value)


def _project_status(event: Dict[str, Any], derived: str) -> str:
    explicit = event.get("status")
    if isinstance(explicit, str):
        candidate = explicit.strip()
        if candidate and _SAFE_STATUS_RE.match(candidate):
            return candidate
    return derived


def project_event(event: Any, *, surface: str) -> Optional[Dict[str, Any]]:
    """One allowlisted operation for one surface, or None if not admissible."""
    if surface not in SURFACES:
        return None
    if not isinstance(event, dict):
        return None

    type_ = event.get("type")
    if not isinstance(type_, str) or type_ not in OPERATIONS:
        return None

    run_id = event.get("run_id")
    if not isinstance(run_id, str):
        return None
    run_id = _safe_id(run_id)
    if run_id is None:
        return None

    seq = event.get("seq")
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 0:
        return None

    token, state, phrase = OPERATIONS[type_]
    op: Dict[str, Any] = {
        "type": type_,
        "operation": token,
        "state": state,
        "run_id": run_id,
        "seq": seq,
        "at": _project_at(event.get("at")),
        "source_ids": _collect_ids(event, "source_ids", "source_id", "sources"),
        "candidate_ids": _collect_ids(event, "candidate_ids", "candidate_id", "candidates"),
        "status": _project_status(event, state),
        "usage": _project_usage(event.get("usage")),
    }
    if surface == "dashboard":
        # A dashboard has room for a factual phrase. It is a fixed label, never
        # a rationale: nothing here is inferred from the run.
        op["operation_text"] = phrase
    return op


def normalize_events(events: Any, surface: str) -> List[Dict[str, Any]]:
    """Project, drop what is inadmissible, order by (run_id, seq), keep status."""
    if surface not in SURFACES:
        return []
    if events is None or isinstance(events, (str, bytes, dict)):
        return []
    if not isinstance(events, Iterable):
        return []

    projected: List[tuple] = []
    for index, event in enumerate(events):
        op = project_event(event, surface=surface)
        if op is not None:
            projected.append((op["run_id"], op["seq"], index, op))

    projected.sort(key=lambda row: (row[0], row[1], row[2]))

    carried: Dict[str, str] = {}
    out: List[Dict[str, Any]] = []
    for run_id, _seq, _index, op in projected:
        previous = carried.get(run_id)
        current = op["status"]
        if previous in TERMINAL_STATUSES:
            # A terminal outcome is the run's latest status: a later usage or
            # feedback record must not demote it back to "running".
            current = previous
        op["status"] = current
        carried[run_id] = current
        out.append(op)
    return out


def serialize(op: Dict[str, Any]) -> str:
    """Strict, sorted JSON. A surface that cannot read this shows nothing."""
    return json.dumps(op, sort_keys=True, allow_nan=False, separators=(",", ":"))


__all__ = [
    "SURFACES", "TOKENS", "OPERATIONS", "USAGE_FIELDS", "BANNED_KEYS", "FIELDS",
    "project_event", "normalize_events", "serialize",
]
