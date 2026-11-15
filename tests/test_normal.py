"""Normal work is measured separately from the surviving walk state."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core import normal  # noqa: E402


def _home(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    normal.clear()


def test_few_turns_do_not_claim_a_baseline(monkeypatch, tmp_path):
    _home(monkeypatch, tmp_path)
    for _ in range(3):
        normal.observe_turn(4, 1)
    assert normal.stats()["measured"] is False
    assert normal.long_stretch_threshold()["turns"] == 30


def test_measured_baseline_reports_its_shape(monkeypatch, tmp_path):
    _home(monkeypatch, tmp_path)
    for i in range(30):
        normal.observe_turn(6 if i % 2 else 4, 0)
    assert normal.stats()["tools_per_turn"] == 5.0


def test_stretch_threshold_is_bounded(monkeypatch, tmp_path):
    _home(monkeypatch, tmp_path)
    for turns in (5, 10, 15, 20, 20, 25, 30, 40):
        normal.observe_stretch(turns)
    assert 15 <= normal.long_stretch_threshold()["turns"] <= 80


def test_entering_walk_records_the_completed_work_stretch(monkeypatch, tmp_path):
    from core import engine

    _home(monkeypatch, tmp_path)
    engine.clear()
    data = engine._load()
    data["work"]["turns"] = 44
    engine._save(data)
    before = normal.stats()["stretches"]
    engine.enter("walk")
    assert normal.stats()["stretches"] == before + 1
    engine.stop()
