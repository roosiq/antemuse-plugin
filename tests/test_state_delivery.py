"""Walk dose delivery: delivered material, ownership, endings, and accounts."""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="delivery-test-")

from core import engine, sources, states  # noqa: E402


def setup_function(_):
    engine.clear()


def provider(*lines):
    queue = list(lines)

    def call(_n):
        return [queue.pop(0)] if queue else []

    return call


def drive(*lines, turns=8, session="delivery"):
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(*lines)
    try:
        engine.enter("walk", session=session)
        blocks = []
        for _ in range(turns):
            engine.note_turn(session)
            engine.tick(session)
            blocks.append(engine.inject(session) or "")
            if engine.peek() is None:
                break
        return blocks
    finally:
        sources.PROVIDERS["walk"] = original


def state_home() -> dict:
    with open(os.path.join(os.environ["ANTEMUSE_STATES_HOME"], "state.json")) as fh:
        return json.load(fh)


def markers(n=6):
    return [f"WALK-MARKER-{i}" for i in range(1, n + 1)]


def test_the_last_unit_reaches_the_turn_that_spends_it():
    lines = markers()
    drive(*lines)
    journal = [e["text"] for e in state_home()["journal"] if e.get("who") == "state"]
    assert journal[:6] == lines
    assert engine.peek() is None


def test_a_state_ends_with_exactly_one_account():
    drive(*markers())
    reports = [r for r in state_home()["residue"] if r.get("kind") == "report"]
    assert len(reports) == 1
    assert reports[0]["state"] == "walk"
    assert reports[0]["reason"] == "complete"


def test_a_dead_source_ends_as_failed_and_claims_no_dose():
    blocks = drive("feed unavailable · nothing to read")
    joined = "\n".join(blocks)
    assert "nothing arrived" in joined
    assert "1 of 6 hops" not in joined
    assert "[WHAT ARRIVED" not in joined
    report = [r for r in state_home()["residue"] if r.get("kind") == "report"][0]
    assert report["reason"] == "failed"
    assert "nothing arrived" in report["text"]


def test_a_source_that_runs_dry_mid_dose_is_not_called_nothing_arrived():
    drive("WALK-MARKER-1", "WALK-MARKER-2")
    report = [r for r in state_home()["residue"] if r.get("kind") == "report"][0]
    assert report["reason"] == "dry"
    assert "2 of 6 hops" in report["text"]
    assert "nothing arrived" not in report["text"]


def test_a_pane_poll_cannot_spend_a_state():
    lines = markers()
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(*lines)
    try:
        engine.enter("walk", session="pane")
        engine.note_turn("pane")
        engine.tick("pane")
        for _ in range(8):
            engine.deliver_if_due(source="pane")
        active = engine.peek()
        assert active is not None
        assert active["served"] == 2
        engine.inject("pane")
        assert engine.peek() is not None
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_turn_from_another_session_does_not_spend_the_dose():
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider("a → b", "b → c")
    try:
        engine.enter("walk", session="A")
        engine.note_turn("A")
        engine.inject("A")
        assert engine._load()["active"]["served"] == 1
        engine.note_turn("B")
        engine.tick("B")
        assert engine.inject("B") is None
        active = engine._load()["active"]
        assert active["served"] == 1
        assert active["turns"] == 1
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_repeated_line_ends_dry_and_does_not_claim_nothing_arrived():
    line = "WALK-MARKER"
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(line, line, line)
    try:
        engine.enter("walk", session="repeat")
        engine.note_turn("repeat")
        engine.inject("repeat")
        engine.deliver_if_due()
        engine.deliver_if_due()
        assert engine.peek() is None
        report = [r for r in state_home()["residue"] if r.get("kind") == "report"][0]
        assert report["reason"] == "dry"
        assert "nothing arrived" not in report["text"]
        assert "nothing new arrived" in report["text"]
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_repeated_line_is_not_new_material():
    line = "WALK-MARKER"
    drive(line, line, line)
    report = [r for r in state_home()["residue"] if r.get("kind") == "report"][0]
    assert report["reason"] == "dry"
    assert "1 of 6 hops" in report["text"]
    assert "6 of 6 hops" not in report["text"]


def test_a_walk_still_withholds_its_material():
    blocks = drive(*markers())
    assert all("[WHAT ARRIVED" not in block for block in blocks)


def test_an_open_ended_explore_never_completes():
    engine.enter("explore", session="pane")
    for _ in range(4):
        engine.note_turn("pane")
        engine.tick("pane")
        engine.deliver_if_due()
    assert engine.peek()["key"] == "explore"


def test_a_provider_failure_line_is_not_material():
    assert engine._is_failure_line("feed unavailable · timed out")


def test_walk_dose_is_six_hops():
    assert states.STATES["walk"]["dose"] == {"unit": "hops", "n": 6}


def test_a_state_whose_session_never_returns_does_not_hold_its_dose_open():
    """Entered in A, the whole dose served by a pane poll, then A stops talking.

    `seen` can only be advanced by a block built for A, so it stayed at zero while `served`
    climbed past the dose: the state hung at "0 hops left" forever, and because a state is
    policy-global, every other conversation wore its annotation. A turn from B is proof A is
    gone, and it must close the state rather than leave it open for nobody.
    """
    lines = markers()
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(*lines)
    try:
        engine.enter("walk", session="A")
        engine.note_turn("A")
        for _ in range(10):                      # a pane poll, serving ahead
            engine.deliver_if_due()
            engine.tick(None)
        active = engine._load()["active"]
        assert active["served"] >= active["dose"], active
        assert int(active.get("seen") or 0) < active["served"], "the dose must be unseen"

        engine.note_turn("B")
        assert engine.inject("B") is None
    finally:
        sources.PROVIDERS["walk"] = original

    assert engine.peek() is None, "a foreign turn left the state open"
    reasons = [(r.get("reason"), r.get("kind")) for r in state_home()["residue"]]
    assert ("complete", "report") in reasons, reasons


def test_a_foreign_turn_does_not_close_a_state_that_still_has_units_to_serve():
    """The escape hatch is for an unshown dose, not for any state someone else walks in on."""
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(*markers())
    try:
        engine.enter("walk", session="A")
        engine.note_turn("A")
        engine.tick("A")
        engine.inject("A")
        assert engine._load()["active"]["served"] < engine._load()["active"]["dose"]

        engine.note_turn("B")
        engine.inject("B")
        assert engine.peek() is not None, "an unfinished state was closed by a stranger"
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_walk_cannot_serve_past_its_dose():
    """Seven hops on a six-hop walk made the account print "6 of 6 hops" over seven lines."""
    lines = markers(12)
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(*lines)
    try:
        engine.enter("walk", session="dose")
        for _ in range(14):
            engine.note_turn("dose")
            engine.tick("dose")
            engine.inject("dose")
            engine.deliver_if_due(source="pane")
            if engine.peek() is None:
                break
    finally:
        sources.PROVIDERS["walk"] = original

    active = state_home().get("active") or {}
    if active:
        assert active["served"] <= active["dose"], active


def test_the_account_counts_the_trail_it_prints():
    """"6 of 6 hops" followed by seven hops is one statement disagreeing with itself."""
    engine.enter("walk", session="count")
    engine.note_turn("count")
    with open(os.path.join(os.environ["ANTEMUSE_STATES_HOME"], "state.json")) as fh:
        data = json.load(fh)
    data["active"]["served"] = 7          # what an overspending build left behind
    data["journal"].extend(
        {"who": "state", "state": "walk", "event": "walk", "at": 9e9 + i,
         "text": f"a{i} (n) → b{i} (n) · took its far edge"} for i in range(7))
    with open(os.path.join(os.environ["ANTEMUSE_STATES_HOME"], "state.json"), "w") as fh:
        json.dump(data, fh)

    account = engine._account(data, data["active"])

    assert "6 of 6 hops" in account["text"], account["text"]
    assert account["text"].count("[far]") == 6, account["text"]


def test_serving_stops_at_the_dose_even_when_a_provider_returns_a_batch():
    engine.enter("walk", session="batch")
    with open(os.path.join(os.environ["ANTEMUSE_STATES_HOME"], "state.json")) as fh:
        data = json.load(fh)
    data["active"]["served"] = data["active"]["dose"] - 1
    with open(os.path.join(os.environ["ANTEMUSE_STATES_HOME"], "state.json"), "w") as fh:
        json.dump(data, fh)

    served = engine._spend(data["active"], 4)

    assert served == data["active"]["dose"], (served, data["active"]["dose"])
