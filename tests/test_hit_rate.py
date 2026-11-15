"""The hit-rate report reads only persisted keep/trash verdicts."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import history  # noqa: E402


TOOL = ROOT / "tools" / "hit_rate.py"


def _ledger_with_verdicts(home: Path) -> None:
    """Make verdict rows in an isolated plugin ledger.

    A verdict is a `served` row whose move is `keep` or `trash` — the schema the
    plugin actually has — so the fixture writes those rather than a table of its
    own invention.
    """
    conn = history._connect()
    assert conn is not None
    try:
        now = time.time()
        rows = [("first", "keep", now - 30), ("second", "keep", now - 20),
                ("third", "trash", now - 10), ("expired", "trash", now - 8 * 86400)]
        for label, move, at in rows:
            cur = conn.execute(
                "INSERT INTO concepts(kind, key, label, first_seen, last_seen, times) "
                "VALUES(?,?,?,?,?,1)", ("term", label, label, at, at))
            conn.execute(
                "INSERT INTO served(concept_id, move, session, at) VALUES(?,?,?,?)",
                (cur.lastrowid, move, "report-test", at))
        conn.commit()
    finally:
        conn.close()


def _run(home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "ANTEMUSE_STATES_HOME": str(home)}
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_hit_rate_counts_persisted_keep_and_trash_verdicts(tmp_path, monkeypatch):
    home = tmp_path / "antemuse-home"
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(home))
    _ledger_with_verdicts(home)

    result = _run(home, "--since", "7")

    assert result.returncode == 0, result.stderr
    assert "2 kept" in result.stdout
    assert "1 trashed" in result.stdout
    assert "66.7%" in result.stdout


def test_hit_rate_says_when_no_verdicts_exist(tmp_path):
    home = tmp_path / "antemuse-home"
    home.mkdir(exist_ok=True)

    result = _run(home)

    assert result.returncode == 0, result.stderr
    assert "no verdicts recorded yet" in result.stdout.lower()
    assert "0%" not in result.stdout
    assert "nan" not in result.stdout.lower()
    assert not (home / "concepts.db").exists(), "a read-only report created a ledger"


def test_hit_rate_json_has_counts_rate_and_window(tmp_path, monkeypatch):
    home = tmp_path / "antemuse-home"
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(home))
    _ledger_with_verdicts(home)

    result = _run(home, "--since", "7", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"keep": 2, "trash": 1, "rate": 2 / 3, "since_days": 7}
