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


def test_entering_a_walk_blocks_every_tool():
    msg = engine.enter("walk")
    assert "WALKING" in msg
    directive = engine.inject()
    assert "You are walking" in directive
    assert "No tools in this state" in directive
    assert engine.policy("terminal")["action"] == "block"
    assert engine.policy("web_search")["action"] == "block"


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
    assert (engine.policy("terminal") or {}).get("action") == "block"


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
    assert "salt (n) → brine (n)" in out
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
