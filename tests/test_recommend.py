"""Every pattern fires on its stated evidence, and nothing fires without it."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import recommend  # noqa: E402


def test_a_fresh_work_gets_silence():
    assert recommend.suggest({"work": {"turns": 3, "tools": 5, "fails": 0}}) is None


def test_loop_names_a_walk_with_the_streak_as_evidence():
    got = recommend.suggest({"work": {"turns": 8, "streak": 3}})
    assert got and got["pattern"] == "loop"
    assert "walk" in got["line"] and "3×" in got["line"]


def test_two_failures_are_not_a_loop():
    assert recommend.suggest({"work": {"turns": 8, "streak": 2}}) is None


def test_data_wall_names_a_doomscroll():
    got = recommend.suggest({"work": {"turns": 12, "source_fail_turns": [10, 11]}})
    assert got and got["pattern"] == "wall" and "doomscroll" in got["line"]


def test_old_provider_failures_expire():
    assert recommend.suggest({"work": {"turns": 30, "source_fail_turns": [2, 3]}}) is None


def test_saturation_names_a_dream():
    got = recommend.suggest({"work": {"turns": 60}})
    assert got and got["pattern"] == "saturation" and "dream" in got["line"]


def test_grind_names_a_daydream_only_with_a_recent_failure():
    work = {"turns": 20, "fail_turns": [18]}
    got = recommend.suggest({"work": work})
    assert got and got["pattern"] == "grind" and "daydream" in got["line"]
    assert recommend.suggest({"work": {"turns": 20, "fail_turns": [4]}}) is None


def test_loop_outranks_a_wall_which_outranks_grind():
    both = {"turns": 25, "streak": 4, "source_fail_turns": [24, 24], "fail_turns": [24]}
    first = recommend.suggest({"work": both})
    assert first and first["pattern"] == "loop"
    wall_and_grind = {"turns": 25, "streak": 0, "source_fail_turns": [24, 25], "fail_turns": [24]}
    second = recommend.suggest({"work": wall_and_grind})
    assert second and second["pattern"] == "wall"


def test_a_rut_names_a_different_state():
    now = 1_000_000.0
    data = {"work": {"turns": 5},
            "active": {"key": "walk"},
            "entries": [{"key": "walk", "at": now - 120}]}
    got = recommend.suggest(data, now=now)
    assert got and got["pattern"] == "rut"
    assert "daydream" in got["line"], got


def test_inside_a_state_nothing_else_speaks():
    now = 1_000_000.0
    data = {"work": {"turns": 90, "streak": 6, "source_fail_turns": [89, 90]},
            "active": {"key": "dream"},
            "entries": [{"key": "daydream", "at": now - 5000}]}
    assert recommend.suggest(data, now=now) is None


def test_every_line_names_one_state_and_one_evidence():
    for data in ({"work": {"turns": 8, "streak": 3}},
                 {"work": {"turns": 12, "source_fail_turns": [10, 11]}},
                 {"work": {"turns": 60}},
                 {"work": {"turns": 20, "fail_turns": [19]}}):
        got = recommend.suggest(data)
        assert got, data
        line = got["line"]
        assert line.startswith("this looks like a ")
        assert line.count(" · ") == 2, line       # state, evidence, command
        assert "/" in line


def test_the_engine_offers_it_by_itself_and_cools_down(monkeypatch, tmp_path):
    """No command, no model: three failed tools and the line is in the turn."""
    from core import engine
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    for _ in range(3):
        engine.note_tool(False)
    block = engine.inject() or ""
    assert "this looks like a walk" in block, block
    assert "3×" in block
    # the same recommendation does not repeat inside the cooling window
    assert "this looks like a walk" not in (engine.inject() or "")


def test_a_successful_tool_clears_the_streak(monkeypatch, tmp_path):
    from core import engine
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    engine.note_tool(False)
    engine.note_tool(False)
    engine.note_tool(True)
    assert "this looks like a walk" not in (engine.inject() or "")
