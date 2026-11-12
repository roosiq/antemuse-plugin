"""The automatic scan: once per session, bounded both ways, and never in the turn's way."""
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
def store(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    from core import settings
    settings.override(session_scan=True)
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(home))
    db = tmp_path / "state.db"
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE messages(id INTEGER PRIMARY KEY, session_id TEXT,
                    role TEXT, content TEXT, timestamp REAL)""")
    now = time.time()
    rows = [(i, f"past-{i % 5}", "user", f"the shipper ledger retries lane {i} twice", now)
            for i in range(1, 21)]
    conn.executemany("INSERT INTO messages(id, session_id, role, content, timestamp) "
                     "VALUES(?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    monkeypatch.setattr(history, "_SCAN_LOCK", {"running": False})
    return db


def test_it_scans_once_and_stores_concepts(store):
    first = history.autoscan("session-1", db=store, wait=True)
    assert first["ok"] and first["scanned"] == 20, first
    assert history.stats()["concepts"] > 0
    second = history.autoscan("session-1", db=store, wait=True)
    assert second["ok"] is False and second["reason"] == "skipped", second


def test_a_different_session_within_the_interval_does_not_rescan(store, monkeypatch):
    assert history.autoscan("session-1", db=store, wait=True)["ok"]
    other = history.autoscan("session-2", db=store, wait=True)
    assert other["ok"] is False, other


def test_the_message_cap_is_respected(store):
    result = history.autoscan("session-1", messages=5, db=store, wait=True)
    assert result["scanned"] == 5, result


def test_a_spent_budget_stops_early_and_leaves_the_cursor_honest(store):
    result = history.autoscan("session-1", messages=20, budget_s=0.0001, db=store, wait=True)
    assert result["ok"]
    assert result["scanned"] < 20, result
    # the cursor must be the last message actually read, never the one it did not reach
    assert result["cursor"] <= 20
    again = history.scan_sessions(days=14, batch=100, db=store)
    assert again["scanned"] == 20 - result["scanned"], (result, again)


def test_it_returns_before_the_scan_finishes(store):
    started = time.time()
    history.autoscan("session-1", db=store, wait=False)
    elapsed = time.time() - started
    # nothing but a lock, a flag and a thread start may happen on the turn's path; 150 ms is a
    # generous ceiling that still fails if any database work moved back onto it
    assert elapsed < 0.15, elapsed
    deadline = time.time() + 10
    while history._SCAN_LOCK["running"] and time.time() < deadline:
        time.sleep(0.02)


def test_two_calls_at_once_start_one_scan(store):
    history.autoscan("session-1", db=store, wait=False)
    second = history.autoscan("session-2", db=store, wait=False)
    assert second["ok"] is False, second
    deadline = time.time() + 10
    while history._SCAN_LOCK["running"] and time.time() < deadline:
        time.sleep(0.02)


def test_nothing_new_is_silent(store, monkeypatch):
    history.autoscan("session-1", db=store, wait=True)
    lines = []
    monkeypatch.setattr(history, "_set_cursor", lambda name, value: None)
    monkeypatch.setattr(history, "_recently_scanned", lambda session: False)
    monkeypatch.setattr("core.engine.record", lambda *a, **k: lines.append(a))
    result = history.autoscan("session-9", db=store, wait=True)
    assert result["ok"] and result["stored"] == 0
    assert lines == []
    assert [e for e in history.last_events(5, "scan") if e["text"].endswith("0 past sessions")] == []


def test_a_scan_leaves_one_line_in_the_ledger(store):
    history.autoscan("session-1", db=store, wait=True)
    events = history.last_events(3, "scan")
    assert events and "concept sightings" in events[0]["text"], events


def test_a_missing_store_is_a_named_failure_not_an_exception(tmp_path, monkeypatch):
    from core import settings
    settings.override(session_scan=True)
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(history, "_SCAN_LOCK", {"running": False})
    result = history.autoscan("session-1", db=tmp_path / "absent.db", wait=True)
    assert result["ok"] is False
    assert "session store" in result.get("reason", "") or result.get("reason") == "failed"


def test_the_thread_never_leaves_the_lock_set(store):
    history.autoscan("session-1", db=store, wait=False)
    deadline = time.time() + 10
    while history._SCAN_LOCK["running"] and time.time() < deadline:
        time.sleep(0.02)
    assert history._SCAN_LOCK["running"] is False


def test_the_setting_is_the_kill_switch(tmp_path):
    from core import settings
    settings.override(session_scan=False)
    assert history.autoscan("session-1", db=tmp_path / "x.db", wait=True)["reason"] == "disabled"
