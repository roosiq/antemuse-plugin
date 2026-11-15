"""A completed walk leaves an account with its actual route."""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="states-report-")
from core import engine  # noqa: E402


def setup_function(_):
    engine.clear()


def _hop(a, b):
    engine.record("state", f"{a} (n) → {b} (n) · took its far edge", event="walk")


def test_stop_returns_an_account_with_the_steps():
    engine.enter("walk")
    _hop("salt", "brine")
    _hop("brine", "river")
    msg = engine.stop()
    assert "WALKING ended" in msg
    assert "2 of 6 hops" in msg
    assert "salt→brine [far]" in msg


def test_account_is_kept_as_residue_and_journalled():
    engine.enter("walk")
    _hop("hinge", "river")
    engine.stop()
    state = engine.watch_state()
    report = [r for r in state["residue"] if r.get("kind") == "report"][0]
    assert report["state"] == "walk" and report["steps"] == 1
    assert state["journal"][-1]["event"] == "report"


def test_empty_walk_still_reports_something():
    engine.enter("walk")
    assert "nothing arrived" in engine.stop()


def test_account_ends_where_walk_landed():
    engine.enter("walk")
    for a, b in [("agent", "dowse"), ("dowse", "igloo"), ("igloo", "hawk")]:
        _hop(a, b)
    msg = engine.stop()
    assert "agent→dowse [far]" in msg and "igloo→hawk [far]" in msg
