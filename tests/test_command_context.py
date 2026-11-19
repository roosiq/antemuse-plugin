"""Slash commands preserve the owning chat for the remaining walk state."""
from __future__ import annotations

import importlib
import json

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="command-context-")

ROOT = Path(__file__).resolve().parents[1]
from core import engine, storage  # noqa: E402

plugin = importlib.import_module("__init__")


def setup_function(_):
    engine.clear()


def _active():
    return json.loads((storage.data_dir() / "state.json").read_text()).get("active") or {}


@pytest.mark.skipif(not (ROOT / ".git").exists(),
                    reason="project attribution reads the repository the package was extracted from")
def test_a_walk_command_files_the_state_under_the_chat_that_asked():
    """`origin.project` is the nearest ancestor holding `.git`, so this needs one on disk.

    A package extracted from the tarball has none, and this asserted a project name that no
    packager can provide — a repo-only fact, not a defect in the shipped code.
    """
    out = plugin._enter("walk")("", session_id="desk-42", platform="desktop")
    assert "WALKING" in out
    # The walk completes inside the command, so its owner is read from the account and the hops it
    # filed, not from a live row.
    data = json.loads((storage.data_dir() / "state.json").read_text())
    report = [r for r in data["residue"] if r.get("kind") == "report"][-1]
    assert report["session"] == "desk-42", report
    hops = [e for e in data["journal"] if e.get("state") == "walk" and e.get("event") == "walk"][-6:]
    assert hops and all(e.get("session") == "desk-42" for e in hops), hops[-3:]
    # The origin machinery itself is unchanged: an entered state still carries where it came from.
    from core import engine
    engine.enter("walk", session="desk-42", platform="desktop")
    origin = _active()["origin"]
    assert origin["session_id"] == "desk-42"
    assert origin["platform"] == "desktop"
    assert origin["project"]
    engine.stop(reason="reset")


def test_a_walk_command_without_context_still_enters():
    assert "WALKING" in plugin._enter("walk")("")


def test_return_ends_the_walk_of_the_chat_that_asked():
    plugin._enter("walk")("", session_id="desk-42", platform="desktop")
    assert plugin._return("", session_id="desk-42")
    assert not _active()


def test_the_walk_name_argument_still_works_with_context():
    out = plugin._enter("walk")("upward", session_id="desk-42", platform="desktop")
    assert "WALKING" in out or "no such walk" in out.lower()


def test_return_with_nothing_running_does_not_repeat_the_last_ending():
    plugin._enter("walk")("", session_id="idle", platform="desktop")
    engine.stop(session_id="idle")
    assert plugin._return("", session_id="idle") == "nothing running."


def test_entry_line_names_the_walk_dose_not_minutes():
    line = plugin._enter("walk")("", session_id="dose-line", platform="desktop").splitlines()[0]
    assert "min" not in line
    assert "6 hops" in line
