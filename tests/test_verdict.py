"""A keep or a trash is the one thing the product can be measured by.

The pane names the concept under the reticle and posts the judgement; the tally it
prints comes from the same ledger row. These tests drive the routes the desktop
half really calls, not the functions behind them.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import engine, history  # noqa: E402


def _client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import dashboard.plugin_api as api

    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/antemuse")
    return TestClient(app)


def test_a_keep_is_written_where_the_ledger_can_count_it():
    result = engine.note_verdict("kept concept", "keep", session="verdict-test")
    assert result["ok"] is True and result["recorded"] == 1, result
    assert history.verdicts(30)["keep"] >= 1


def test_a_verdict_is_keep_or_trash_and_nothing_else():
    assert engine.note_verdict("concept", "meh")["ok"] is False
    assert engine.note_verdict("", "keep")["ok"] is False


def test_the_pane_posts_a_verdict_and_reads_the_tally():
    client = _client()

    posted = client.post("/api/plugins/antemuse/verdict",
                         json={"label": "via route", "verdict": "trash", "session": "s-verdict"})
    assert posted.status_code == 200, posted.text
    assert posted.json()["ok"] is True, posted.json()

    tally = client.get("/api/plugins/antemuse/verdicts").json()
    assert tally["trash"] >= 1, tally
    assert set(tally) == {"keep", "trash", "rate"}, tally
    assert tally["rate"] is None or 0.0 <= tally["rate"] <= 1.0, tally


def test_a_named_concept_is_required_and_an_unknown_body_does_not_500():
    client = _client()
    assert client.post("/api/plugins/antemuse/verdict", json={}).status_code == 200
    assert client.post("/api/plugins/antemuse/verdict", json={}).json()["ok"] is False
    assert client.get("/api/plugins/antemuse/verdicts").status_code == 200
