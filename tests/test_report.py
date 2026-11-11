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
    assert "3 of 6 hops" in msg
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


def test_a_dry_turn_also_produces_the_account():
    """The clock is gone; a turn that arrives with nothing delivered is what ends it now."""
    engine.enter("daydream")
    assert engine.peek()
    engine.note_turn()          # turn one: nothing owed yet
    engine.note_turn()          # turn two: the material is dry

    directive = engine.inject()
    assert "YOU JUST CAME BACK" in directive
    assert "daydream" in directive


def test_an_empty_state_still_reports_something():
    engine.enter("walk")
    msg = engine.stop()
    assert "nothing arrived" in msg


def _hop(a, b):
    engine.record("state", f"{a} (n) → {b} (n) · took its far edge", event="walk")


def test_the_account_ends_where_the_walk_landed():
    """Six hops used to print five: the dropped one was always the landing.

    The line beside the trail counted `6 step(s)`, so an account that stopped short was
    not just narrow, it was wrong about the only fact the walk promises — where it got to.
    """
    engine.enter("walk")
    for a, b in [("agent", "dowse"), ("dowse", "igloo"), ("igloo", "thalassemia"),
                 ("thalassemia", "coder"), ("coder", "weigela"), ("weigela", "hawk")]:
        _hop(a, b)

    msg = engine.stop()
    assert "6 of 6 hops" in msg, msg
    assert "weigela→hawk [far]" in msg, msg
    assert "agent→dowse [far]" in msg, msg


def test_six_real_wordnet_hops_still_fit_and_end_on_the_landing():
    """The everyday case: six hops with real labels, none of them dropped."""
    engine.enter("walk")
    chain = [("agent", "alveolar rhabdomyosarcoma"),
             ("alveolar rhabdomyosarcoma", "Australian coral snake"),
             ("Australian coral snake", "European fly honeysuckle"),
             ("European fly honeysuckle", "buffel grass"),
             ("buffel grass", "seborrheic dermatitis"),
             ("seborrheic dermatitis", "cyprinodont")]
    for a, b in chain:
        _hop(a, b)

    msg = engine.stop()
    assert "6 of 6 hops" in msg, msg
    assert "agent→alveolar rhabdomyosarcoma [far]" in msg, msg
    assert "seborrheic dermatitis→cyprinodont [far]" in msg, msg
    assert "…" not in msg, msg


def test_a_chain_too_long_for_the_line_gives_up_its_middle_not_its_landing():
    engine.enter("walk")
    names = [f"concept number {i} of a long walk" for i in range(12)]
    for a, b in zip(names, names[1:]):
        _hop(a, b)

    msg = engine.stop()
    assert "6 of 6 hops" in msg, msg     # the dose caps the count
    assert "concept number 0 of a long walk→concept number 1" in msg, msg
    assert "concept number 11 of a long walk" in msg, msg     # where it landed survives
    assert "…" in msg, msg                                    # and the gap is admitted
    assert "concept number 3 of a long walk" not in msg, msg   # the middle gave way
