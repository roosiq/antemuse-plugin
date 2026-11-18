"""Every walk ending writes one `moves` row."""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="moves-ledger-")

from core import engine, history, sources  # noqa: E402


def _moves():
    conn = history._connect()
    assert conn is not None
    try:
        return conn.execute("SELECT state, ending, dose_done FROM moves WHERE state = 'walk' ORDER BY id").fetchall()
    finally:
        conn.close()


def _provider(*lines):
    queue = list(lines)

    def call(steps=1):
        return [queue.pop(0)] if queue else []

    return call


def test_a_state_that_ends_dry_records_how_it_ended(monkeypatch):
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = _provider("one hop", "one hop", "one hop")
    try:
        engine.enter("walk", session="moves-dry")
        engine.note_turn("moves-dry")
        engine.inject("moves-dry")
        engine.deliver_if_due()
        engine.deliver_if_due()
        assert engine.peek() is None
        row = _moves()[-1]
        assert row[1] == "dry"
        assert row[2] == 1
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_state_that_finishes_its_dose_records_a_different_ending(monkeypatch):
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = _provider(*[f"hop {n}" for n in range(6)])
    try:
        engine.enter("walk", session="moves-dose")
        # One unit per turn: six hops take six turns, and the sixth closes it in its own block.
        for _ in range(6):
            engine.note_turn("moves-dose")
            engine.inject("moves-dose")
        assert engine.peek() is None
        row = _moves()[-1]
        assert row[1] == "complete"
        assert row[2] == 6
    finally:
        sources.PROVIDERS["walk"] = original


def test_one_row_per_state_not_one_per_turn(monkeypatch):
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = _provider(*[f"hop {n}" for n in range(6)])
    before = len(_moves())
    try:
        engine.enter("walk", session="moves-turns")
        for _ in range(6):
            engine.note_turn("moves-turns")
            engine.inject("moves-turns")
        assert len(_moves()) - before == 1
    finally:
        sources.PROVIDERS["walk"] = original
