"""The takeover frame: block clock, drained bar, two columns, key legend."""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="states-tui-")

from kitchen import definitions, engine, tui  # noqa: E402


def setup_function(_):
    engine.clear()


def _visible(rows):
    return [tui.strip(r) for r in rows]


def test_frame_fills_the_screen_without_overflowing():
    engine.enter("walk")
    rows = tui.render_frame(engine.watch_state(), 100, 30, 0)
    assert len(rows) >= 28
    for r in _visible(rows):
        assert len(r) <= 100


def test_block_clock_renders_five_rows():
    rows = tui.clock_big(487)
    assert len(rows) == 5
    assert all(len(r) == len(rows[0]) for r in rows)
    assert "█" in "".join(rows)


def test_active_frame_names_the_state_and_hides_the_menu():
    engine.enter("doomscroll")
    text = "\n".join(_visible(tui.render_frame(engine.watch_state(), 100, 30, 3)))
    assert "DOOMSCROLLING" in text
    assert "random feed" in text
    assert "web_search" in text


def test_idle_frame_offers_every_state():
    text = "\n".join(_visible(tui.render_frame(engine.watch_state(), 100, 30, 0)))
    assert "no state running" in text
    for key in definitions.STATES:
        assert key in text
    assert "q quit" in text


def test_both_columns_appear_with_their_entries():
    engine.enter("daydream")
    engine.record("agent", "a vending machine that only takes expired coins")
    engine.record("person", "the fridge stopping mid-hum")
    text = "\n".join(_visible(tui.render_frame(engine.watch_state(), 110, 34, 0)))
    assert "THE AGENT" in text and "YOU" in text
    assert "vending machine" in text
    assert "fridge stopping" in text


def test_bar_drains_as_time_passes():
    engine.enter("daydream")
    state = engine.watch_state()
    state["active"]["seconds_left"] = state["active"]["total_seconds"]
    full = "\n".join(_visible(tui.render_frame(state, 100, 30, 0)))
    state["active"]["seconds_left"] = 60
    low = "\n".join(_visible(tui.render_frame(state, 100, 30, 0)))
    assert full.count("█") > low.count("█")


def test_spinner_moves():
    engine.enter("daydream")
    a = "\n".join(_visible(tui.render_frame(engine.watch_state(), 100, 30, 0)))
    b = "\n".join(_visible(tui.render_frame(engine.watch_state(), 100, 30, 1)))
    assert a != b
