"""Mood measures; the recommender names. Those are different jobs now."""
from __future__ import annotations

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="mood-test-")

import pytest  # noqa: E402

from core import engine, mood, settings, states  # noqa: E402


def setup_function(_):
    engine.clear()

class _Host:
    """The host surface settings reads; display is on, because these tests are about speech."""

    def __init__(self, values=None):
        self.values = values or {}

    def get_config(self, key, default=None):
        return self.values.get(key, default)


@pytest.fixture(autouse=True)
def _recommendations_visible():
    settings.bind(_Host({"show_recommendations": True}))
    yield



def _age_the_break(minutes: float, turns: int = 0, fails: int = 0) -> None:
    """Put the last break in the past and load the counters."""
    import pathlib
    import json
    path = pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    data = json.loads(path.read_text())
    data["breaks"] = [time.time() - minutes * 60]
    data["work"] = {"turns": turns, "tools": turns * 2, "fails": fails,
                    "started_at": time.time() - minutes * 60}
    data["since_offer"] = 60      # past the cooling window, so a nudge may speak
    path.write_text(json.dumps(data))


def test_a_fresh_start_measures_near_zero():
    view = engine.break_view()
    assert view["turns"] == 0
    assert "minutes" not in view, "a stretch is counted in turns, not minutes"


def test_the_strain_score_is_gone():
    """A number that named a state was a timer pretending to be a judgement."""
    assert not hasattr(mood, "offer")
    assert not hasattr(mood, "menu")
    assert "strain" not in engine.break_view()


def test_a_long_stretch_is_measured_and_named():
    _age_the_break(140, turns=30, fails=6)
    view = engine.break_view()
    assert view["turns"] == 30
    line = (engine.inject() or "")
    assert "30 turns since the last state" in line, line
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
    assert view["turns"] == 10 and view["feeling"] == "sharp"


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
    engine.enter("daydream")
    view = engine.break_view()
    assert view["turns"] == 0 and view["fails"] == 0


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
    assert view["turns"] == 10_000


def test_a_profile_that_has_never_run_anything_can_still_report():
    """The blank-state path used to KeyError: defaults lived only in the branch
    that read an existing file."""
    import pathlib
    path = pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    path.unlink(missing_ok=True)
    assert engine.record_mood("tired").startswith("mood: tired")
    assert engine.take_break()
    assert engine.break_view()["turns"] >= 0


def test_a_state_has_a_dose_and_no_clock():
    """There is no ceiling and no cadence: the dose is the whole of a state's length."""
    for key, spec in states.STATES.items():
        assert "minutes" not in spec, f"{key} still carries a time ceiling"
        assert "cadence" not in spec, f"{key} still carries a second-based cadence"
        assert int((spec.get("dose") or {}).get("n") or 0) > 0, f"{key} has no dose"


def _age_state(seconds: float) -> None:
    """Hand the running state N seconds, so a test does not have to sleep for them."""
    data = engine._load()
    data["active"]["entered_at"] = float(data["active"]["entered_at"]) - seconds
    engine._save(data)


def test_the_dose_arrives_at_the_dose_and_stops():
    """The act is short; spreading it over six of the person's messages was the defect.

    Delivery is paced by the clock now — one unit a second — so what this pins is the
    ceiling on the dose: once the state has served what it promised, nothing more arrives,
    however much time passes after that.
    """
    engine.enter("dream", 10)
    engine.note_turn()
    assert engine.deliver_if_due() >= 1, "the state that is due gets its material"
    _age_state(120)                        # everything the dose could still owe
    engine.deliver_if_due()
    assert engine.deliver_if_due() == 0, "a spent dose keeps arriving"
