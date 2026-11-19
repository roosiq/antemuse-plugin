"""Recent turns, provider-neutral.

Hermes owns memory and swaps its backend at will (`memory.provider`); it exposes no
plugin-facing read. So a state that wants "something this person actually said" must
not depend on which banker is on duty. The one thing every provider hands a plugin is
the turn itself — `pre_llm_call` carries `user_message` and `conversation_history` — so
this module keeps a bounded ring of what the conversation has said, in the plugin's own
data dir, and the walk's seeding draws from it before falling back to the built-in memory files.

Bounded on purpose: 24 entries, 400 characters each, newest wins. This is a working
surface, not a store; nothing here is written back to Hermes memory.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from . import storage

CAP = 24
#: How many chats the ring keeps. The cap is per chat, not global: one file serves the whole
#: profile, and a single busy conversation used to evict every other chat's material — measured
#: live as 18 of 24 rows held by one chat, leaving another unable to start daydream.
CHATS = 8
MAX_CHARS = 400
FILENAME = "recent_turns.json"


def path() -> Path:
    """Resolved at call time: `ANTEMUSE_STATES_HOME` can be set after import."""
    return storage.data_dir() / FILENAME


def _load() -> List[Dict[str, Any]]:
    file = path()
    try:
        data = json.loads(file.read_text())
    except Exception:
        return []
    return _bounded([item for item in data if isinstance(item, dict) and item.get("text")])


def _bounded(items):
    """Keep the last CAP rows of each of the last CHATS chats, in arrival order.

    Bounded overall at CAP * CHATS rows, so a chatty session cannot spend another's quota.
    """
    order = []
    for item in items:
        key = str(item.get("session") or "")
        if key in order:
            order.remove(key)
        order.append(key)
    keep = set(order[-CHATS:])
    seen = {}
    out = []
    for item in reversed(items):
        key = str(item.get("session") or "")
        if key not in keep:
            continue
        seen[key] = seen.get(key, 0) + 1
        if seen[key] <= CAP:
            out.append(item)
    out.reverse()
    return out


def _save(items: List[Dict[str, Any]]) -> None:
    file = path()
    try:
        file.parent.mkdir(parents=True, exist_ok=True)
        tmp = file.with_suffix(".tmp")
        tmp.write_text(json.dumps(_bounded(items)))
        os.replace(tmp, file)
    except Exception:
        pass  # a full disk must not cost the turn


def remember(text: str, who: str = "person", session: str = "") -> None:
    """Keep one line of the conversation, stamped with the chat it was said in.

    The ring is one file per profile, so without the stamp a daydream in one chat served
    another chat's private turns as its material. An empty session means "nobody in
    particular" (a caller with no session id), which is the plugin's existing rule.
    """
    clean = " ".join(str(text or "").split())[:MAX_CHARS]
    if len(clean) < 12:
        return
    items = _load()
    if items and items[-1].get("text") == clean and items[-1].get("who") == who:
        return
    items.append({"who": who, "text": clean, "at": time.time(), "session": str(session or "")})
    _save(items)


def recent(limit: int = 6, who: str | None = None, session: str | None = None) -> List[str]:
    """What was said, optionally only in one chat.

    `session=None` reads the whole ring (a caller that has no chat context). A session id
    reads only that chat's turns. An unattributed row belongs to no chat: including it let
    migrated or partially written text from one conversation become another's material.
    """
    items = _load()
    if who:
        items = [item for item in items if item.get("who") == who]
    if session is not None:
        items = [item for item in items if str(item.get("session") or "") == str(session)]
    return [item["text"] for item in items[-limit:]]


def clear() -> None:
    try:
        path().unlink()
    except Exception:
        pass
