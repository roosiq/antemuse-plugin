"""Every state comes back with an account of what happened in there.

The plugin knows the facts — how long, how many steps, which material arrived.
The agent supplies the meaning. These tests hold the facts side.
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="states-report-")

from core import engine  # noqa: E402


def setup_function(_):
    engine.clear()


def test_stop_returns_an_account_with_the_steps():
    engine.enter("walk")
    engine.record("state", "salt to brine", event="walk")
    engine.record("state", "hinge to river", event="walk")
    engine.record("state", "river to door", event="walk")

    msg = engine.stop()
    assert "WALKING ended" in msg
    assert "3 step(s)" in msg
    assert "salt" in msg and "river" in msg
    assert "different first step" in msg.lower()


def test_the_account_is_kept_as_residue_and_journalled():
    engine.enter("dream")
    engine.record("state", "a hinge that remembers being a river", event="dream")
    engine.stop()

    state = engine.watch_state()
    reports = [r for r in state["residue"] if r.get("kind") == "report"]
    assert reports, state["residue"]
    assert reports[0]["state"] == "dream"
    assert reports[0]["steps"] == 1

    journalled = [e for e in state["journal"] if e.get("event") == "report"]
    assert journalled and journalled[-1]["state"] == "dream"


def test_next_turn_is_told_to_talk_about_it():
    engine.enter("doomscroll")
    engine.record("state", "feed item about a harbour", event="doomscroll")
    engine.stop()

    directive = engine.inject()
    assert "YOU JUST CAME BACK" in directive
    assert "harbour" in directive


def test_expiry_also_produces_the_account():
    engine.enter("daydream")
    active = engine.peek()
    assert active
    # run the clock out without spending turns
    data = engine._load()
    data["active"]["ends_at"] = 0
    engine._save(data)

    directive = engine.inject()
    assert "YOU JUST CAME BACK" in directive
    assert "daydream" in directive


def test_an_empty_state_still_reports_something():
    engine.enter("walk")
    msg = engine.stop()
    assert "nothing arrived" in msg
