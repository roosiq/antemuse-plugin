"""Acceptance evidence for dream's local-git material."""
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
    root = tmp_path / "dream-repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    for index, subject in enumerate(("shape migration boundary", "test migration boundary", "document migration boundary")):
        (root / f"note-{index}.txt").write_text(f"PRIVATE TRANSCRIPT {index}")
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", subject], check=True)
    return root


def test_dream_recombines_local_commit_subjects_not_transcripts(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    monkeypatch.chdir(root)

    assert states.STATES["dream"]["dose"] == {"unit": "recombinations", "n": 2}
    assert "cannot enter" not in engine.enter("dream", session="dream-owner")
    blocks = []
    for _ in range(6):
        engine.note_turn("dream-owner")
        blocks.append(engine.inject("dream-owner") or "")
        if engine.peek() is None:
            break
    text = "\n".join(blocks)
    closing = engine.stop("dream-owner")

    assert "shape migration boundary" in text and "test migration boundary" in text
    assert "PRIVATE TRANSCRIPT" not in text
    assert "Tools are open in this state" in text, "tools are open unless the entry asks"
    engine.stop()
    engine.enter("dream", block=True)
    text = engine.inject() or ""
    assert "Tools are closed in this state; /return ends it." in text
    assert "2 of 2 recombinations" in text
    assert "connection you found" in closing


def test_dream_fails_at_entry_when_local_git_has_too_few_subjects(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    monkeypatch.chdir(root)
    monkeypatch.setattr(sources, "_git_subjects", lambda _root: ["only one subject", "another subject"])

    out = engine.enter("dream", session="dry-dream")

    assert "cannot enter dream" in out and "empty" in out
