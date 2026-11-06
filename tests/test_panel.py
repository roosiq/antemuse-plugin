"""The CLI panel: one frame, both sides, readable in a terminal."""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="states-panel-")

from kitchen import engine, panel  # noqa: E402


def setup_function(_):
    engine.clear()


def test_idle_panel_says_nothing_is_running_debug():
    out = panel.debug(engine.watch_state(), w=88, color=False)
    assert "ANTEMUSE" in out
    assert "nothing is running" in out
    assert "THE AGENT" in out and "YOU" in out


def test_active_panel_shows_state_clock_and_contract_debug():
    engine.enter("walk")
    out = panel.debug(engine.watch_state(), w=88, color=False)
    assert "WALKING" in out
    assert "concept to concept" in out
    assert "closed" in out
    assert "█" in out or "░" in out


def test_both_columns_carry_their_own_words_debug():
    engine.enter("daydream")
    engine.record("agent", "a lid that will not stay down")
    engine.record("person", "the fridge stopping mid-hum")
    out = panel.debug(engine.watch_state(), w=96, color=False)
    assert "a lid that will not stay down" in out
    assert "the fridge stopping mid-hum" in out


def test_empty_person_column_teaches_the_note_command_debug():
    engine.enter("walk")
    out = panel.debug(engine.watch_state(), w=88, color=False)
    assert "/note" in out


def test_panel_respects_a_narrow_terminal():
    engine.enter("walk")
    out = panel.debug(engine.watch_state(), w=64, color=False)
    assert max(len(line) for line in out.splitlines()) <= 80


def test_residue_survives_into_the_next_panel_debug():
    engine.enter("walk")
    engine.stop()
    out = panel.debug(engine.watch_state(), w=88, color=False)
    assert "residue" in out
    assert "walked" in out


def test_clock_and_bar_helpers():
    assert panel.clock(0) == "00:00"
    assert panel.clock(487) == "08:07"
    assert panel.bar(1.0, 4) == "████"
    assert panel.bar(0.0, 4) == "░░░░"


def test_panel_is_pictures_only():
    import re
    out = panel.render(engine.watch_state())
    assert out.strip()
    assert not re.search(r"[A-Za-z]{2,}", out)
