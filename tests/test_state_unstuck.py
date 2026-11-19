"""Acceptance evidence for the history-plus-graph unstuck state."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import engine, sources, states


def setup_function(_):
    engine.clear()


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "design-repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    (root / "README.md").write_text("design")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "add design boundary"], check=True)
    return root


def test_unstuck_delivers_one_direction_from_history_and_graph(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    monkeypatch.chdir(root)
    monkeypatch.setattr(sources, "_graph_edge", lambda _root=None, _session=None: "design → blueprint (hypernym)")

    assert states.STATES["unstuck"]["dose"] == {"unit": "moves", "n": 1}
    assert "can't start" not in engine.enter("unstuck", session="unstuck-owner")
    engine.note_turn("unstuck-owner")
    text = engine.inject("unstuck-owner") or ""
    closing = engine.stop("unstuck-owner")

    # One thing in the record means there is nothing earlier to return to, and it says so rather
    # than telling the person to continue the change they just finished.
    assert "only one thing here (add design boundary)" in text
    assert "continue the last change" not in text
    assert "map link: design → blueprint (hypernym)" in text
    assert "Tools are open in this state" in text, "tools are open unless the entry asks"
    engine.stop()
    engine.enter("unstuck", block=True)
    assert "Only these tools: read_file, search_files. /return ends it." in (engine.inject() or "")
    assert "1 of 1 move" in text
    assert "suggestion stands" in closing and "first move" in closing


def test_unstuck_works_without_a_project(monkeypatch):
    """No state may require a git repo: a chat outside one still has a day to go on."""
    monkeypatch.setattr(sources.storage, "project_root", lambda: None)
    monkeypatch.setattr(sources, "_graph_edge",
                        lambda _root=None, _session=None: "design → blueprint (hypernym)")
    from core import recall
    recall.remember("the pricing page needs an annual discount line", "person", "no-project")
    recall.remember("the signup flow should explain the yearly discount", "person", "no-project")

    out = engine.enter("unstuck", session="no-project")

    assert "can't start" not in out, out
    line = sources.unstuck_text(1, session="no-project")[0]
    assert "next move" in line and "map link:" in line
    assert "git" not in line.lower() and "commit" not in line.lower()


def test_unstuck_refuses_plainly_when_there_is_nothing_to_go_on(monkeypatch):
    monkeypatch.setattr(sources.storage, "project_root", lambda: None)
    monkeypatch.setattr(sources, "_day_threads", lambda session=None: [])

    out = engine.enter("unstuck", session="empty-chat")

    assert "can't start unstuck" in out and "nothing to go on yet" in out
    assert "git" not in out.lower() and "commit" not in out.lower()


def test_unstuck_steps_away_from_the_change_just_finished(tmp_path, monkeypatch):
    """The bug this state existed to fix: it recommended the newest commit.

    `subjects[0]` is the change the person just made. Rendering it as "continue the last change"
    told someone who is stuck to keep doing the thing that stuck them.
    """
    root = _repo(tmp_path)
    (root / "README.md").write_text("design, again")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "finish design boundary"], check=True)
    monkeypatch.chdir(root)
    monkeypatch.setattr(sources, "_graph_edge", lambda _root=None, _session=None: "design → blueprint (hypernym)")

    line = sources.unstuck_text(1)[0]
    assert "skip another pass at finish design boundary" in line, line
    assert "try add design boundary a different way" in line, line
    assert "continue the last change" not in line, line
