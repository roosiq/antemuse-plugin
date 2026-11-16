"""Leaving a cockpit session is work, so it gets written down.

A flight was the one thing this plugin produced and threw away: outside `/explore`,
`note_pick()` returns `not exploring` and nothing is counted, nothing is written to the
ledger, and nothing is owed to the agent. The cockpit became a tab in 0.11.1, so flying
without entering a state is the ordinary case rather than the corner — and the exit filed
nothing at all.

The chosen shape: a flight is a *note*, not a state. It costs no turns, it does not touch
`active`, and the next turn reads it as residue.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import engine  # noqa: E402


def _client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import dashboard.plugin_api as api

    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/antemuse")
    return TestClient(app)


def test_a_flight_outside_a_state_is_still_filed():
    assert engine._load()["active"] is None
    out = engine.note_flight(["harpoon", "harpoon", "lighthouse"], session="s-flight")
    assert out["ok"] is True
    assert out["concepts"] == 2, "repeats are interest, not new concepts"
    residue = engine._load()["residue"]
    assert any("you flew" in str(r.get("text") or "") for r in residue), residue
    last = engine.flight_last()
    assert last["trail"] == ["harpoon", "lighthouse"], "the trail keeps the order it was flown"


def test_a_flight_does_not_enter_or_spend_a_state():
    engine.note_flight(["timber"], session="s-flight")
    assert engine._load()["active"] is None, "a flight is a note, not a state"


def test_a_flight_with_nothing_touched_files_nothing():
    before = len(engine._load()["residue"])
    out = engine.note_flight([], session="s-flight")
    assert out["concepts"] == 0
    assert len(engine._load()["residue"]) == before
    assert engine.flight_last() is None


def test_the_flight_note_reaches_the_next_turn_and_then_stops():
    engine.note_flight(["harpoon", "lighthouse"], kept=["harpoon"], dropped=["lighthouse"],
                       session="s-flight-turn")
    block = engine.inject(session="s-flight-turn")
    assert block and "you flew the map" in block, block
    assert "kept harpoon" in block and "dropped lighthouse" in block
    # Residue decays per turn (in `tick`, which hangs off the turn hook), so the note is not a
    # permanent claim about now.
    for _ in range(3):
        engine.tick(session="s-flight-turn")
    later = engine.inject(session="s-flight-turn") or ""
    assert "you flew the map" not in later


def test_the_pane_files_a_flight_over_its_own_route():
    client = _client()
    body = client.post("/api/plugins/antemuse/flight",
                       json={"trail": ["harpoon", "lighthouse"], "kept": ["harpoon"],
                             "session": "s-flight-api"}).json()
    assert body["ok"] is True and body["concepts"] == 2
    assert any("you flew" in str(r.get("text") or "") for r in engine._load()["residue"])
    state = client.get("/api/plugins/antemuse/state?session=s-flight-api").json()
    assert state["flight"]["concepts"] == 2, "the pane needs to be able to show what it filed"
    assert state["flight"]["trail"] == ["harpoon", "lighthouse"]


def test_a_flight_route_that_gets_nonsense_does_not_500():
    client = _client()
    body = client.post("/api/plugins/antemuse/flight", json={"trail": "harpoon"}).json()
    assert body["concepts"] == 0
