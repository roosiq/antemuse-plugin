"""The delivery door belongs to the chat that owns the state.

The always-mounted status-bar chip asks `/deliver` every 900ms. When no chat is focused it
carries no session, and the old gate `bool(session and owner and session != owner)` let an
empty session straight through: a sessionless poll spent another chat's dose and was shown
that chat's state. Fail closed instead - a caller that cannot name itself as the owner gets a
pure look at nothing, and an unowned state (entered from the CLI) still works.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import engine, recall  # noqa: E402

plugin = importlib.import_module("__init__")


def _api():
    root = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    spec = importlib.util.spec_from_file_location("am_api", root / "dashboard" / "plugin_api.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _seed(session="OWNER-A"):
    engine.clear()
    recall.clear()
    for line in ("the parser keeps failing on nested quotes",
                 "the coffee shop closed after twenty years",
                 "I want the walk to feel like wandering"):
        recall.remember(line, session=session)
    engine.enter("dream", session=session)


def _served():
    doc = json.loads((pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json").read_text())
    return int((doc.get("active") or {}).get("served") or 0)


def test_a_sessionless_poll_cannot_spend_another_chats_dose():
    api = _api()
    _seed()
    before = _served()
    api._state_payload(None, 0, deliver=True)
    assert _served() == before, "a poll with no session spent the owner's dose"


def test_a_sessionless_poll_is_not_shown_another_chats_state():
    api = _api()
    _seed()
    payload = api._state_payload(None, 0, deliver=False)
    assert payload.get("active") in (None, {}), f"leaked the owner's state: {payload.get('active')}"


def test_a_foreign_poll_cannot_spend_the_dose():
    api = _api()
    _seed()
    before = _served()
    api._state_payload("OWNER-B", 0, deliver=True)
    assert _served() == before, "a foreign chat spent the owner's dose"


def test_the_owner_still_gets_its_unit():
    api = _api()
    _seed()
    api._state_payload("OWNER-A", 0, deliver=True)
    assert _served() == 1, "the owner's own poll must still deliver"


def test_an_unowned_state_still_delivers():
    """A state entered with no chat (the CLI path) has no owner to match, so the door stays open."""
    api = _api()
    engine.clear()
    recall.clear()
    for line in ("the parser keeps failing on nested quotes",
                 "the coffee shop closed after twenty years",
                 "I want the walk to feel like wandering"):
        recall.remember(line, session="")
    engine.enter("dream", session="")
    api._state_payload(None, 0, deliver=True)
    assert _served() == 1, "an unowned state must still be deliverable"
