"""Tools stay open unless the entry asks for less — the owner's rule, enforced.

A state changes the frame the agent works in. Taking the tools away is a second decision the
caller has to make on purpose (`block: true`), and only then does the state's declared set
apply. `/return` and the `state` tool itself are never blocked, in any state, at any setting.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import engine, recall, states


def setup_function(_):
    engine.clear()
    recall.clear()


def _ready(*_a, **_k):
    return None


def test_tools_stay_open_in_every_state_unless_the_entry_asks(monkeypatch):
    monkeypatch.setattr("core.sources.ready", _ready)
    for key in states.STATES:
        assert "can't start" not in engine.enter(key), key
        assert engine.policy("write_file") is None, f"{key} took a tool away unasked"
        assert engine.policy("terminal") is None, key
        assert "Tools are open in this state" in (engine.inject() or ""), key
        engine.stop()


def test_block_narrows_to_the_state_own_set(monkeypatch):
    monkeypatch.setattr("core.sources.ready", _ready)
    engine.enter("doomscroll", block=True)
    assert engine.policy("web_search") is None
    assert engine.policy("write_file")["action"] == "block"
    engine.stop()


def test_allow_narrows_further_inside_the_set(monkeypatch):
    monkeypatch.setattr("core.sources.ready", _ready)
    engine.enter("doomscroll", block=True, allow=["read_file"])
    assert engine.policy("read_file") is None
    assert engine.policy("web_search")["action"] == "block"
    engine.stop()

    engine.enter("unstuck", block=True, allow=["read_file"])
    assert engine.policy("read_file") is None
    assert engine.policy("search_files")["action"] == "block"
    engine.stop()


def test_a_blocked_state_blocks_everything_when_asked(monkeypatch):
    recall.remember("A recorded turn with enough words for one memory.")
    recall.remember("Another recorded turn with enough words for another memory.")
    recall.remember("A third recorded turn lets two memory pairs remain distinct.")
    monkeypatch.setattr("core.sources.ready", _ready)
    for key in ("daydream", "dream"):
        assert "can't start" not in engine.enter(key, block=True), key
        assert engine.policy("read_file")["action"] == "block", key
        assert key in engine.policy("read_file")["message"], key
        engine.stop()


def test_the_state_tool_is_never_blocked(monkeypatch):
    monkeypatch.setattr("core.sources.ready", _ready)
    for key in states.STATES:
        engine.enter(key)
        assert engine.policy("state") is None, key
        engine.stop()
        engine.enter(key, block=True)
        assert engine.policy("state") is None, key
        engine.stop()
        engine.enter(key, block=True, allow=[])
        assert engine.policy("state") is None, key
        engine.stop()
