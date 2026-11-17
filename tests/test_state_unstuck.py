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
    monkeypatch.setattr(sources, "_graph_edge", lambda _root: "design → blueprint (hypernym)")

    assert states.STATES["unstuck"]["dose"] == {"unit": "directions", "n": 1}
    assert "cannot enter" not in engine.enter("unstuck", session="unstuck-owner")
    engine.note_turn("unstuck-owner")
    text = engine.inject("unstuck-owner") or ""
    closing = engine.stop("unstuck-owner")

    assert "continue the last change: add design boundary" in text
    assert "graph edge: design → blueprint (hypernym)" in text
    assert "Tools are open in this state" in text, "tools are open unless the entry asks"
    engine.stop()
    engine.enter("unstuck", block=True)
    assert "Only these tools: read_file, search_files. /return ends it." in (engine.inject() or "")
    assert "1 of 1 direction" in text
    assert "recommendation stands" in closing and "first move" in closing


def test_unstuck_fails_at_entry_without_a_project(monkeypatch):
    monkeypatch.setattr(sources.storage, "project_root", lambda: None)

    out = engine.enter("unstuck", session="no-project")

    assert "cannot enter unstuck" in out and "unavailable" in out
