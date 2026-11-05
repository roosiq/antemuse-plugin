"""The room machine: phase rotation, state effects, commit, and two projections."""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_ROOM_HOME"] = tempfile.mkdtemp(prefix="room-test-")

from kitchen import phases, room as room_mod, store  # noqa: E402
from kitchen.visual import Frame, Spark, render_text  # noqa: E402


def fresh(seed="a machine that converts boredom into a plan"):
    store.save_active(None) if hasattr(store, "save_active") else None
    room_mod.save(None)
    return room_mod.create(seed)


def spark_text(title="Charge for the second thought",
               because="Instead of assuming the first answer is free, flip the resource expectation so only the follow-up is billed, because the second thought is the one people attend to.",
               nxt="Add one line to the price page and test it with two users by Friday."):
    return f"{title} :: {because} :: {nxt}"


def test_step_returns_a_move_brief():
    room = fresh()
    out = room_mod.step(room)
    assert "PHASE" not in out
    assert "DISCOVER" in out
    assert "a machine that converts boredom" in out
    assert room["phase"] == "discover"


def test_state_phase_applies_and_advances():
    room = fresh()
    room["phase"] = "walk"
    out = room_mod.step(room)
    assert "WALK" in out and "residue" in out
    assert room["relief"] == 1
    assert room["phase"] == "shift"  # walk's successor in the rotation


def test_dissociate_rewrites_the_seed_and_expects_far():
    room = fresh()
    room["rotation"] = ["discover", "dissociate", "flip"]
    room["phase"] = "dissociate"
    out = room_mod.step(room)
    assert "a stranger in 2036 inherits" in room["seed"]
    assert room["expect_far"] is True
    assert "DISSOCIATE" in out


def test_dream_recombines_two_sparks():
    room = fresh()
    room["sparks"] = [
        {"n": 1, "arc": 1, "phase": "discover", "move": "unpack", "score": 60, "distance": "lateral",
         "title": "Bill the boredom", "because": "b", "do_first": "d", "seed": "s", "at": 0},
        {"n": 2, "arc": 1, "phase": "flip", "move": "flip", "score": 70, "distance": "lateral",
         "title": "Sell it before it exists", "because": "b", "do_first": "d", "seed": "s", "at": 0},
    ]
    room["phase"] = "dream"
    room_mod.step(room)
    assert " meets " in room["seed"]


def test_doomscroll_charges_the_next_spark():
    room = fresh()
    room["phase"] = "doomscroll"
    room_mod.step(room)
    assert room["penalty"] == 10
    # the rotation puts converge next; force a move phase to commit
    room["phase"] = "flip"
    card, spark = room_mod.commit(room, spark_text())
    assert spark is not None
    assert "doomscroll debt" in card
    assert room["penalty"] == 0


def test_commit_scores_advances_and_reseeds():
    room = fresh()
    card, spark = room_mod.commit(room, spark_text())
    assert spark and spark["score"] > 0
    assert room["sparks"][-1]["title"] == "Charge for the second thought"
    assert room["seed"].startswith("Charge for the second thought")
    assert room["phase"] == phases.next_phase(room["rotation"], "discover")


def test_commit_rejects_non_move_phases():
    room = fresh()
    room["phase"] = "walk"
    card, spark = room_mod.commit(room, spark_text())
    assert spark is None
    assert "does not take a spark" in card


def test_converge_keeps_best_and_opens_next_arc():
    room = fresh()
    room["sparks"] = [
        {"n": 1, "arc": 1, "phase": "discover", "move": "unpack", "score": 61, "distance": "lateral",
         "title": "A", "because": "b", "do_first": "d", "seed": "s", "at": 0},
        {"n": 2, "arc": 1, "phase": "flip", "move": "flip", "score": 88, "distance": "far",
         "title": "B", "because": "b", "do_first": "d", "seed": "s", "at": 0},
    ]
    room["phase"] = "converge"
    out = room_mod.step(room)
    assert room["keepers"][-1]["title"] == "B"
    assert room["arc"] == 2
    assert room["phase"] == "discover"
    assert "CONVERGE" in out


def test_both_projections_carry_the_same_numbers():
    room = fresh()
    room_mod.commit(room, spark_text())
    room["phase"] = "flip"
    room_mod.commit(room, spark_text("Sell it before it exists",
                                     "Instead of assuming the hold reserves something built, reverse the sequence so the reservation is sold first, because a paid hold is a forecast.",
                                     "Take three paid reservations by Friday and count refunds."))
    f = room_mod.frame(room)
    text = render_text(f)
    assert f"| {f.total}/{f.cap}" in text
    for s in f.sparks:
        assert f"r{s.n} {s.phase} {s.score} {s.distance}" in text


def test_poster_renders_a_png():
    room = fresh()
    room_mod.commit(room, spark_text())
    path = room_mod.poster(room)
    assert path.endswith(".png")
    with open(path, "rb") as fh:
        assert fh.read(8) == b"\x89PNG\r\n\x1a\n"


def test_palette_lists_every_phase():
    out = phases.palette()
    for key in phases.PHASES:
        assert key in out
