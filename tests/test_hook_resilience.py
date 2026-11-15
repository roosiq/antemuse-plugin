"""A plugin hook must never take the tool channel down.

The bug this file exists for: entering `/explore` made every tool call in the session
fail with ``pre_tool_call plugin callback _pre_tool_call raised KeyError:
'turns_left'``. No tool could run — not the ones the state meant to block, all of them —
because the policy hook raised instead of returning a decision, and a missing field on a
state that does not carry it was enough to do it.

Two rules come out of that, and both are tested here:

1. ``_pre_tool_call`` answers with a decision or with nothing, never with an exception.
2. Every hook path that reads the state record tolerates a record that is missing the
   field it wants — including a residue entry written by an older version.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import engine, states  # noqa: E402


def _plugin():
    spec = importlib.util.spec_from_file_location(
        "antemuse_hooks", os.path.join(ROOT, "__init__.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _store() -> dict:
    from core import storage
    return json.loads((storage.data_dir() / "state.json").read_text())


@pytest.mark.parametrize("key", sorted(states.STATES))
def test_every_state_survives_the_hook_paths(key):
    """Enter each state and walk the reads the hooks depend on. None may raise."""
    said = engine.enter(key, session=f"s-{key}")
    assert "cannot enter" not in said, said
    decision = engine.policy("terminal")
    assert decision is None or decision.get("action") == "block", decision
    engine.tick()
    engine.note_turn()
    engine.deliver_if_due()
    engine.complete_if_dosed()
    assert isinstance(engine.status_line(), str)
    assert isinstance(engine.status(), str)
    engine.inject()
    assert isinstance(engine.annotate("hello"), (str, type(None)))
    engine.stop(session_id=f"s-{key}")


def test_an_open_ended_state_cannot_wedge_the_tool_channel():
    """The exact shape of the shipped failure: explore running, a tool call attempted."""
    plugin = _plugin()
    assert "cannot enter" not in engine.enter("explore", session="s-wedge")
    # whatever the decision is, it is a decision — not an exception
    for tool in ("terminal", "read_file", "write_file", "execute_code"):
        assert plugin._pre_tool_call(tool) is None


def test_a_broken_policy_decision_allows_the_call(monkeypatch):
    """If the policy cannot be computed, tools keep working and the log says why."""
    plugin = _plugin()

    def boom(_name):
        raise KeyError("turns_left")

    monkeypatch.setattr(engine, "policy", boom)
    assert plugin._pre_tool_call("terminal") is None


def test_a_legacy_residue_entry_does_not_crash_the_tick():
    engine.enter("walk", session="s-legacy")
    engine.stop(session_id="s-legacy")
    # an entry from a version that stored bare strings, and one with no count at all
    data = _store()
    data["residue"] = ["a walk that ended without a record", {"kind": "report", "text": "old"}]
    from core import storage
    (storage.data_dir() / "state.json").write_text(json.dumps(data))

    engine.tick()          # used to raise KeyError: 'turns_left'
    after = _store()["residue"]
    assert isinstance(after, list)          # it decays rather than exploding
    for entry in after:
        assert isinstance(entry, dict)
