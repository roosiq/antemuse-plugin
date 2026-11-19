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

    assert states.STATES["dream"]["dose"] == {"unit": "links", "n": 2}
    assert "can't start" not in engine.enter("dream", session="dream-owner")
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
    assert "2 of 2 links" in text
    assert "what linked up" in closing


def test_dream_refuses_only_when_the_whole_day_is_empty(tmp_path, monkeypatch):
    """Too few commits is no longer a refusal on its own — the day has other records."""
    root = _repo(tmp_path)
    monkeypatch.chdir(root)
    monkeypatch.setattr(sources, "_git_subjects",
                        lambda _root, _since="24 hours ago": ["only one subject", "another subject"])
    monkeypatch.setattr(sources, "_day_threads", lambda session=None: [])

    out = engine.enter("dream", session="dry-dream")

    assert "can't start dream" in out and "nothing from today yet" in out
    assert "commit" not in out.lower()

    # The same thin repo, but the chat has a day of its own: dream starts.
    monkeypatch.setattr(sources, "_day_threads",
                        lambda session=None: [("today", "the pricing page"), ("today", "the signup flow")])
    started = engine.enter("dream", session="thin-repo-with-a-day")
    assert "can't start" not in started, started
