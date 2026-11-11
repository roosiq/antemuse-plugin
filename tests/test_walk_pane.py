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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="walk-pane-")

from core import activation, engine, history, sources  # noqa: E402
from dashboard import plugin_api  # noqa: E402

HOPS = ["morris dance→sea swallow [far]", "sea swallow→thalassemia [far]",
        "thalassemia→long-horned beetle [far]"]


def _rows(move: str, session: str) -> int:
    conn = history._connect()
    assert conn is not None
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM served s WHERE s.move = ? AND s.session = ?",
            (move, session)).fetchone()[0]
    finally:
        conn.close()


def test_a_walk_writes_its_hops_to_the_served_ledger(monkeypatch):
    monkeypatch.setattr(sources, "PROVIDERS", {**sources.PROVIDERS,
                                               "walk": lambda steps=1: list(HOPS[:steps])})
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
    engine.enter("walk", session="typed-here", platform="discord")
    engine.note_turn()
    engine.deliver_if_due()

    payload = plugin_api.graph(session="the-pane-asks-with-this", limit=1400)
    assert payload.get("key") == "walk", "the pane dropped a running state it did not enter"
    assert payload.get("lit", 0) >= 1, "the pane drew no firings for a running walk"
    assert payload.get("path"), "the pane has no trail for the walk it is drawing"


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
        assert active.get("unit") == unit, f"{key}: pane says {active.get('unit')}, unit is {unit}"
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
