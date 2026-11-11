"""A command is not a message: it carries the chat that asked.

The desktop pane asks ``/state?session=<this chat>`` and refuses a state that belongs to another
chat — by design, because a chat's state is that chat's. A slash command produces no turn, so the
"last channel that spoke" is the wrong answer, and it made a walk entered from the desktop look
like a walk entered from Discord: the pane was correctly told the state was somebody else's and
never painted it.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="command-context-")

import importlib  # noqa: E402

from core import engine, storage  # noqa: E402

plugin = importlib.import_module("__init__")


def setup_function(_):
    engine.clear()


def _active():
    path = storage.data_dir() / "state.json"
    return json.loads(path.read_text()).get("active") or {}


def test_a_command_files_the_state_under_the_chat_that_asked():
    handler = plugin._enter("walk")
    out = handler("", session_id="desk-42", platform="desktop")
    assert "WALKING" in out
    active = _active()
    assert active["origin"]["session_id"] == "desk-42"
    assert active["origin"]["platform"] == "desktop"


def test_a_command_without_context_still_enters():
    """Older hosts pass no context; the state still enters, it is just not attributed."""
    handler = plugin._enter("daydream")
    assert "DAYDREAM" in handler("")


def test_return_ends_the_state_of_the_chat_that_asked():
    plugin._enter("walk")("", session_id="desk-42", platform="desktop")
    assert plugin._return("", session_id="desk-42")
    assert not (_active().get("key"))


def test_the_walk_name_argument_still_works_with_context():
    handler = plugin._enter("walk")
    out = handler("upward", session_id="desk-42", platform="desktop")
    assert "WALKING" in out or "no such walk" in out.lower()


def test_return_with_nothing_running_does_not_repeat_the_last_ending():
    """`/return` handed back the previous account and looked like it had just ended a state
    the person was never in. The stale ending is only there once a state has closed, so the
    state has to close first."""
    plugin._enter("walk")("", session_id="idle", platform="desktop")
    engine.note_turn()
    engine.inject(session="idle")          # the dose falls due and the state closes
    engine.stop(session_id="idle")
    assert not engine.peek()
    told = plugin._return("", session_id="idle")
    assert told == "not in a state.", told
    assert "WALKING" not in told and "ended" not in told, told


def test_entry_line_leads_with_the_dose_not_the_ceiling():
    """A dream is over after one turn of work, yet the line said "30 min"; an unstuck that
    owes ONE direction announced three."""
    lines = {}
    for key in ("walk", "dream", "unstuck", "daydream", "doomscroll"):
        engine.stop(reason="look")
        lines[key] = plugin._enter(key)("", session_id="dose-line", platform="desktop").splitlines()[0]
    for key, line in lines.items():
        assert "up to" in line, (key, line)
        assert "min" not in line.split("up to")[0], (key, line)
    assert "1 direction" in lines["unstuck"], lines["unstuck"]
    assert " 1 directions" not in lines["unstuck"], lines["unstuck"]
    engine.stop(reason="look")
