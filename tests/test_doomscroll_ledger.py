"""A state that serves material must leave a ledger row for it.

Shipped bug (0.10.6 and earlier): doomscroll's provider returned feed text and recorded nothing.
`_note_terms` was called by daydream and dream, and walk's own step wrote its concept — doomscroll
had no such call anywhere, so the `served` table had no `move='doomscroll'` rows. The consequence
was not an empty picture: `activation_stills` fell through to the *session baseline* and painted
unrelated chatter, so the pane showed concepts the doomscroll never served, and nothing about it
said so.

The state's own `served` counter is not evidence — it increments when the dose is delivered,
whether or not the ledger write worked. These tests read the ledger.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="doomscroll-ledger-")

from core import activation, engine, history, social, sources  # noqa: E402

FEED = [
    "bluesky · @someone · a raccoon has learned to open the office fridge · [2 skipped as work]",
    "fosstodon · @other · the printer's error message is a short poem about death",
]


def _count(move: str) -> int:
    conn = history._connect()
    assert conn is not None
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM served s WHERE s.move = ?", (move,)).fetchone()[0]
    finally:
        conn.close()


def test_a_doomscroll_writes_its_served_rows(monkeypatch):
    monkeypatch.setattr(social, "pick", lambda steps=1: FEED[:steps])
    before = _count("doomscroll")

    engine.enter("doomscroll", session="scroll-test", platform="discord")
    engine.note_turn()
    engine.tick()
    served = engine.deliver_if_due()
    session = "scroll-test"

    assert served > 0, "the state delivered nothing at all"
    assert _count("doomscroll") > before, \
        "doomscroll delivered material but wrote no served rows"


def test_the_scroll_activities_are_not_recorded_as_concepts(monkeypatch):
    """The handle and the skip note are the state talking about itself, not material."""
    monkeypatch.setattr(social, "pick", lambda steps=1: FEED[:1])
    body = sources._scroll_body(FEED[0])
    assert "bluesky" not in body, body
    assert "@someone" not in body, body
    assert "skipped as work" not in body, body
    assert "raccoon" in body, body


def test_a_failed_feed_serves_nothing_and_is_not_recorded(monkeypatch):
    """`feed unavailable` is a failure, not material; it must not reach the ledger."""
    before = _count("doomscroll")
    assert sources._scroll_body("feed unavailable · no network") == ""
    monkeypatch.setattr(social, "pick", lambda steps=1: ["feed unavailable · no network"])
    engine.enter("doomscroll", session="scroll-fail", platform="discord")
    engine.note_turn()
    engine.tick()
    engine.deliver_if_due()
    assert _count("doomscroll") == before, "a failed feed wrote ledger rows"


def test_the_activation_for_a_doomscroll_is_not_empty_when_it_served(monkeypatch):
    """The stills fall back to the session baseline when a move has no rows — silently.

    That fallback is why the bug looked like 'nothing activated': the picture existed and showed
    the wrong concepts.
    """
    monkeypatch.setattr(social, "pick", lambda steps=1: FEED[:1])
    engine.enter("doomscroll", session="scroll-activation", platform="discord")
    engine.note_turn()
    engine.tick()
    engine.deliver_if_due()

    lit = activation.activations(session="scroll-activation", move="doomscroll")
    assert lit, "a doomscroll that served material has no activation for its own move"
    assert any("raccoon" in label or "fridge" in label or "poem" in label for label in lit), \
        f"the activation is not the material that was served: {sorted(lit)[:6]}"


def test_a_broken_ledger_says_so_instead_of_swallowing_it(monkeypatch):
    """The write path must not break a turn — but silence is how this bug survived a release."""
    def boom(*a, **k):
        raise RuntimeError("disk is on fire")

    monkeypatch.setattr(history, "notice", boom)
    # the journal only takes entries while a state is running
    engine.enter("doomscroll", session="scroll-broken", platform="discord")
    sources._note_terms("a raccoon has learned to open the office fridge", "doomscroll")

    texts = [str(e.get("text") or "") for e in (engine._load().get("journal") or [])]
    notes = [t for t in texts if "served terms not recorded" in t]
    assert notes, "a failed ledger write left no trace anywhere"
    assert "RuntimeError" in notes[-1] and "disk is on fire" in notes[-1], notes[-1]
