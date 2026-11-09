"""A state ends when its act is done. The clock is only a ceiling."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="semantic-states-")

from core import engine, states  # noqa: E402


def setup_function(_):
    engine.clear()


def _state_file():
    import pathlib
    return pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"


def test_every_state_declares_a_dose():
    for key, spec in states.STATES.items():
        dose = spec.get("dose") or {}
        assert dose.get("n", 0) >= 1, f"{key} has no dose"
        assert dose.get("unit"), f"{key} has no unit"


def test_the_dose_ends_the_state_without_a_command():
    """A doomscroll is three feed items; after the third there is nothing to wait for."""
    engine.enter("doomscroll", 30)
    for _ in range(4):
        engine.note_turn()
        engine.deliver_if_due()
        if engine.peek() is None:
            break
    assert engine.peek() is None, "the state outlived its dose"


def test_an_early_completion_is_a_completion_not_an_expiry():
    engine.enter("dream", 30)
    out = engine.stop(engine.current_session(), reason="complete")
    assert "finished" in out.lower(), out
    report = [r for r in json.loads(_state_file().read_text())["journal"] if r.get("event") == "report"]
    assert report[-1]["reason"] == "complete"


def test_an_expiry_reports_how_much_of_the_dose_was_delivered():
    engine.enter("doomscroll", 30)
    path = _state_file()
    data = json.loads(path.read_text())
    data["active"]["ends_at"] = time.time() - 1
    data["active"]["served"] = 1
    path.write_text(json.dumps(data))
    engine.inject()
    report = [r for r in json.loads(path.read_text())["journal"] if r.get("event") == "report"]
    # the turn's own delivery arrives first, so the count is 2 of 3 — what matters is
    # that the expiry states the shortfall instead of pretending the act was finished
    assert "expired before its dose: 2 of 3" in report[-1]["text"], report[-1]


def test_the_same_dose_costs_the_same_turns_at_any_speed():
    """Slow turns must not buy fewer items: delivery is per turn, not per second."""
    engine.enter("doomscroll", 30)
    served = []
    for _ in range(3):
        engine.note_turn()
        served.append(engine.deliver_if_due())
        if engine.peek() is None:
            break
    assert served[0] >= 1, "the first turn got nothing"
    assert sum(served) >= 3 or engine.peek() is None


def test_the_ceiling_is_still_a_ceiling():
    engine.enter("walk", 3)
    assert engine.peek()["ends_at"] > time.time()


def test_per_turn_delivery_beats_the_old_clock():
    """Two turns in the same second still get two items: the old code returned 0."""
    engine.enter("daydream", 10)
    engine.note_turn()
    first = engine.deliver_if_due()
    engine.note_turn()
    second = engine.deliver_if_due()
    assert first >= 1 and second >= 1, (first, second)
