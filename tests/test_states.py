"""States change behaviour: tools, reply shape, residue, and expiry."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="states-test-")

from core import states, engine  # noqa: E402


def setup_function(_):
    engine.clear()


def test_a_walk_leaves_every_tool_open():
    """Ambient: the work continues, so nothing is taken away."""
    msg = engine.enter("walk")
    assert "WALKING" in msg
    directive = engine.inject()
    assert "walking while you work" in directive
    assert "No tools in this state" not in directive
    assert engine.policy("terminal") is None
    assert engine.policy("web_search") is None


def test_dream_still_takes_every_tool():
    engine.enter("dream")
    assert engine.policy("terminal")["action"] == "block"
    assert "No tools in this state" in (engine.inject() or "")


def test_doomscroll_allows_reading_but_blocks_writing():
    engine.enter("doomscroll")
    assert engine.policy("web_search") is None
    assert engine.policy("read_file") is None
    blocked = engine.policy("write_file")
    assert blocked["action"] == "block"
    assert "doomscrolling" in blocked["message"]


def test_doomscroll_is_read_only_and_random():
    engine.enter("doomscroll")
    assert engine.policy("web_search") is None
    assert engine.policy("terminal")["action"] == "block"
    directive = engine.inject()
    assert "random" in directive.lower()
    assert "do not produce anything" in directive


def test_state_expires_on_turns_and_leaves_residue():
    engine.enter("daydream")  # 2 turns
    assert engine.tick() is not None
    assert engine.tick() is not None
    assert engine.tick() is None                     # spent
    assert engine.peek() is None
    assert "daydream" in engine.inject()


def test_state_expires_on_clock():
    engine.enter("walk", minutes=1)
    path = None
    import pathlib
    path = pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    data = json.loads(path.read_text())
    data["active"]["ends_at"] = time.time() - 1
    path.write_text(json.dumps(data))
    assert engine.peek() is None
    assert "walk" in engine.inject()


def test_return_ends_the_state_and_keeps_residue():
    engine.enter("walk")
    out = engine.stop()
    assert "ended" in out
    assert engine.peek() is None
    assert "walk" in engine.status() and "ended" not in engine.status()


def test_loading_the_plugin_keeps_a_live_state():
    """A new process (every CLI invocation) must not drop a state that is running."""
    engine.enter("walk", minutes=5)
    engine.settle()
    live = engine.peek()
    assert live is not None, "settle() must not end a state inside its window"
    assert live["key"] == "walk"


def test_loading_the_plugin_expires_a_dead_clock_and_keeps_the_account():
    import pathlib
    engine.enter("walk", minutes=5)
    engine.record("state", "salt to brine", event="walk")
    path = pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    data = json.loads(path.read_text())
    data["active"]["ends_at"] = time.time() - 1
    path.write_text(json.dumps(data))
    engine.settle()
    assert engine.peek() is None
    reports = [r for r in engine.watch_state()["residue"] if r.get("kind") == "report"]
    assert reports and "salt" in reports[-1]["text"]


def test_annotate_marks_the_reply_only_while_active():
    assert engine.annotate("hello") is None
    engine.enter("walk", minutes=5)
    out = engine.annotate("hello")
    assert out.startswith("hello")
    assert "walking" in out
    assert "/return" in out


def test_entering_a_second_state_reports_the_first():
    engine.enter("walk")
    msg = engine.enter("dream")
    assert "left walk" in msg
    assert engine.peek()["key"] == "dream"


def test_unknown_state_is_refused():
    assert "no such state" in engine.enter("levitate")


def test_every_state_declares_a_contract_and_a_residue():
    for key, spec in states.STATES.items():
        assert spec["contract"], key
        assert spec["residue"], key
        assert spec["directive"], key


def test_palette_lists_the_commands():
    out = states.palette()
    for key in states.STATES:
        assert f"/{key}" in out
    assert "/return" in out


def test_the_account_counts_material_not_the_agents_own_words():
    engine.enter("walk", minutes=5)
    engine.record("state", "salt (n) → brine (n) · took its hyponym", event="walk")
    engine.record("agent", "the salt made the water feel heavier", event="walk")
    out = engine.stop()
    assert "1 step(s)" in out, out
    assert "salt→brine [hyponym]" in out, out
    assert "heavier" not in out, "the agent's prose is not material"


def test_a_new_state_does_not_inherit_the_last_states_material():
    engine.enter("walk", minutes=5)
    engine.record("state", "salt (n) → brine (n) · took its hyponym", event="walk")
    engine.stop()
    engine.enter("doomscroll", minutes=5)
    engine.record("state", "a post about rent", event="scroll")
    text = engine.inject() or ""
    arrived = text.split("[WHAT ARRIVED WHILE YOU WERE THERE", 1)[-1]
    arrived = arrived.split("[YOU JUST CAME BACK", 1)[0].split("[RESIDUE:", 1)[0]
    assert "a post about rent" in arrived
    assert "brine" not in arrived, "the doomscroll must not consume the walk's steps"


def test_the_account_stops_at_the_states_own_clock():
    import pathlib
    engine.enter("walk", minutes=2)
    engine.record("state", "salt (n) → brine (n) · took its hyponym", event="walk")
    path = pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    data = json.loads(path.read_text())
    # a two-minute walk whose end was only noticed an hour later
    data["active"]["entered_at"] -= 3600
    data["active"]["ends_at"] = data["active"]["entered_at"] + 120
    path.write_text(json.dumps(data))
    engine.settle()
    text = [r["text"] for r in engine.watch_state()["residue"] if r.get("kind") == "report"][-1]
    assert text.startswith("walk 2m"), text


def test_a_missing_corpus_refuses_the_entry_instead_of_going_empty(monkeypatch):
    from core import sources
    monkeypatch.setattr(sources, "ready", lambda kind: f"{kind} has no material here")
    msg = engine.enter("walk")
    assert msg.startswith("cannot enter walk · walk has no material here")
    assert engine.peek() is None, "a refused entry must not leave a state running"


def test_a_present_corpus_lets_the_walk_in():
    from core import sources
    assert sources.ready("walk") is None
    assert sources.ready("dream") is None
    assert sources.ready("doomscroll") is None, "doomscroll needs no corpus"


def test_ready_explains_a_missing_nltk(monkeypatch):
    import importlib.util
    from core import sources
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a, **k: None)
    why = sources.ready("walk")
    assert why and "nltk" in why and "uv pip install" in why


def test_the_trail_does_not_end_on_a_dangling_separator():
    engine.enter("walk", minutes=5)
    engine.record("state", "hand (n) → palm (n) · took its meronym", event="walk")
    out = engine.stop()
    trail = out.splitlines()[0].split("· ", 2)[-1]
    assert not trail.rstrip().endswith("·"), trail


def test_a_turn_brings_material_that_the_dead_thread_missed():
    """One turn per process: without this a state delivers one step, not several.

    Dream still feeds material; a walk deliberately does not."""
    from core import sources
    engine.enter("dream", minutes=5)
    monkeypatch_calls = []
    import core.engine as eng
    class Fake:
        PROVIDERS = {"dream": lambda n: ["salt (n) → brine (n) · took its hyponym"]}
    import sys
    real = sources.PROVIDERS
    sources.PROVIDERS = Fake.PROVIDERS
    try:
        assert eng.deliver_if_due() == 1, "the first turn of a state gets material"
        assert eng.deliver_if_due() == 0, "not due twice in a row"
        text = engine.inject() or ""
        assert "salt (n) → brine (n)" in text
    finally:
        sources.PROVIDERS = real


def test_a_walk_supplies_nothing_to_the_working_turn():
    """Subtraction, not addition: no material is handed over while walking."""
    engine.enter("walk", 3)
    engine.record("state", "hand (n) → palm (n) · took its far edge", event="walk")
    text = engine.inject() or ""
    assert "[WHAT ARRIVED" not in text
    assert "palm" not in text, "the step must not reach the working turn"


def test_a_dream_still_hands_its_material_over():
    engine.enter("dream", 3)
    engine.record("state", "invented · a sell missing its rate", event="dream")
    assert "[WHAT ARRIVED" in (engine.inject() or "")


def test_a_walk_ends_by_taking_the_frame_away():
    engine.enter("walk", 3)
    engine.record("state", "hand (n) → palm (n) · took its far edge", event="walk")
    engine.inject()
    out = engine.stop()
    assert "different first step" in out
    text = engine.inject() or ""
    assert "frame you were in is gone" in text
    assert "different first step" in text
    assert "scenery, not a hint" in text


def test_a_dream_ends_by_asking_for_a_summary():
    engine.enter("dream", 3)
    out = engine.stop()
    assert "Summarise it in three lines" in out
