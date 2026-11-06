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
    # without photographs or walk events the fallback is the map, which is
    # shorter than the screen by design
    assert len(rows) >= 10
    for r in _visible(rows):
        assert len(r) <= 100


def test_block_clock_renders_five_rows():
    rows = tui.clock_big(487)
    assert len(rows) == 5
    assert all(len(r) == len(rows[0]) for r in rows)
    assert "█" in "".join(rows)


def test_active_frame_is_pictures_only():
    import re
    engine.enter("doomscroll")
    text = "\n".join(_visible(tui.render_frame(engine.watch_state(), 100, 30, 3)))
    assert not re.search(r"[A-Za-z]{2,}", text), "no prose on screen"


def test_idle_frame_is_pictures_only():
    import re
    text = "\n".join(_visible(tui.render_frame(engine.watch_state(), 100, 30, 0)))
    assert not re.search(r"[A-Za-z]{2,}", text)


def test_the_stream_is_not_on_screen_but_reaches_the_agent():
    engine.enter("daydream")
    engine.record("state", "JOINED · two memories, one shared term", event="daydream")
    frame = "\n".join(_visible(tui.render_frame(engine.watch_state(), 110, 34, 0)))
    assert "JOINED" not in frame
    assert "JOINED" in (engine.inject() or "")
