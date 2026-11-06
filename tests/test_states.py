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


def test_snap_ends_the_state_and_keeps_residue():
    engine.enter("walk")
    out = engine.stop()
    assert "ended" in out
    assert engine.peek() is None
    assert "walk" in engine.status() and "ended" not in engine.status()


def test_annotate_marks_the_reply_only_while_active():
    assert engine.annotate("hello") is None
    engine.enter("walk", minutes=5)
    out = engine.annotate("hello")
    assert out.startswith("hello")
    assert "walking" in out
    assert "/snap" in out


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
    assert "/snap" in out
