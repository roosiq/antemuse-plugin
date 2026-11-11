"""Every ending writes a `moves` row — not just `/return`.

The table was created, the writer written, and then never called for a release. It was wired into
`stop()` next, and still nothing appeared, because a state that ends by *expiry* (time-out or
dose-exhausted — the common ending) never goes through `stop()`. So `moves` looked broken when it
was merely unrecorded, and the natural conclusion was "no state has ended yet", which was wrong.

Both endings go through `engine._record_finish` now. These tests end a state each way and read
the table.
"""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="moves-ledger-")

from core import engine, history, social, sources  # noqa: E402

FEED = [
    "bluesky · @a · the office fridge is now a raccoon habitat · [1 skipped as work]",
    "fosstodon · @b · the printer has started writing poems about death",
    "babylonbee.com · @c · Local Man Unsure Why Fridge Has Raccoon In It",
]


def _moves(state: str) -> list:
    conn = history._connect()
    assert conn is not None
    try:
        return conn.execute(
            "SELECT state, ending, dose_done FROM moves WHERE state = ? ORDER BY id", (state,)
        ).fetchall()
    finally:
        conn.close()


def test_a_state_that_expires_by_time_records_how_it_ended(monkeypatch):
    monkeypatch.setattr(social, "pick", lambda steps=1: FEED[:steps])
    engine.enter("doomscroll", session="moves-time", platform="discord")
    engine.note_turn()
    engine.tick()
    engine.deliver_if_due()

    data = engine._load()
    data["active"]["ends_at"] = time.time() - 1
    engine._save(data)
    engine.tick()

    assert engine.peek() is None, "the state should have expired"
    rows = _moves("doomscroll")
    assert rows, "a state expired and left no moves row"
    assert rows[-1][1] == "expired", rows[-1]
    assert rows[-1][2] >= 0, rows[-1]


def test_a_state_that_finishes_its_dose_records_a_different_ending(monkeypatch):
    """The dose ending is not the expiry ending and must not be labelled as one."""
    monkeypatch.setattr(social, "pick", lambda steps=1: FEED[:steps])
    engine.enter("doomscroll", session="moves-dose", platform="discord")
    for _ in range(3):
        engine.note_turn()
        engine.tick()
        engine.deliver_if_due()
        engine.complete_if_dosed()

    assert engine.peek() is None, "the dose should have ended the state"
    rows = _moves("doomscroll")
    assert rows, "a state finished its dose and left no moves row"
    assert rows[-1][1] and rows[-1][1] != "expired", rows[-1]
    assert rows[-1][2] == 3, rows[-1]


def test_one_row_per_state_not_one_per_turn(monkeypatch):
    """A turn is not an ending. Three turns of a state that then expires: one row."""
    monkeypatch.setattr(social, "pick", lambda steps=1: FEED[:steps])
    before = len(_moves("walk"))
    engine.enter("walk", session="moves-turns", platform="discord")
    for _ in range(3):
        engine.note_turn()
        engine.tick()
        engine.deliver_if_due()
    data = engine._load()
    data["active"]["ends_at"] = time.time() - 1
    engine._save(data)
    engine.tick()
    assert len(_moves("walk")) - before == 1
