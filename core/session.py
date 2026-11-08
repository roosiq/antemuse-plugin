"""The session boundary: material prepared for one session dies with it.

A state may prepare candidates for the turn that asked for them. Those
candidates belong to that session and to nothing else — a run that finishes
after its session ended must not arrive in somebody else's turn. This module is
the deterministic boundary: a dict, a lock, no inference. One session cannot
consume another's material; reads are by explicit id, for a status line.

Fail-closed throughout: an empty session id binds and takes nothing, a foreign
take returns ``None`` without consuming, releasing an unknown session is quiet,
and a full store refuses a new session rather than dropping an existing one.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_PENDING: Dict[str, Any] = {}

# One prepared set per live session. More than this at once is a bug upstream;
# the store refuses a new session rather than evicting someone's material.
MAX_SESSIONS = 8


def _key(session_id: str) -> str:
    return (session_id or "").strip()


def bind(session_id: str, material: Any) -> bool:
    """Attach the material this session prepared. Replaces an earlier binding.

    At capacity a new session is refused rather than allowed to push an older
    one out: losing material that another turn is still waiting to take is worse
    than telling the caller its binding did not happen. ``False`` therefore
    means either an empty id or a full store; callers that need to tell those
    apart can read :func:`count`.
    """
    key = _key(session_id)
    if not key:
        return False
    with _LOCK:
        if key not in _PENDING and len(_PENDING) >= MAX_SESSIONS:
            return False
        _PENDING.pop(key, None)
        _PENDING[key] = material
    return True


def take(session_id: str) -> Optional[Any]:
    """Consume this session's material. Another session's material is untouched."""
    key = _key(session_id)
    if not key:
        return None
    with _LOCK:
        return _PENDING.pop(key, None)


def peek(session_id: str) -> Optional[Any]:
    """Read without consuming, for a status line."""
    key = _key(session_id)
    if not key:
        return None
    with _LOCK:
        return _PENDING.get(key)


def release(session_id: str) -> int:
    """Drop everything this session prepared. Returns 1 when something was dropped."""
    key = _key(session_id)
    if not key:
        return 0
    with _LOCK:
        return 1 if _PENDING.pop(key, None) is not None else 0


def pending(session_id: str) -> bool:
    return peek(session_id) is not None


def count() -> int:
    with _LOCK:
        return len(_PENDING)


def clear() -> None:
    """Drop every binding. For tests and for a full reset."""
    with _LOCK:
        _PENDING.clear()
