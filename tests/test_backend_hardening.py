"""Regression coverage for persistence, ownership, and cockpit input bounds."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core import engine, history


def _client() -> TestClient:
    import dashboard.plugin_api as api

    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/antemuse")
    return TestClient(app)


def test_notice_prunes_old_rows_from_the_database(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    history.notice("oldconcept", session="old")
    conn = sqlite3.connect(history.db_path())
    conn.execute("UPDATE served SET at=?", (time.time() - (history.RETENTION_DAYS + 1) * 86400,))
    conn.commit()
    conn.close()

    history.notice("newconcept", session="new")

    conn = sqlite3.connect(history.db_path())
    try:
        assert conn.execute("SELECT COUNT(*) FROM served WHERE session='old'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM concepts WHERE label='oldconcept'").fetchone()[0] == 0
    finally:
        conn.close()


def test_concurrent_process_saves_leave_valid_state_file(tmp_path):
    home = tmp_path / "shared"
    code = """
import os, sys
sys.path.insert(0, sys.argv[1])
from core import engine
engine.remember_platform(sys.argv[2], sys.argv[2])
"""
    env = {**os.environ, "ANTEMUSE_STATES_HOME": str(home)}
    first = subprocess.Popen([sys.executable, "-c", code, str(ROOT), "one"], env=env)
    second = subprocess.Popen([sys.executable, "-c", code, str(ROOT), "two"], env=env)
    assert first.wait(timeout=20) == 0
    assert second.wait(timeout=20) == 0
    data = json.loads((home / "state.json").read_text())
    assert data["session_id"] in {"one", "two"}
    assert (home / "state.json.last-good").exists()


def test_truncated_state_file_recovers_last_known_good_state():
    engine.enter("walk", session="durable")
    path = Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    path.write_text('{"active":')

    assert engine.watch_state()["active"]["key"] == "walk"
    assert json.loads(path.read_text())["active"]["key"] == "walk"


def test_wrong_shaped_state_file_does_not_break_state_route():
    path = Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    path.write_text('{"active":"not-a-state"}')

    response = _client().get("/api/plugins/antemuse/state")
    assert response.status_code == 200
    assert response.json()["active"] is None
    assert list(path.parent.glob("state.json.invalid-*"))


def test_enter_supersedes_a_running_state_with_account_and_move():
    # The owner replacing its own state. A foreign entry is refused instead: `stop` already
    # refuses a bystander's /return, and superseding was the way around that.
    engine.enter("walk", session="owner")
    answer = engine.enter("walk", session="owner")

    assert "left walk" in answer and "account kept" in answer
    report = [r for r in engine._load()["residue"] if r.get("reason") == "superseded"]
    assert len(report) == 1 and report[0]["state"] == "walk"
    conn = history._connect()
    assert conn is not None
    try:
        assert conn.execute("SELECT ending FROM moves ORDER BY id DESC LIMIT 1").fetchone()[0] == "superseded"
    finally:
        conn.close()


def test_foreign_turns_do_not_decay_a_sessions_flight_note():
    engine.note_flight(["harpoon"], session="A")
    engine.tick(session="B")
    engine.tick(session="B")

    note = engine._load()["residue"][0]
    assert note["session"] == "A"
    assert note["turns_left"] == 2

    engine.tick(session="A")
    assert engine._load()["residue"][0]["turns_left"] == 1
    engine.tick(session="A")
    assert engine._load()["residue"] == []


def test_flight_body_size_is_rejected_before_ledger_writes(monkeypatch):
    import types
    import dashboard.plugin_api as api

    calls = []
    monkeypatch.setattr(engine.history, "notice", lambda label, **kwargs: calls.append(label))
    monkeypatch.setattr(api, "plugin", lambda: types.SimpleNamespace(
        core=types.SimpleNamespace(engine=engine)))

    response = _client().post("/api/plugins/antemuse/flight",
                              json={"trail": ["x" * 64 for _ in range(1000)]})
    assert response.status_code == 413
    assert calls == []


def test_flight_bounds_writes_and_discards_verdicts_outside_trail(monkeypatch):
    import types
    import dashboard.plugin_api as api

    calls = []
    monkeypatch.setattr(engine.history, "notice", lambda label, **kwargs: calls.append(label))
    monkeypatch.setattr(api, "plugin", lambda: types.SimpleNamespace(
        core=types.SimpleNamespace(engine=engine)))
    body = _client().post(
        "/api/plugins/antemuse/flight",
        json={"trail": [f"label-{i}" for i in range(1000)],
              "kept": ["not-in-trail"], "dropped": ["also-not-in-trail"]},
    ).json()

    assert body["ok"] is True
    assert body["concepts"] == 64
    assert body["reason"] == "trail trimmed to 64 labels"
    assert len(calls) == 64
    assert engine.flight_last()["kept"] == []
    assert engine.flight_last()["dropped"] == []



def test_an_empty_active_dict_is_a_state_that_ended_not_a_broken_file():
    """`active: {}` is how a walk got erased nine times in one second.

    The writer saved `data["active"] or {}`; the validator demanded a dict with a string key,
    so `{}` failed, `_load` quarantined the entire document (sixty journal entries and a moving
    walk with it), and the next hop wrote it again. An empty dict means "no state", and it must
    not cost the rest of the file.
    """
    engine.enter("walk", session="empty-active")
    engine.note_turn("empty-active")
    engine.inject("empty-active")
    path = Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    stored = json.loads(path.read_text())
    stored["active"] = {}
    stored["residue"] = [{"kind": "report", "state": "walk", "text": "walk · 2 of 6 hops"}]
    path.write_text(json.dumps(stored))

    loaded = engine._load()

    assert loaded["active"] is None, loaded["active"]
    assert loaded["journal"], "the journal must survive an empty active"
    assert loaded["residue"], "the ending account must survive an empty active"
    assert not list(path.parent.glob("state.json.invalid-*")), "{} is not corruption"
    assert json.loads(path.read_text())["active"] is None, "it should be rewritten in shape"


def test_one_bad_field_does_not_cost_the_document():
    """A wrong-shaped `active` is quarantined for forensics, but the journal beside it is kept."""
    engine.enter("walk", session="salvage")
    path = Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    stored = json.loads(path.read_text())
    stored["active"] = "not-a-state"
    path.write_text(json.dumps(stored))
    before = len(stored.get("journal") or [])

    loaded = engine._load()

    assert loaded["active"] is None
    assert list(path.parent.glob("state.json.invalid-*")), "the bytes are still quarantined"
    assert len(loaded["journal"]) == before, "the readable part of the document survives"
