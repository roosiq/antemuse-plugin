"""`/explore` over the wire: the pane's own two routes, driven for real.

The unit tests prove the engine; this proves the contract the desktop half actually
uses. The cockpit posts what it shoots to ``POST /picks`` and asks ``GET /state`` what
it is in, so both are exercised through the mounted router rather than called as
functions — a route that exists in a test but not in the app is the mistake this
project has made before.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import engine  # noqa: E402


def _client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import dashboard.plugin_api as api

    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/antemuse")
    return TestClient(app)


def test_the_pane_sees_an_open_ended_state_without_a_countdown():
    assert "can't start" not in engine.enter("explore", session="s-api")
    client = _client()

    body = client.get("/api/plugins/antemuse/state?session=s-api").json()
    active = body["active"]
    assert active["key"] == "explore" and active["label"] == "EXPLORING"
    # the pane's counts line branches on dose: zero means "you end it", not "0 to go"
    assert active["dose"] == 0 and active["unit"] == "picks"
    assert active["served"] == 0
    # and the model-facing directive must never ride the pane's payload
    assert "directive" not in active


def test_the_cockpit_body_files_picks_and_the_pane_counts_them():
    assert "can't start" not in engine.enter("explore", session="s-api")
    client = _client()

    posted = client.post("/api/plugins/antemuse/picks",
                         json={"picks": ["bookshelf", "bookshelf", "legacy"], "session": "s-api"})
    assert posted.status_code == 200, posted.text
    assert posted.json() == {"ok": True, "concepts": 2, "added": 3}

    active = client.get("/api/plugins/antemuse/state?session=s-api").json()["active"]
    assert active["served"] == 3

    bad = client.post("/api/plugins/antemuse/picks", json={"picks": "bookshelf"})
    assert bad.status_code == 400


def test_an_explore_survives_the_pane_polling_it():
    """The pane polls every four seconds; a poll is not a turn and must not end the state."""
    assert "can't start" not in engine.enter("explore", session="s-api")
    client = _client()
    for _ in range(6):
        assert client.get("/api/plugins/antemuse/state?session=s-api").json()["active"]["key"] == "explore"
    assert engine.peek() and engine.peek()["key"] == "explore"


def test_picks_stop_being_recorded_once_the_explore_ends():
    assert "can't start" not in engine.enter("explore", session="s-api")
    client = _client()
    client.post("/api/plugins/antemuse/picks", json={"picks": ["bookshelf"], "session": "s-api"})
    engine.stop(session_id="s-api")

    late = client.post("/api/plugins/antemuse/picks", json={"picks": ["late"]})
    assert late.json()["ok"] is False
    assert engine.peek() is None
