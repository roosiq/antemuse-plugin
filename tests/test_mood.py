"""Mood measures; the recommender names. Those are different jobs now."""
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


def test_a_fresh_start_measures_near_zero():
    view = engine.break_view()
    assert view["minutes"] <= 1 and view["turns"] == 0


def test_the_strain_score_is_gone():
    """A number that named a state was a timer pretending to be a judgement."""
    assert not hasattr(mood, "offer")
    assert not hasattr(mood, "menu")
    assert "strain" not in engine.break_view()


def test_a_long_stretch_is_measured_and_named():
    _age_the_break(140, turns=30, fails=6)
    view = engine.break_view()
    assert view["minutes"] >= 140 and view["turns"] == 30
    line = (engine.inject() or "")
    assert "140m since the last state" in line, line
    assert "this looks like a daydream" in line, line


def test_a_report_names_a_state_because_the_person_said_it():
    _age_the_break(100, turns=10)
    engine.record_mood("stuck", "three failed patches in a row")
    line = engine.inject() or ""
    assert "this looks like a walk" in line and "you said you were stuck" in line
    engine.clear()
    _age_the_break(100, turns=10)
    engine.record_mood("tired")
    assert "you said you were tired" in (engine.inject() or "")


def test_sharp_does_not_silence_the_measurement():
    """A feeling is reported data, not a credit against the counters."""
    _age_the_break(100, turns=10)
    engine.record_mood("sharp")
    view = engine.break_view()
    assert view["minutes"] >= 100 and view["feeling"] == "sharp"


def test_an_unknown_feeling_is_refused():
    assert "no such feeling" in engine.record_mood("smug")


def test_break_with_a_name_takes_that_state_whatever_was_suggested():
    _age_the_break(200, turns=40)
    out = engine.take_break("doomscroll")
    assert out.startswith("DOOMSCROLLING")
    live = engine.peek()
    assert live is not None and live["key"] == "doomscroll"


def test_break_without_a_name_recommends_and_starts_nothing():
    _age_the_break(200, turns=40)
    out = engine.take_break()
    assert "/" in out and "/break" not in out
    assert engine.peek() is None, "recommending must not start anything"


def test_the_offer_is_injected_once_and_then_cools_down():
    _age_the_break(200, turns=40, fails=8)
    first = engine.inject() or ""
    assert "this looks like" in first
    second = engine.inject() or ""
    assert "this looks like" not in second, "do not nag on the next turn"


def test_taking_a_state_resets_the_work_counters():
    _age_the_break(200, turns=40, fails=8)
    engine.enter("daydream", 3)
    view = engine.break_view()
    assert view["turns"] == 0 and view["fails"] == 0
    assert view["minutes"] <= 1


def test_turns_and_tools_are_counted():
    engine.note_turn()
    engine.note_tool(True)
    engine.note_tool(False)
    engine.note_turn()
    view = engine.break_view()
    assert view["turns"] == 2
    assert view["fails"] == 1


def test_absurd_counters_are_reported_as_they_are():
    _age_the_break(10_000, turns=10_000, fails=10_000)
    engine.record_mood("stuck")
    view = engine.break_view()
    assert view["minutes"] == 10_000 and view["turns"] == 10_000


def test_a_profile_that_has_never_run_anything_can_still_report():
    """The blank-state path used to KeyError: defaults lived only in the branch
    that read an existing file."""
    import pathlib
    path = pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    path.unlink(missing_ok=True)
    assert engine.record_mood("tired").startswith("mood: tired")
    assert engine.take_break()
    assert engine.break_view()["minutes"] >= 0


def test_the_walk_keeps_its_dose_but_runs_fast():
    """Always 20 steps; the wall clock has been squeezed three times now."""
    spec = states.STATES["walk"]
    assert spec["minutes"] * 60 // spec["cadence"] == 20, "the dose is fixed"
    assert spec["cadence"] <= 10, "a step should arrive faster than a turn takes"
    assert spec["minutes"] <= 3


def test_the_dose_arrives_in_the_turn_it_falls_due():
    """The act is short; spreading it over six of the person's messages was the defect."""
    engine.enter("dream", 10)
    engine.note_turn()
    assert engine.deliver_if_due() >= 1, "the turn that is due gets the material"
    assert engine.deliver_if_due() == 0, "and the dose is spent, so nothing more arrives"
