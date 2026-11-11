"""The walk must exist in the ledger the pane draws from, and in every interface.

Two defects made a walk invisible outside the chat:

1. The built-in walk served six hops and recorded none of them. `_note_terms` was called by
   daydream and dream; walk's WordNet provider never wrote a row, so `activations()` had nothing
   for `move='walk'`, `lit` was 0, and the pane's trail query found no path to draw.
2. The pane refused to draw a state whose recorded origin session differed from the session it
   asked about. A state entered from a slash command is recorded against the surface that typed
   it, so the pane fell back to the profile baseline and showed the same background nodes in
   every state — the same nine concepts during a walk as during a dream.

These tests read the ledger and the pane payload, not the state's own counters.
"""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="walk-pane-")

from core import activation, engine, history, sources  # noqa: E402
from dashboard import plugin_api  # noqa: E402

# A stub keeps the test offline; the ledger rows it produces are what the picture reads.


def _rows(move: str, session: str) -> int:
    conn = history._connect()
    assert conn is not None
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM served s WHERE s.move = ? AND s.session = ?",
            (move, session)).fetchone()[0]
    finally:
        conn.close()


HOPS = ["morris dance→sea swallow [far]", "sea swallow→thalassemia [far]",
        "thalassemia→long-horned beetle [far]"]


def test_a_walk_writes_its_hops_to_the_served_ledger(monkeypatch):
    monkeypatch.setattr(sources, "PROVIDERS", {**sources.PROVIDERS,
                                               "walk": lambda steps=1: list(HOPS[:steps])})
    engine.stop(reason="reset")
    before = _rows("walk", "walk-ledger")
    engine.enter("walk", session="walk-ledger", platform="discord")
    engine.note_turn()
    engine.deliver_if_due()
    assert _rows("walk", "walk-ledger") > before, "a walk served hops and wrote no ledger rows"

    lit = activation.activations("walk-ledger", "walk")
    assert lit, "the walk's own firings are empty, so the pane has nothing to light"


def test_the_pane_draws_the_state_another_session_entered(monkeypatch):
    monkeypatch.setattr(sources, "PROVIDERS", {**sources.PROVIDERS,
                                               "walk": lambda steps=1: list(HOPS[:steps])})
    engine.stop(reason="reset")
    engine.enter("walk", session="typed-here", platform="discord")
    engine.note_turn()
    engine.deliver_if_due()

    payload = plugin_api.graph(session="the-pane-asks-with-this", limit=1400)
    assert payload.get("key") == "walk", "the pane dropped a running state it did not enter"
    assert _rows("walk", "typed-here") >= 1, "the walk wrote no firings for the pane to use"


def test_a_failure_line_never_lights_the_picture():
    before = _rows("walk", "fail-line")
    engine.enter("walk", session="fail-line", platform="discord")
    engine.note_turn()
    started = engine.peek() or {}
    assert started, "state did not enter"
    from core import engine as eng
    assert eng._is_failure_line("feed unavailable · no network")
    assert not eng._is_failure_line("morris dance→sea swallow [far]")
    assert _rows("walk", "fail-line") == before


def test_every_state_reports_the_same_dose_to_the_chat_and_the_pane():
    """/state, the entry line and the pane must agree on the dose and its unit.

    An unstuck owes one direction. The entry line said so while /state said three, because the
    active record stored spec["turns"] — three — beside a unit of "directions".
    """
    from core import states

    for key, spec in states.STATES.items():
        engine.stop(reason="dose")
        line = mod_line(key)
        engine.enter(key, session=f"dose-{key}", platform="discord")
        active = (plugin_api.state(session=f"dose-{key}") or {}).get("active") or {}
        want = (spec.get("dose") or {}).get("n") or spec["turns"]
        unit = (spec.get("dose") or {}).get("unit") or "turn(s)"
        assert active.get("dose") == want, f"{key}: pane says {active.get('dose')}, dose is {want}"
        singular = unit[:-1] if want == 1 and unit.endswith("s") and unit != "turn(s)" else unit
        assert active.get("unit") == singular, \
            f"{key}: pane says {active.get('unit')}, unit is {singular}"
        assert f"{want} {unit}".split()[0] in line, f"{key}: entry line disagrees: {line}"


def mod_line(key: str) -> str:
    import importlib.util
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("antemuse_dose", repo / "__init__.py",
                                                  submodule_search_locations=[str(repo)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["antemuse_dose"] = mod
    spec.loader.exec_module(mod)
    return mod._enter(key)("", session_id=f"dose-{key}", platform="discord")


def test_a_walk_that_just_ended_still_draws_its_path(monkeypatch):
    """The picture must survive the walk's ending.

    A walk delivers its whole dose in one turn and closes in that same turn, so the moment the
    path exists is the moment the state stops being active. With nothing active the pane fell
    back to the session baseline and the six hops vanished — the person saw the same background
    nodes as in every other state. The last finished state stays drawn.
    """
    monkeypatch.setattr(sources, "PROVIDERS", {**sources.PROVIDERS,
                                               "walk": lambda steps=1: list(HOPS[:steps])})
    engine.stop(reason="reset")
    engine.enter("walk", session="ended-walk", platform="discord")
    engine.note_turn()
    engine.deliver_if_due()
    engine.stop(reason="qa")
    assert not engine.peek(), "the walk is still running; this test is about the ended one"

    payload = plugin_api.graph(session="ended-walk", limit=1400)
    assert payload.get("key") == "walk", "the pane dropped back to the profile baseline"
    assert payload.get("path"), "the ended walk left no trail to draw"


def test_a_walk_entered_with_no_session_still_lights_its_own_hops():
    """The app and scripts enter a state with an empty origin session.

    Entered from the desktop or by a capture script, a walk records `origin.session_id` as ""
    while its servings are written against the conversation that took the turn. The pane scoped
    the picture to the recorded origin — "" — so it lit one stale empty-session concept and drew
    a trail nobody walked, while the walk's own six hops stayed dark. The owner the picture
    draws is the session the ledger says fired, origin or no origin.
    """
    engine.stop(reason="reset")
    engine.enter("walk", session="walk-origin-blank", platform="desktop")
    data = engine._load()
    data["active"]["origin"]["session_id"] = ""
    engine._save(data)
    assert not (engine.peek() or {}).get("origin", {}).get("session_id"), "the origin is not blank"
    history.notice("porbeagle", move="walk", session="turn-took-it", at=time.time())

    payload = plugin_api.graph(session="", limit=1400)
    lit = [n["l"] for n in payload["nodes"] if n["w"] > 0.05]
    assert payload["key"] == "walk", payload["key"]
    assert "porbeagle" in lit, f"the walk's own hop is not lit: {lit}"
    assert "porbeagle" in (payload.get("path") or []), payload.get("path")


def test_an_empty_pane_lights_nothing():
    """No state and no session: the pane said "no state" over one lit, day-old concept.

    A state entered from a script writes its servings against an empty session. With nothing
    running and no session to scope by, `activations("")` returned the newest of those — an
    ancient hop — and because every weight is normalised against the brightest row in the same
    set, that lone stale row became 1.0 and the floor never dropped it. The empty pane draws the
    ground with nothing lit: a dark picture, not a blank one.
    """
    engine.stop(reason="reset")
    history.notice("porbeagle", move="walk", session="", at=time.time() - 86400)
    # The stale serving must really be readable, or the assertion below proves nothing.
    assert activation.activations("", None), "no empty-session serving was written"

    payload = plugin_api.graph(session="", limit=1400)
    assert payload["key"] == "profile", payload["key"]
    assert payload["lit"] == 0, [n["l"] for n in payload["nodes"] if n["w"] > 0.05]
    assert all(n["w"] == 0 for n in payload["nodes"])
    assert payload["nodes"], "the ground is still drawn: a dark picture, not a blank one"


def test_a_state_entered_from_a_chat_lights_the_pane(monkeypatch):
    """A /walk typed in a chat has a real owner; that is the normal entry path.

    `watch_state()` hands the pane a whitelisted slice of the active record, and `origin` and
    `entered_at` were not in it. `graph()` reads exactly those two, so a chat-entered walk —
    the ordinary way one is entered — drew a map with nothing lit, and its trail query ran with
    a window of 0.0, which is every walk ever recorded rather than this one. The trail is the
    discriminator: an older walk in the ledger must not appear in a picture of this one.
    """
    monkeypatch.setattr(sources, "PROVIDERS", {**sources.PROVIDERS,
                                               "walk": lambda steps=1: list(HOPS[:steps])})
    engine.stop(reason="reset")
    # An earlier walk by the same conversation: without `entered_at` the trail window is 0.0
    # and this row joins the picture of the walk being drawn now.
    history.notice("leopard", move="walk", session="local-REALCHAT", at=time.time() - 900)

    engine.enter("walk", session="local-REALCHAT", platform="discord")
    engine.note_turn()
    engine.deliver_if_due()
    assert engine.peek(), "the walk should still be running with a dose left"

    body = plugin_api.graph(session="pane-x", limit=1400)
    lit = [n for n in body["nodes"] if n["w"] > 0.05]
    assert lit, "a chat-entered walk that served a concept must light it"
    path = body.get("path") or []
    spoke = HOPS[0].split("\u2192")[0].strip().split()[0]
    assert spoke in path, f"the trail is not this walk's: {path}"
    assert "leopard" not in path, f"the trail spans earlier walks too: {path}"
