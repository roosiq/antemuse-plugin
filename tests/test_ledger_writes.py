"""A served concept must actually land in the ledger.

Shipped bug: `core/history.py:_prune` referenced `CAP_SERVED`, a constant that did not exist, so
every concept write raised `NameError: name 'CAP_SERVED' is not defined` *after* inserting the
row. The write path catches exceptions by design (a ledger failure must never break a turn), so
the crash surfaced only as a note — `concept write failed · …` — and the walk looked like it was
doing nothing. The e2e test passed anyway, because it counted lit nodes, which the insert had
already done.

So the assertions here are about the *ledger's own record of the run*, not about what a picture
shows: rows written, no failure note, and a `moves` row for the run that just ended.
"""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="ledger-test-")

from core import engine, history  # noqa: E402


def _count(table: str) -> int:
    conn = history._connect()
    assert conn is not None
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_prune_runs_without_a_nameerror():
    """`_prune` executes. It is called from the write path, so a NameError here aborts writes."""
    conn = history._connect()
    assert conn is not None
    try:
        history._prune(conn, time.time())   # would raise NameError before the fix
        conn.commit()
    finally:
        conn.close()


def test_a_full_walk_writes_its_concepts_and_crashes_on_nothing():
    """enter -> a turn per delivery -> stop: the served rows are there and nothing failed."""
    engine.enter("walk", session="ledger-test", platform="discord")
    for _ in range(6):
        engine.note_turn()
        engine.tick()
        engine.deliver_if_due()
    engine.stop("ledger-test")

    assert _count("served") > 0, "a walk that served concepts wrote no served rows"
    assert _count("concepts") > 0, "a walk that served concepts wrote no concept rows"

    # A ledger failure does not raise — it is recorded as an event, by design, so a broken store
    # cannot break a turn. That is exactly why the crash went unnoticed: the journal is where it
    # surfaced, so the journal is what this asserts on.
    history._FAILED.clear()          # the note is deduped per five minutes; don't inherit a mute
    engine.enter("walk", session="ledger-test-2", platform="discord")
    for _ in range(3):
        engine.note_turn()
        engine.tick()
        engine.deliver_if_due()
    engine.stop("ledger-test-2")

    texts = [str(e.get("text") or "") for e in (engine._load().get("journal") or [])]
    bad = [t for t in texts if "concept write failed" in t]
    assert not bad, f"a concept write was reported as failed: {bad}"


def test_a_finished_state_leaves_a_move_row():
    """The moves table was created and its writer written, and then never called by anything."""
    before = _count("moves")
    engine.enter("daydream", session="move-test", platform="discord")
    engine.note_turn()
    engine.tick()
    engine.stop("move-test")
    assert _count("moves") == before + 1, "a finished state left no record that it ran"

    conn = history._connect()
    assert conn is not None
    try:
        row = conn.execute(
            "SELECT state, started, ended, ending FROM moves ORDER BY rowid DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    assert row[0] == "daydream", row
    assert row[2] and row[2] >= row[1], f"ended before it started: {row}"
    assert row[3] == "returned", row
