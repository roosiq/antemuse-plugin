"""Recent turns: the one memory-ish source that is the same under any provider."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_the_ring_is_bounded_and_deduped(monkeypatch, tmp_path):
    from core import recall
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    recall.clear()
    for i in range(recall.CAP + 8):
        recall.remember(f"turn number {i} with enough words to be kept", "person")
    items = recall.recent(limit=100)
    assert len(items) == recall.CAP, len(items)
    assert items[-1].endswith("be kept")
    # the same line twice in a row is one turn, not two
    recall.remember("a repeated sentence that should not duplicate", "person")
    recall.remember("a repeated sentence that should not duplicate", "person")
    assert recall.recent(100).count("a repeated sentence that should not duplicate") == 1


def test_short_noise_is_not_a_turn(monkeypatch, tmp_path):
    from core import recall
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    recall.clear()
    recall.remember("ok", "person")
    recall.remember("", "person")
    assert recall.recent() == []


def test_entries_are_truncated_not_dropped(monkeypatch, tmp_path):
    from core import recall
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    recall.clear()
    recall.remember("x" * 4000, "agent")
    kept = recall.recent()[0]
    assert len(kept) == recall.MAX_CHARS


def test_it_lives_in_the_plugin_data_dir(monkeypatch, tmp_path):
    from core import recall
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    assert recall.path().parent == tmp_path
