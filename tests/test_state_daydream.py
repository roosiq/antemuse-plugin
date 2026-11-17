"""Acceptance evidence for the daydream state."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import engine, recall, sources, states


def setup_function(_):
    engine.clear()
    recall.clear()


def _drive(key: str, session: str) -> tuple[str, str]:
    assert "cannot enter" not in engine.enter(key, session=session)
    blocks = []
    for _ in range(8):
        engine.note_turn(session)
        blocks.append(engine.inject(session) or "")
        if engine.peek() is None:
            break
    return "\n".join(blocks), engine.stop(session)


def test_daydream_pairs_own_recorded_turns_and_delivers_its_dose():
    recall.remember("I keep postponing the migration because its boundary is unclear.")
    recall.remember("The release checklist keeps the same deployment boundary visible.")
    recall.remember("A small test can make the deployment boundary explicit before release.")

    assert states.STATES["daydream"]["dose"] == {"unit": "pairs", "n": 2}
    text, closing = _drive("daydream", "daydream-owner")

    assert "memory one:" in text and "memory two:" in text and "touch:" in text
    assert "possibility:" in text
    assert "Tools are open in this state" in text, "tools are open unless the entry asks"
    engine.stop()
    engine.enter("daydream", block=True)
    text = engine.inject() or ""
    assert "Tools are closed in this state; /return ends it." in text
    assert "2 of 2 pairs" in text
    assert "two things that surfaced" in closing
    report = [r for r in engine.watch_state()["residue"] if r.get("kind") == "report"][-1]
    assert report["reason"] == "complete" and report["steps"] == 2


def test_daydream_refuses_entry_when_own_turns_are_empty():
    out = engine.enter("daydream", session="empty-daydream")

    assert "cannot enter daydream" in out and "empty" in out
    assert engine.peek() is None
