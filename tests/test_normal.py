"""A state is only meaningful against normal, so normal is measured too."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import normal, recommend  # noqa: E402


def _home(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    normal.clear()


def test_nothing_is_claimed_from_a_few_turns(monkeypatch, tmp_path):
    _home(monkeypatch, tmp_path)
    for _ in range(3):
        normal.observe_turn(4, 1)
    s = normal.stats()
    assert s["measured"] is False
    assert "tools_per_turn" not in s
    assert normal.long_stretch_threshold()["source"] == "fixed"
    assert normal.long_stretch_threshold()["minutes"] == 90


def test_a_measured_baseline_reports_its_shape(monkeypatch, tmp_path):
    _home(monkeypatch, tmp_path)
    for i in range(30):
        normal.observe_turn(6 if i % 2 else 4, 0)
    s = normal.stats()
    assert s["measured"] is True and s["turns"] == 30
    assert s["tools_per_turn"] == 5.0
    assert s["fail_rate"] == 0.0


def test_the_threshold_follows_the_measured_stretch(monkeypatch, tmp_path):
    _home(monkeypatch, tmp_path)
    for minutes in (20, 30, 40, 50, 50, 60, 70, 80):
        normal.observe_stretch(minutes)
    limit = normal.long_stretch_threshold()
    assert limit["source"] == "measured"
    assert 60 <= limit["minutes"] <= 180


def test_the_floor_stops_short_sessions_from_causing_nagging(monkeypatch, tmp_path):
    _home(monkeypatch, tmp_path)
    for minutes in (2, 3, 4, 5, 6, 7):
        normal.observe_stretch(minutes)
    assert normal.long_stretch_threshold()["minutes"] == 60


def test_the_cap_stops_one_long_day_from_silencing_it_for_a_week(monkeypatch, tmp_path):
    _home(monkeypatch, tmp_path)
    for minutes in (300, 400, 500, 600, 700, 800):
        normal.observe_stretch(minutes)
    assert normal.long_stretch_threshold()["minutes"] == 180


def test_the_line_says_which_threshold_it_used(monkeypatch, tmp_path):
    _home(monkeypatch, tmp_path)
    got = recommend._long_stretch(200, 30)
    assert got and "no baseline yet" in got, got
    for minutes in (30, 40, 50, 55, 60, 65, 70, 75):
        normal.observe_stretch(minutes)
    got = recommend._long_stretch(200, 30)
    assert got and "your usual" in got, got


def test_stretches_are_not_recorded_for_a_zero_length_gap(monkeypatch, tmp_path):
    _home(monkeypatch, tmp_path)
    normal.observe_stretch(0)
    normal.observe_stretch(-5)
    assert normal.stats()["stretches"] == 0


def test_a_state_turn_does_not_enter_the_baseline(monkeypatch, tmp_path):
    """The baseline must not be contaminated by the condition it measures against."""
    from core import engine
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    normal.clear()
    engine.clear()
    engine.enter("walk", 5)
    before = normal.stats()["turns"]
    engine.note_turn()
    engine.note_turn()
    assert normal.stats()["turns"] == before, "a turn inside a state entered the baseline"
    engine.stop("")
    engine.note_turn()
    assert normal.stats()["turns"] == before + 1


def test_entering_after_a_gap_records_the_stretch(monkeypatch):
    """The measurement has to happen on the path a person actually takes.

    Every existing test called observe_stretch() directly. In the real entry the gap was computed
    from `breaks[-1]` *after* appending the new break, so it was always 0.0, the floor dropped it,
    and the footer said "no baseline yet" after eighteen states. This goes through enter().
    """
    import time

    from core import engine, normal

    data = engine._load()
    three_hours_ago = time.time() - 3 * 3600
    data["work"]["started_at"] = three_hours_ago
    data["breaks"] = [three_hours_ago]
    data["entries"] = []
    data["active"] = None
    data["baseline"] = {}
    engine._save(data)

    before = normal.stats().get("stretches") or 0
    engine.enter("daydream")
    after = normal.stats().get("stretches") or 0
    assert after == before + 1, (before, after)
    recorded = normal._load().get("stretches") or []
    assert max(recorded) > 60, f"a three-hour gap was recorded as {max(recorded)} minutes"
    engine.stop(reason="returned")
