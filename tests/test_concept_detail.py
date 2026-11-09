"""What a concept connects to, with the evidence — the inspect tool and the ledger's detail()."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT))
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))

from core import history  # noqa: E402


def _seed(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    history.notice("gateway", move="session", session="20261108_162120_aaaa",
                   ref="9001", at=1_760_000_000)
    history.notice("plugin", move="session", session="20261108_162120_aaaa",
                   ref="9001", at=1_760_000_000)
    history.notice("gateway", move="session", session="20261107_120000_bbbb",
                   ref="9002", at=1_759_900_000)
    history.notice_artifact("antemuse-plugin", "core/gateway_routes.py", commit="deadbee",
                            at=1_760_000_500)


def test_detail_names_the_sessions_the_messages_and_the_files(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    detail = history.detail("gateway")
    assert detail["ok"], detail
    assert len(detail["sessions"]) == 2
    assert {m["id"] for m in detail["messages"]} == {"9001", "9002"}
    assert detail["files"] == ["antemuse-plugin/core/gateway_routes.py"]
    assert detail["commits"][0]["sha"] == "deadbee"


def test_detail_shows_what_was_said_beside_it_not_just_the_session(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    detail = history.detail("gateway")
    assert [s["label"] for s in detail["siblings"]] == ["plugin"], detail["siblings"]


def test_detail_says_when_it_has_never_seen_the_word(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    detail = history.detail("zzzqx")
    assert detail["ok"] is False
    assert "never seen" in detail["reason"]


def test_the_card_can_be_printed_for_a_person(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "tools/graph_inspect.py"), "gateway"],
                            capture_output=True, text=True, timeout=120,
                            env={**os.environ, "ANTEMUSE_STATES_HOME": str(tmp_path)})
    assert result.returncode == 1            # nothing in this ledger
    assert "not a concept" in result.stdout or "never seen" in result.stdout


def test_the_card_renders_evidence_when_there_is_some(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    result = subprocess.run([sys.executable, str(ROOT / "tools/graph_inspect.py"),
                             "gateway", "--json"],
                            capture_output=True, text=True, timeout=120,
                            env={**os.environ, "ANTEMUSE_STATES_HOME": str(tmp_path)})
    assert result.returncode == 0, result.stderr[-300:]
    payload = json.loads(result.stdout)
    assert payload["concept"]["label"] == "gateway"
    assert payload["messages"][0]["id"] == "9001"


def test_the_top_list_is_ordered_by_how_often_a_concept_was_met(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    result = subprocess.run([sys.executable, str(ROOT / "tools/graph_inspect.py"), "--top", "3"],
                            capture_output=True, text=True, timeout=120,
                            env={**os.environ, "ANTEMUSE_STATES_HOME": str(tmp_path)})
    assert result.returncode == 0, result.stderr[-300:]
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    assert lines[0].endswith("gateway"), lines          # seen twice, plugin once


def test_an_excerpt_is_read_on_demand_and_never_stored(tmp_path, monkeypatch):
    """The transcript stays in Hermes' store; the ledger keeps ids."""
    store = tmp_path / "state.db"
    import sqlite3
    conn = sqlite3.connect(store)
    conn.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, role TEXT, content TEXT)")
    conn.execute("INSERT INTO messages VALUES (9001, 'assistant', 'the gateway routes were stale')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(history, "HERMES_DB", store)
    excerpts = history.message_excerpts(["9001"])
    assert "gateway routes" in excerpts["9001"]
    assert history._query("SELECT COUNT(*) FROM appearances WHERE ref='9001'")[0][0] == 0
