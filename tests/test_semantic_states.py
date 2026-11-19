"""Walk endings use the state unit and preserve the account semantics."""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="semantic-states-")

from core import engine, sources, states  # noqa: E402


def setup_function(_):
    engine.clear()


def _state_file():
    import pathlib
    return pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"


def _provider(*lines):
    queue = list(lines)

    def call(steps=1):
        return [queue.pop(0)] if queue else []

    return call


def test_every_state_declares_a_dose():
    assert set(states.STATES) == {"walk", "daydream", "doomscroll", "dream", "unstuck"}
    want = {
        "walk": {"unit": "hops", "n": 6},
        "daydream": {"unit": "pairs", "n": 2},
        "doomscroll": {"unit": "items", "n": 3},
        "dream": {"unit": "links", "n": 2},
        "unstuck": {"unit": "moves", "n": 1},
    }
    for key, dose in want.items():
        assert states.STATES[key]["dose"] == dose, key


def test_an_early_completion_is_a_completion_not_an_expiry():
    engine.enter("walk")
    out = engine.stop(engine.current_session(), reason="complete")
    assert "ended" in out.lower(), out   # one shape: every ending says "ended"
    report = [r for r in json.loads(_state_file().read_text())["journal"] if r.get("event") == "report"]
    assert report[-1]["reason"] == "complete"


def test_a_dry_ending_reports_how_much_of_the_dose_was_delivered():
    engine.enter("walk")
    data = json.loads(_state_file().read_text())
    data["active"]["served"] = 1
    _state_file().write_text(json.dumps(data))
    engine.note_turn()
    engine.note_turn()
    report = [r for r in json.loads(_state_file().read_text())["journal"] if r.get("event") == "report"]
    assert report[-1]["reason"] == "dry"
    assert "1 of 6 hops" in report[-1]["text"]


def test_the_first_unit_lands_as_soon_as_the_state_exists(monkeypatch):
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = _provider("a → b")
    try:
        engine.enter("walk", session="pace", platform="discord")
        assert engine.deliver_if_due() == 1
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_turn_buys_no_extra_units(monkeypatch):
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = _provider("a → b", "b → c")
    try:
        engine.enter("walk", session="pace", platform="discord")
        assert engine.deliver_if_due() == 1
        served = engine.peek()["served"]
        engine.note_turn("pace")
        assert engine.peek()["served"] == served
        assert engine.deliver_if_due() == 1
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_state_command_answers_with_a_waiting_line_not_the_palette():
    card = states.palette()
    assert "AGENT STATE" in card
    line = states.waiting("walk")
    assert line and "\n" not in line and line != "walk"
    assert line not in card


def test_the_walk_mask_matches_its_move():
    assert "walk" in states.waiting("walk").lower()


def test_every_ending_speaks_in_the_state_that_ended():
    text = states.after("walk")
    assert len(text) > 40
    assert "walk" in text.lower()
    # Each state closes in its own words: five states, five instructions, no shared template.
    closings = {k: states.after(k) for k in states.STATES}
    assert len(set(closings.values())) == len(states.STATES), closings
    assert all(len(v) > 40 for v in closings.values()), closings


def test_the_pane_counts_the_dose_in_the_states_own_unit():
    from dashboard import projection

    engine.enter("walk", session="unit-walk", platform="discord")
    line = engine.status_line()
    assert "6 hops" in line
    active = projection.project(engine.watch_state())["active"]
    assert active["unit"] == "hops"
    assert active["dose_left"] == 6


def test_residue_cap_holds_when_endings_arrive_between_turns():
    for _ in range(8):
        engine.enter("walk", session="cap")
        engine.stop(reason="cap")
    assert len(engine._load()["residue"]) <= 3
    assert len(engine.watch_state()["residue"]) <= 3


def test_the_account_is_posted_when_the_dose_lands(monkeypatch):
    posted = []
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = _provider(*[f"hop {n}" for n in range(6)])
    monkeypatch.setattr(engine, "_NOTIFY", lambda text: posted.append(text) or True)
    try:
        engine.enter("walk", session="say-now", platform="discord")
        for _ in range(6):
            engine.note_turn("say-now")
            engine.inject(session="say-now")
        assert engine.peek() is None
        assert posted
        assert "6 of 6 hops" in posted[-1]
        assert engine.unreported("say-now") is None
    finally:
        sources.PROVIDERS["walk"] = original
        engine._NOTIFY = None
