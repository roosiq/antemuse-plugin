"""Acceptance evidence for doomscroll's material, dose, and failure path."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import engine, settings, sources, states


def setup_function(_):
    engine.clear()
    settings.clear_overrides()


def _drive(session: str) -> tuple[str, str]:
    assert "cannot enter" not in engine.enter("doomscroll", session=session)
    blocks = []
    for _ in range(8):
        engine.note_turn(session)
        blocks.append(engine.inject(session) or "")
        if engine.peek() is None:
            break
    return "\n".join(blocks), engine.stop(session)


def test_doomscroll_delivers_three_one_line_feed_items(monkeypatch):
    monkeypatch.setattr(sources, "feed", lambda: [
        {"source": "jokes.example", "title": "A ridiculous headline that remains one readable line"},
        {"source": "satire.example", "title": "A second ridiculous headline for the feed"},
        {"source": "odd.example", "title": "A third ridiculous headline for the feed"},
    ])

    assert states.STATES["doomscroll"]["dose"] == {"unit": "items", "n": 3}
    text, closing = _drive("doomscroll-owner")

    assert "3 of 3 items" in text
    assert "Tools are open in this state" in text, "tools are open unless the entry asks"
    engine.stop()
    engine.enter("doomscroll", block=True)
    assert ("Only these tools: web_search, web_extract, read_file, search_files, "
            "browser_exec. /return ends it.") in (engine.inject() or "")
    assert "nothing to take away" in closing
    report = [r for r in engine.watch_state()["residue"] if r.get("kind") == "report"][-1]
    assert report["reason"] == "complete" and report["steps"] == 3


def test_doomscroll_feed_disabled_fails_at_entry():
    settings.override(doomscroll_feed=False)

    out = engine.enter("doomscroll", session="disabled-feed")

    assert "cannot enter doomscroll" in out and "disabled" in out
    assert engine.peek() is None
