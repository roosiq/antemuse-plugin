"""The concept ledger: identity, bounds, fail-open, and concepts from past sessions."""
from __future__ import annotations

import os
import sqlite3
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))

from core import history  # noqa: E402


@pytest.fixture()
def ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    return tmp_path / "concepts.db"


def test_the_same_concept_seen_twice_is_one_row(ledger):
    history.notice("shipper", move="walk", session="s1")
    history.notice("shipper", move="dream", session="s2")
    assert history.stats()["concepts"] == 1
    assert history.stats()["servings"] == 2


def test_a_word_wordnet_knows_only_as_a_verb_is_not_a_concept(ledger):
    assert history.extract("we exist already actually") == []


def test_a_word_wordnet_has_never_heard_of_is_a_concept(ledger):
    assert "antemuse" in history.extract("the antemuse plugin")


def test_nothing_longer_than_a_term_can_be_stored(ledger):
    history.notice("x" * 200, move="walk")
    rows = history.recent(days=1, limit=5)
    assert all(len(r["label"]) <= history.MAX_TERM for r in rows), rows
    assert not rows or "\n" not in rows[0]["label"]


def test_where_a_concept_was_met_before_this_session(ledger):
    history.notice("shipper", move="walk", session="old")
    past = history.seen_before("shipper", exclude_session="now")
    assert past["sessions"] == 1
    assert past["session_ids"] == ["old"]
    assert history.seen_before("shipper", exclude_session="old")["sessions"] == 0


def test_keeps_coming_back_across_sessions(ledger):
    for sid in ("a", "b", "c"):
        history.notice("shipper", move="walk", session=sid)
    history.notice("kob", move="walk", session="a")
    circled = history.circling(days=7, min_sessions=2)
    assert [c["label"] for c in circled] == ["shipper"], circled


def test_an_unreadable_ledger_does_not_break_a_state(tmp_path, monkeypatch):
    """Fail-open is the contract: this store is never allowed to stop a move."""
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("i am a file")
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(blocker / "sub"))
    assert history.notice("shipper") is None
    assert history.seen_before("shipper") == {}
    assert history.recent(days=1) == []
    assert history.circling(days=1) == []
    assert history.stats()["concepts"] == 0


def _fake_store(path, messages):
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE messages(id INTEGER PRIMARY KEY, session_id TEXT,
                    role TEXT, content TEXT, timestamp REAL)""")
    conn.executemany("INSERT INTO messages(id, session_id, role, content, timestamp) "
                     "VALUES(?,?,?,?,?)", messages)
    conn.commit()
    conn.close()


def test_a_scan_identifies_concepts_from_past_sessions(tmp_path, monkeypatch):
    ledger_dir = tmp_path / "home"
    ledger_dir.mkdir()
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(ledger_dir))
    store = tmp_path / "state.db"
    now = time.time()
    _fake_store(store, [
        (1, "session-a", "user", "the shipper retries the same lane twice", now),
        (2, "session-b", "assistant", "the shipper drops the second retry", now),
        (3, "session-b", "tool", "RAW TOOL OUTPUT that must never be read", now),
    ])
    result = history.scan_sessions(days=2, batch=10, db=store)
    assert result["ok"] and result["scanned"] == 2, result
    assert result["sessions"] == 2
    past = history.seen_before("shipper", exclude_session="")
    assert past["sessions"] >= 1 and "shipper" in past["label"]
    # and the tool message was not read at all
    assert "raw" not in {r["label"] for r in history.recent(days=1, limit=50)}


def test_a_second_scan_does_not_re_read_the_same_messages(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(home))
    store = tmp_path / "state.db"
    _fake_store(store, [(1, "s", "user", "the ledger remembers concepts", time.time())])
    first = history.scan_sessions(days=2, batch=10, db=store)
    second = history.scan_sessions(days=2, batch=10, db=store)
    assert first["scanned"] == 1
    assert second["scanned"] == 0, second


def test_a_scan_that_cannot_open_the_store_says_so(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path / "home"))
    result = history.scan_sessions(days=1, db=tmp_path / "missing.db")
    assert result["ok"] is False and "session store" in result["reason"]


def test_old_sightings_are_pruned_and_recent_ones_are_kept(ledger):
    history.notice("shipper", move="walk", session="old")
    conn = sqlite3.connect(ledger)
    conn.execute("UPDATE served SET at = ?", (time.time() - (history.RETENTION_DAYS + 2) * 86400,))
    conn.commit()
    conn.close()
    history.notice("kob", move="walk", session="new")
    labels = {r["label"] for r in history.recent(days=1, limit=20)}
    assert "kob" in labels
    assert "shipper" not in labels, "a sighting older than the window must be pruned"
