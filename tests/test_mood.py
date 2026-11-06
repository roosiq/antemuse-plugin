"""Mood, strain, and when to step away."""
from __future__ import annotations

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="mood-test-")

from core import engine, mood, states  # noqa: E402


def setup_function(_):
    engine.clear()


def _age_the_break(minutes: float, turns: int = 0, fails: int = 0) -> None:
    """Put the last break in the past and load the counters."""
    import pathlib
    import json
    path = pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    data = json.loads(path.read_text())
    data["breaks"] = [time.time() - minutes * 60]
    data["work"] = {"turns": turns, "tools": turns * 2, "fails": fails,
                    "started_at": time.time() - minutes * 60}
    data["offered_at"] = 0.0
    path.write_text(json.dumps(data))


def test_a_fresh_start_is_not_a_break():
    view = engine.break_view()
    assert view["due"] == "carry on"
    assert view["minutes"] <= 1


def test_two_hours_thirty_turns_and_failures_is_overdue():
    _age_the_break(140, turns=30, fails=6)
    view = engine.break_view()
    assert view["due"] == "break overdue", view
    assert view["suggest"] in states.STATES


def test_a_report_changes_what_is_suggested():
    _age_the_break(100, turns=10)
    engine.record_mood("stuck", "three failed patches in a row")
    assert engine.break_view()["suggest"] == "walk"
    engine.clear()
    engine.record_mood("tired")
    assert engine.break_view()["suggest"] == "daydream"


def test_sharp_pushes_the_break_away():
    _age_the_break(100, turns=10)
    before = engine.break_view()["strain"]
    engine.record_mood("sharp")
    after = engine.break_view()["strain"]
    assert after < before


def test_an_unknown_feeling_is_refused():
    assert "no such feeling" in engine.record_mood("smug")


def test_break_with_a_name_takes_that_state_whatever_was_suggested():
    _age_the_break(200, turns=40)
    out = engine.take_break("doomscroll")
    assert out.startswith("DOOMSCROLLING")
    live = engine.peek()
    assert live is not None and live["key"] == "doomscroll"


def test_break_without_a_name_recommends_and_lists_the_menu():
    _age_the_break(200, turns=40)
    out = engine.take_break()
    assert "break " in out and "/break walk" in out
    assert engine.peek() is None, "recommending must not start anything"


def test_the_offer_is_injected_once_and_then_cools_down():
    _age_the_break(200, turns=40, fails=8)
    first = engine.inject() or ""
    assert "[BREAK" in first
    second = engine.inject() or ""
    assert "[BREAK" not in second, "do not nag on the next turn"


def test_taking_a_state_resets_the_work_counters():
    _age_the_break(200, turns=40, fails=8)
    engine.enter("daydream", 3)
    view = engine.break_view()
    assert view["turns"] == 0 and view["fails"] == 0
    assert view["due"] == "carry on"


def test_turns_and_tools_are_counted():
    engine.note_turn()
    engine.note_tool(True)
    engine.note_tool(False)
    engine.note_turn()
    view = engine.break_view()
    assert view["turns"] == 2
    assert view["fails"] == 1


def test_mood_scores_are_bounded():
    _age_the_break(10_000, turns=10_000, fails=10_000)
    engine.record_mood("stuck")
    assert engine.break_view()["strain"] == 3.0


def test_a_profile_that_has_never_run_anything_can_still_report():
    """The blank-state path used to KeyError: defaults lived only in the branch
    that read an existing file."""
    import pathlib
    path = pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    path.unlink(missing_ok=True)
    assert engine.record_mood("tired").startswith("mood: tired")
    assert "break:" in engine.take_break()
    assert engine.break_view()["due"] in ("carry on", "break due", "break overdue")
