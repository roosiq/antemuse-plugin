"""`/explore` remains person-driven, outside the agent-state table."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import engine, states  # noqa: E402


def setup_function(_):
    engine.clear()


def _enter():
    said = engine.enter("explore", session="s-explore")
    assert "EXPLORING" in said


def test_explore_has_a_separate_open_ended_spec():
    assert "explore" not in states.STATES
    spec = states.spec("explore")
    assert spec["label"] == "EXPLORING"
    assert spec["dose"] == {"unit": "picks", "n": 0}


def test_nothing_can_expire_explore():
    _enter()
    for _ in range(3):
        engine.note_turn("s-explore")
        engine.tick("s-explore")
        assert engine.deliver_if_due() == 0
    assert engine.peek()["key"] == "explore"


def test_picks_are_ignored_unless_explore_is_running():
    assert engine.note_pick(["concept-a"])["ok"] is False
    engine.enter("walk", session="s-explore")
    assert engine.note_pick(["concept-a"])["ok"] is False


def test_picks_are_counted_and_named_on_return():
    _enter()
    engine.note_pick(["bookshelf", "bookshelf", "legacy"])
    assert engine.peek()["picks"]["bookshelf"] == 2
    said = engine.stop(session_id="s-explore")
    assert "bookshelf ×2" in said and "legacy ×1" in said


def test_explore_surfaces_never_claim_a_countdown():
    _enter()
    engine.note_pick(["bookshelf"])
    assert "0/0" not in engine.status_line()
    assert "running · you stop it" in (engine.annotate("hello") or "")


def test_the_pane_route_files_picks():
    from dashboard import plugin_api

    _enter()
    out = plugin_api.picks({"picks": ["bookshelf", "bookshelf", "legacy"]})
    assert out["ok"] and out["added"] == 3 and out["concepts"] == 2
    with pytest.raises(Exception):
        plugin_api.picks({"picks": "bookshelf"})
