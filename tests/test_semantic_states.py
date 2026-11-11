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
    # What matters is that the expiry states the shortfall rather than pretending the act was
    # finished. The count itself was pinned at "2 of 3" and depended on whether the turn's own
    # delivery landed before the expiry — a race between a past `ends_at` and the load that
    # expires it — so the number moved whenever unrelated tests changed the turn order.
    import re
    text = report[-1]["text"]
    m = re.search(r"expired before its dose: (\d+) of 3", text)
    assert m, text
    assert int(m.group(1)) < 3, text


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


def test_a_state_serves_one_unit_per_turn():
    """The dose is unchanged; the units arrive one at a time so the pane can show each.

    A provider that hands back its whole dose in one call (the walk returns all six hops)
    used to land the picture complete in turn one and then hold it, motionless, for the
    rest of the ceiling. Delivery is now paced: one unit per turn, ending at the same dose.
    """
    for key, spec in states.STATES.items():
        dose = int((spec.get("dose") or {}).get("n") or 0)
        engine.enter(key, session="pace", platform="discord")
        engine.note_turn()
        engine.inject()
        active = engine.peek()
        if dose == 1:
            assert active is None, f"{key} did not end on its single unit"
            continue
        assert active is not None, f"{key} ended after one unit of a {dose}-unit dose"
        assert active["served"] == 1, f"{key} served {active['served']} units in one turn"
        for _ in range(dose - 1):
            engine.note_turn()
            engine.inject()
        assert engine.peek() is None, f"{key} was still running after its {dose}-unit dose"
        engine.stop(reason="probe")


def test_drip_is_still_available_and_still_delivers_the_same_dose(monkeypatch):
    """A setting may change how long a state is; it may not change what a state is."""
    from core import settings

    from core import sources

    monkeypatch.setattr(settings, "_raw", lambda key, default=None: "drip" if key == "deliver" else default)
    monkeypatch.setitem(sources.PROVIDERS, "dream", lambda n=1: ["a joining line"] * n)
    engine.enter("dream", session="drip", platform="discord")
    engine.note_turn()
    first = engine.deliver_if_due()
    assert engine.deliver_if_due() == 0, "drip: one delivery per turn"
    engine.note_turn()
    second = engine.deliver_if_due()
    assert first == 1 and second == 1, (first, second)


def test_a_directive_never_promises_material_its_state_does_not_feed():
    """A directive and the arrival policy are one contract, checked as one.

    walk's directive said "each line says how many hops it went" while `feeds: False` suppressed
    the arrival block entirely: the model was told to use lines it could never receive, and the
    only way to obey was to invent a hop. Every other state feeds, so every other directive may
    speak about what arrives. This asserts the two halves agree, for every state, without naming
    any state in particular.
    """
    from core import states

    # "no material will arrive" is the opposite of a promise, so a bare substring search would
    # read the honest sentence as the dishonest one
    import re

    promise = re.compile(r"(?<!no )(?<!no concepts )(what arrives|each line|concepts will arrive)")
    # the detector has to catch the sentence that was actually shipped, or this test is a no-op
    old = ("what arrives are concepts far from the task that are still on a path from it: "
           "each line says how many hops it went")
    assert promise.findall(old), "the detector does not catch the old directive"
    for key, spec in states.STATES.items():
        feeds = bool(spec.get("feeds", True))
        directive = str(spec.get("directive") or "").lower()
        claims = promise.findall(directive)
        # one direction only: a state may feed without advertising it, but a state that does not
        # feed must never tell the model to expect material
        if not feeds:
            assert not claims, f"{key} does not feed but its directive promises {claims}"


def test_a_walk_tells_the_model_it_is_getting_nothing():
    from core import engine, states

    assert states.STATES["walk"]["feeds"] is False
    text = str(states.STATES["walk"]["directive"]).lower()
    assert "no material" in text, "a subtractive state must say so, or the model invents a hop"
    assert "scenery" in text


def test_a_state_command_answers_with_a_waiting_line_not_the_palette():
    """`/walk` used to answer with five states, their ceilings, doses, tool policies and a legend.

    That is a listing, not a reply: the person asked for a walk and got the menu back. What belongs
    under the entry line is one sentence in the state's own voice — the shape of a waiting message.
    """
    from core import states

    card = states.palette()
    assert "AGENT STATES" in card, "the listing still exists for /break and /states"
    for key in states.STATES:
        line = states.waiting(key)
        assert line and "\n" not in line, key
        assert line != key, f"{key} needs words of its own"
        assert states.waiting(key) not in card, "the waiting line is not a menu row"


def test_every_state_has_a_mask_that_matches_its_move():
    """One word per state, checked for the thing it actually does — not for being pretty."""
    from core import states

    wants = {"walk": "walk", "daydream": "memor", "doomscroll": "scroll", "unstuck": "done", "dream": "asleep"}
    for key, needle in wants.items():
        assert needle in states.waiting(key).lower(), (key, states.waiting(key))


def test_every_ending_speaks_in_the_state_that_ended(tmp_path, monkeypatch):
    """A daydream must not come back sounding like a walk.

    The closing block used to be one constant paragraph — the walk's — handed to the model after
    any state, so a daydream's summary arrived in walk language ("the path you walked is scenery",
    "name the approach you were stuck in"). The instruction now belongs to the state that closed.
    """
    from core import states

    for key in ("walk", "daydream", "doomscroll", "dream", "unstuck"):
        text = states.after(key)
        assert text and len(text) > 40, key
        if key != "walk":
            assert "the walk is over" not in text, key
            assert "path you walked" not in text, key

    # every state carries its own, and no two are the same paragraph
    assert len({states.after(k) for k in states.STATES}) == len(states.STATES)

    # the block the model actually receives names the state that closed, not another one
    named = {"walk": "walk", "daydream": "daydream", "doomscroll": "scroll",
             "dream": "dream", "unstuck": "recommendation"}
    for key, word in named.items():
        assert word in states.after(key).lower(), (key, word)


def test_the_pane_counts_the_dose_in_the_states_own_unit(tmp_path, monkeypatch):
    """A daydream owes two *pairs*, a walk six *hops*. Both used to be printed as "turns".

    The pane had only ``turns_left`` to draw from, so it said "2 turns left" for a state whose
    dose is pairs, and the entry line said "6 turn(s)" for one counted in hops. The unit is part
    of what the state is; the number has to be in it.
    """
    from core import engine, states
    from dashboard import projection

    for key, unit in (("walk", "hops"), ("daydream", "pairs"),
                      ("doomscroll", "items"), ("dream", "recombinations")):
        engine.stop(reason="unit")
        engine.enter(key, session=f"unit-{key}", platform="discord")
        line = engine.status_line()
        assert f"{states.STATES[key]['dose']['n']} {unit}" in line, (key, line)
        assert "turn(s)" not in line, (key, line)
        active = projection.project(engine.watch_state())["active"]
        assert active["unit"] == unit, (key, active)
        assert active["dose_left"] == states.STATES[key]["dose"]["n"], (key, active)
        engine.stop(reason="unit")


def test_residue_cap_holds_when_endings_arrive_between_turns(tmp_path, monkeypatch):
    """The cap is on the write, not on the turn.

    The trim lived only in note_turn(), so a straight-line run that entered and ended eight
    states without a turn in between left nine residue entries in the store while every reader
    trusted a cap of three.
    """
    from core import engine

    engine.stop(reason="cap")
    for _ in range(8):
        engine.enter("walk", session="cap-probe", platform="discord")
        engine.stop(reason="cap")
    stored = engine._load().get("residue") or []
    shown = engine.watch_state()["residue"]
    assert len(stored) <= 3, len(stored)
    assert len(shown) <= 3, len(shown)


def test_a_finished_state_reaches_the_person_even_when_the_model_ignores_it(tmp_path):
    """The account must land in the chat, not only in the model's context.

    The plugin hands the model the facts and asks it to say them. A model that answers the
    person's actual question instead left the walk with no post-walk message at all: the state
    ended and the conversation simply moved on. When the reply carries none of the report's
    numbers, the plugin appends the line itself.
    """
    import importlib.util
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("antemuse_t", repo / "__init__.py",
                                                 submodule_search_locations=[str(repo)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["antemuse_t"] = mod
    spec.loader.exec_module(mod)

    from core import engine

    engine.stop(reason="qa")
    engine.enter("walk", session="post-walk", platform="cli")
    engine.note_turn()
    engine.inject(session="post-walk")
    ending = engine.stop(reason="qa")
    mod._PENDING_REPORT = ("post-walk", "walk")

    silent = mod._transform(response_text="Sure — the build is green.", session_id="post-walk")
    assert silent and silent.startswith("Sure — the build is green."), silent
    assert "— " in silent and "step" in silent, silent

    # a model that does say the facts is not double-printed
    engine.stop(reason="qa")
    engine.enter("walk", session="post-walk-2", platform="cli")
    engine.note_turn()
    engine.inject(session="post-walk-2")
    engine.stop(reason="qa")
    facts = engine.unreported("post-walk-2") or {}
    assert facts.get("text"), "no report to test against"
    mod._PENDING_REPORT = ("post-walk-2", "walk")
    said = mod._transform(response_text=facts["text"], session_id="post-walk-2")
    assert said is None or said.count("— ") <= 1, said
