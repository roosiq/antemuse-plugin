"""A durable record of concepts the plugin has seen, across sessions.

Not a memory layer. The plugin must work with any memory provider by its default interface,
so nothing here writes to MEMORY.md or reads a provider behind its back. This store holds
*identity*: a term, what kind of thing it is, a stable key, and where and when it was met.

Why it exists: every state re-derived its world from scratch. The journal is a decaying
transcript, `residue` is a two-turn note, the recall ring is this conversation only, and a
walk's `seen` set is twelve terms. So no state could answer "have we been here before?" —
which is exactly what walk repeats, dream's thinness and unstuck's thin evidence all need.

Fail-open by design: a missing or corrupt database returns empty answers and records one named
failure. Entry, exit, expiry, tool restoration and rendering never depend on this module.
"""
from __future__ import annotations

import functools
import hashlib
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

#: Nothing longer than this is a concept. It is also the acceptance test for "no transcripts
#: in the ledger": a sentence cannot be stored because it cannot be a term.
MAX_TERM = 30
RETENTION_DAYS = 30
MAX_CONCEPTS = 20_000
MAX_SERVED = 60_000

STOP = set("""
a an the and or but if then than that this these those is are was were be been being am
of to in on at for with from by as it its it's their there here we you i he she they them
not no yes do does did have has had will would can could should may might must about into
over under more most less very just also so such only own same other some any each
what which who whom whose when where why how all both few many much neither either
make made get got go going gone one two three now then still even ever never always
add adds added use used uses using run runs ran set sets put keep keeps kept take takes
file files line lines code test tests spec specs doc docs read reads write writes wrote
your yours our ours my mine me us them its themselves myself yourself himself herself
exist exists exist already still yet actually really quite very much many something
anything nothing everything someone anyone everyone nobody here there where when why
like just also even again once twice about around through during before after while
need needs needed want wants wanted say says said tell tells told ask asks asked
should could would might must may can cannot able maybe perhaps probably sure
work works working worked repo repository repositories scratch start started small
enough logs log load loaded thing things stuff part parts piece pieces way ways
next last first second third number count total every each other others another
against between without within across along behind beyond toward towards though although
however therefore because since until unless whether rather almost often sometimes
""".split())

SCHEMA = """
CREATE TABLE IF NOT EXISTS concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    label TEXT NOT NULL,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    times INTEGER NOT NULL DEFAULT 1,
    UNIQUE(kind, key)
);
CREATE TABLE IF NOT EXISTS served (
    concept_id INTEGER NOT NULL,
    move TEXT NOT NULL,
    session TEXT NOT NULL DEFAULT '',
    at REAL NOT NULL,
    used_at REAL
);
CREATE INDEX IF NOT EXISTS idx_served_concept ON served(concept_id, at);
CREATE INDEX IF NOT EXISTS idx_served_session ON served(session, at);
CREATE TABLE IF NOT EXISTS moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    started REAL NOT NULL,
    ended REAL,
    ending TEXT,
    dose_done INTEGER
);
CREATE TABLE IF NOT EXISTS links (
    a TEXT NOT NULL,
    b TEXT NOT NULL,
    relation TEXT NOT NULL,
    move TEXT NOT NULL,
    at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS cursor (name TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

_FAILED: Dict[str, float] = {}


def _home() -> Path:
    """The plugin data dir. An explicit override is honoured even when it cannot be made:
    falling back to the real data dir would let a test or a typo write into the user's own
    ledger, which is worse than failing."""
    override = os.environ.get("ANTEMUSE_STATES_HOME")
    if override:
        return Path(override)
    try:
        from . import storage
        return storage.data_dir()
    except Exception:
        return Path.home() / ".hermes" / "plugin-data" / "antemuse"


def db_path() -> Path:
    return _home() / "concepts.db"


def _connect() -> Optional[sqlite3.Connection]:
    """A connection, or None. Never raises: this store is not allowed to break a state."""
    try:
        path = db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), timeout=3.0)
        conn.executescript(SCHEMA)
        return conn
    except Exception as exc:
        _note_failure(f"concept ledger unavailable · {str(exc).splitlines()[0][:80]}")
        return None


def _note_failure(text: str) -> None:
    """One failure event per five minutes, so a broken store cannot flood the journal."""
    now = time.time()
    if now - _FAILED.get(text, 0) < 300:
        return
    _FAILED[text] = now
    try:
        from . import engine
        engine.record("state", text, event="history")
    except Exception:
        pass


# --------------------------------------------------------------------- identity

def normalise(term: str) -> str:
    return re.sub(r"[^a-z0-9 \-]", "", (term or "").strip().lower())[:MAX_TERM].strip()


@functools.lru_cache(maxsize=20_000)
def _synset(low: str) -> str:
    """The first synset name for a term, or "". Cached: a session scan asks thousands of
    times for the same few hundred words, and WordNet lookups were the whole cost."""
    try:
        from .sources import _wn
        syns = _wn().synsets(low.replace(" ", "_"))
        return syns[0].name() if syns else ""
    except Exception:
        return ""


def identify(term: str) -> Optional[Tuple[str, str, str]]:
    """`(kind, key, label)` for a term — WordNet synset where possible, lemma otherwise.

    Merging on the synset is what makes "shipper", "shipping" and "shipped" one concept; the
    label stays as it was seen so a line can read the way it read.
    """
    label = normalise(term)
    if len(label) < 3 or label in STOP:
        return None
    key = _synset(label)
    if key:
        return ("wordnet", key, label)
    return ("lemma", label, label)


# ---------------------------------------------------------------------- writing

def active_session() -> str:
    try:
        from . import engine
        state = engine.watch_state() or {}
        return str(state.get("session_id") or "")
    except Exception:
        return ""


def notice(term: str, move: str = "", session: str = "", kind: str = "",
           key: str = "", at: Optional[float] = None) -> None:
    """Record one sighting. Cheap, idempotent per (kind, key), and never raises."""
    now = at or time.time()
    session = session or active_session()
    ident = (kind, key, normalise(term)) if kind and key else identify(term)
    if not ident:
        return
    kind, key, label = ident
    conn = _connect()
    if conn is None:
        return
    try:
        with conn:
            conn.execute(
                """INSERT INTO concepts(kind, key, label, first_seen, last_seen, times)
                   VALUES(?,?,?,?,?,1)
                   ON CONFLICT(kind, key) DO UPDATE SET
                     last_seen=excluded.last_seen, times=times+1""",
                (kind, key, label[:MAX_TERM], now, now))
            cid = conn.execute("SELECT id FROM concepts WHERE kind=? AND key=?",
                               (kind, key)).fetchone()[0]
            conn.execute("INSERT INTO served(concept_id, move, session, at) VALUES(?,?,?,?)",
                         (cid, move or "", session or "", now))
        _prune(conn, now)
    except Exception as exc:
        _note_failure(f"concept write failed · {str(exc).splitlines()[0][:70]}")
    finally:
        conn.close()


def link(a: str, b: str, relation: str = "shared", move: str = "") -> None:
    conn = _connect()
    if conn is None:
        return
    try:
        with conn:
            conn.execute("INSERT INTO links(a, b, relation, move, at) VALUES(?,?,?,?,?)",
                         (a[:MAX_TERM], b[:MAX_TERM], relation, move, time.time()))
    except Exception:
        pass
    finally:
        conn.close()


def mark_move(state: str, started: float, ended: Optional[float] = None,
              ending: str = "", dose_done: Optional[int] = None) -> None:
    conn = _connect()
    if conn is None:
        return
    try:
        with conn:
            conn.execute("""INSERT INTO moves(state, started, ended, ending, dose_done)
                            VALUES(?,?,?,?,?)""", (state, started, ended, ending, dose_done))
    except Exception:
        pass
    finally:
        conn.close()


def _prune(conn: sqlite3.Connection, now: float) -> None:
    horizon = now - RETENTION_DAYS * 86400
    conn.execute("DELETE FROM served WHERE at < ? AND used_at IS NULL", (horizon,))
    conn.execute("""DELETE FROM concepts WHERE last_seen < ?
                    AND id NOT IN (SELECT concept_id FROM served)""", (horizon,))
    conn.execute("""DELETE FROM concepts WHERE id IN (
                      SELECT id FROM concepts ORDER BY last_seen DESC LIMIT -1 OFFSET ?)""",
                 (MAX_CONCEPTS,))
    conn.execute("""DELETE FROM served WHERE rowid IN (
                      SELECT rowid FROM served ORDER BY at DESC LIMIT -1 OFFSET ?)""",
                 (MAX_SERVED,))


# ---------------------------------------------------------------------- reading

def _query(sql: str, args: Iterable[Any] = ()) -> List[Tuple]:
    conn = _connect()
    if conn is None:
        return []
    try:
        return conn.execute(sql, tuple(args)).fetchall()
    except Exception as exc:
        _note_failure(f"concept read failed · {str(exc).splitlines()[0][:70]}")
        return []
    finally:
        conn.close()


def _row(term: str) -> Optional[Tuple[str, str, str]]:
    return identify(term)


def seen_before(term: str, exclude_session: str = "") -> Dict[str, Any]:
    """When and where this concept was met, ignoring the session we are in.

    The answer dream and unstuck need: not "does the word exist" but "we have been here,
    then, in that many sessions".
    """
    ident = _row(term)
    if ident is None:
        return {}
    kind, key, label = ident
    rows = _query("""SELECT id, first_seen, last_seen, times FROM concepts
                     WHERE kind=? AND key=?""", (kind, key))
    if not rows:
        return {}
    cid, first, last, times = rows[0]
    hits = _query("""SELECT session, at FROM served WHERE concept_id=?
                     AND session != ? ORDER BY at DESC LIMIT 8""", (cid, exclude_session or ""))
    sessions = sorted({h[0] for h in hits if h[0]})
    return {"key": key, "kind": kind, "label": label, "times": times,
            "first_seen": first, "last_seen": last,
            "sessions": len(sessions), "session_ids": sessions,
            "last_session_at": hits[0][1] if hits else None}


def in_session(session: str, limit: int = 40) -> List[str]:
    return [r[0] for r in _query("""SELECT DISTINCT c.label FROM served s
                                    JOIN concepts c ON c.id = s.concept_id
                                    WHERE s.session=? ORDER BY s.at DESC LIMIT ?""",
                                 (session, limit))]


def circling(days: int = 7, min_sessions: int = 2, limit: int = 12,
             share: float = 0.35) -> List[Dict[str, Any]]:
    """Concepts that keep coming back across sessions — relevance by repetition.

    A word in *every* session is the session template talking ("work", "repo"), not a
    concept the work keeps returning to. So the upper bound matters as much as the lower one:
    a concept whose session count exceeds `share` of all sessions in the window is boilerplate.
    """
    since = time.time() - days * 86400
    total = _query("SELECT COUNT(DISTINCT session) FROM served WHERE at >= ?", (since,))
    sessions_in_window = total[0][0] if total else 0
    # a boilerplate filter needs a corpus to be boilerplate *in*: with a handful of sessions
    # there is no "every session says this", so the upper bound does not apply yet
    ceiling = (sessions_in_window if sessions_in_window < 8
               else max(min_sessions, int(sessions_in_window * share)))
    rows = _query("""SELECT c.label, c.kind, c.key, COUNT(DISTINCT s.session) AS n,
                            MAX(s.at) AS last
                     FROM served s JOIN concepts c ON c.id = s.concept_id
                     WHERE s.at >= ?
                     GROUP BY c.id HAVING n >= ? AND n <= ?
                     ORDER BY n DESC, last DESC LIMIT ?""",
                  (since, min_sessions, ceiling, limit))
    return [{"label": r[0], "kind": r[1], "key": r[2], "sessions": r[3], "last": r[4]}
            for r in rows]


def unused(days: int = 7, limit: int = 12) -> List[str]:
    since = time.time() - days * 86400
    return [r[0] for r in _query("""SELECT DISTINCT c.label FROM served s
                                    JOIN concepts c ON c.id = s.concept_id
                                    WHERE s.at >= ? AND s.used_at IS NULL
                                    ORDER BY s.at DESC LIMIT ?""", (since, limit))]


def recent(days: int = 3, limit: int = 40) -> List[Dict[str, Any]]:
    since = time.time() - days * 86400
    rows = _query("""SELECT c.label, c.kind, c.key, s.move, s.session, s.at
                     FROM served s JOIN concepts c ON c.id = s.concept_id
                     WHERE s.at >= ? ORDER BY s.at DESC LIMIT ?""", (since, limit))
    return [{"label": r[0], "kind": r[1], "key": r[2], "move": r[3], "session": r[4], "at": r[5]}
            for r in rows]


def when(ts: Optional[float]) -> str:
    if not ts:
        return ""
    days = (time.time() - ts) / 86400
    if days < 1:
        return "earlier today"
    if days < 2:
        return "yesterday"
    if days < 14:
        return f"{int(days)} days ago"
    return f"{int(days / 7)} weeks ago"


def known(term: str, exclude_session: str = "") -> bool:
    return bool(seen_before(term, exclude_session).get("sessions"))


def stats() -> Dict[str, Any]:
    rows = _query("SELECT COUNT(*), COUNT(DISTINCT key) FROM concepts")
    served = _query("SELECT COUNT(*), COUNT(DISTINCT session) FROM served")
    return {"concepts": rows[0][0] if rows else 0,
            "keys": rows[0][1] if rows else 0,
            "servings": served[0][0] if served else 0,
            "sessions": served[0][1] if served else 0}


# ------------------------------------------------------- past-session extraction

HERMES_DB = Path.home() / ".hermes" / "state.db"


@functools.lru_cache(maxsize=20_000)
def _is_concept(word: str) -> bool:
    """A concept is a thing, so: a noun, or a word WordNet has never heard of.

    Verbs and adjectives were making up a third of everything extracted ("exist",
    "already", "actually"), and a ledger full of those is a word counter, not a history of
    what the work was about. An unknown word is kept because jargon is exactly the kind of
    concept this repo uses — `antemuse`, `toslop`, `kanban` are not in WordNet and matter
    more than any dictionary noun.
    """
    low = normalise(word)
    if len(low) < 3 or low in STOP:
        return False
    try:
        from .sources import _wn
        wn = _wn()
        if wn.synsets(low.replace(" ", "_"), pos="n"):
            # A short dictionary noun is usually a function word in disguise: "point",
            # "look", "let", "state". Six characters is where English nouns start carrying
            # their own weight; below that only a word WordNet has never seen is kept,
            # because jargon is exactly what this repo's concepts are.
            return len(low) >= 6
        if wn.synsets(low.replace(" ", "_")):
            return False                      # known, but only as verb or adjective
        return len(low) >= 4
    except Exception:
        return len(low) >= 4


def extract(text: str, limit: int = 24) -> List[str]:
    """Candidate concepts in a piece of text: identity only, nothing verbatim but a term."""
    out: List[str] = []
    seen = set()
    for word in re.findall(r"[A-Za-z][A-Za-z0-9\-']{2,}", text or ""):
        low = normalise(word)
        if low in seen or not _is_concept(word):
            continue
        seen.add(low)
        out.append(low)
        if len(out) >= limit:
            break
    return out


def scan_sessions(days: int = 7, batch: int = 400, source: str = "",
                  db: Optional[Path] = None) -> Dict[str, Any]:
    """Read past Hermes sessions and record their concepts. Read-only, incremental, bounded.

    Only user and assistant text is read: tool output and reasoning are not concepts, and
    reading them would make this a transcript scanner. The cursor makes a repeat call cheap.
    """
    path = Path(db or source or HERMES_DB)
    if not path.exists():
        return {"ok": False, "reason": f"no session store at {path}"}
    since = time.time() - days * 86400
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=3.0)
    except Exception as exc:
        return {"ok": False, "reason": str(exc).splitlines()[0][:80]}
    try:
        # the cursor lives in *our* ledger, not in the read-only session store
        row = _query("SELECT value FROM cursor WHERE name='session_scan'")
        start = int(row[0][0]) if row else 0
        message = conn.execute(
            """SELECT id, session_id, role, content FROM messages
               WHERE id > ? AND timestamp >= ? AND role IN ('user','assistant')
               AND content IS NOT NULL AND length(content) > 0
               ORDER BY id LIMIT ?""", (start, since, batch)).fetchall()
        scanned, stored, sessions = 0, 0, set()
        last = start
        for mid, sid, _role, content in message:
            scanned += 1
            last = max(last, mid)
            sessions.add(sid)
            for term in extract(content):
                notice(term, move="session", session=sid)
                stored += 1
        _set_cursor("session_scan", str(last))
        return {"ok": True, "scanned": scanned, "stored": stored,
                "sessions": len(sessions), "cursor": last,
                "more": len(message) == batch}
    except Exception as exc:
        return {"ok": False, "reason": str(exc).splitlines()[0][:80]}
    finally:
        conn.close()


def _set_cursor(name: str, value: str) -> None:
    conn = _connect()
    if conn is None:
        return
    try:
        with conn:
            conn.execute("INSERT INTO cursor(name, value) VALUES(?,?) "
                         "ON CONFLICT(name) DO UPDATE SET value=excluded.value", (name, value))
    except Exception:
        pass
    finally:
        conn.close()


def session_of(state: Optional[Dict[str, Any]]) -> str:
    return str((state or {}).get("session_id") or "")
