"""The tool's contract with its caller: what it accepts, and what it says back.

Every test here started as a sentence the tool told a caller that was not true.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _plugin():
    return importlib.import_module("__init__")


def test_entering_a_walk_that_does_not_exist_is_refused():
    """`walks.get()` used to turn an unknown name into `wander`, so a typo entered a real
    walk and said WALKING. The store must be untouched, not merely the message polite."""
    plugin = _plugin()
    from core import engine

    out = plugin._handler({"action": "enter", "name": "walk", "walk": "bogus"})

    assert "no such walk" in out, out
    assert "bogus" in out
    assert (engine._load().get("active") or {}) == {}, "a refused walk left a state behind"


def test_a_real_walk_still_enters():
    plugin = _plugin()
    from core import engine

    out = plugin._handler({"action": "enter", "name": "walk", "walk": "outer"})

    assert out.startswith("WALKING"), out
    assert (engine._load().get("active") or {}).get("walk") == "outer"


def test_the_walk_resolver_refuses_an_unknown_name():
    """The fallback lived here, not in the handler, so it is checked here too."""
    from core import walks

    with pytest.raises(ValueError) as err:
        walks.get("nope")
    assert "no such walk" in str(err.value)

    assert walks.get("outer").name == "outer"
    assert walks.get("").name == "wander", "no name at all still means the default walk"


def test_every_action_the_tool_advertises_is_answered():
    """`card` and `image` were in the rejection message and both answered "no such action"."""
    plugin = _plugin()

    for action in plugin.ACTIONS:
        out = str(plugin._handler({"action": action}))
        assert "no such action" not in out, f"{action} is advertised but not handled: {out}"


def test_the_rejection_names_only_actions_that_exist():
    plugin = _plugin()

    out = plugin._handler({"action": "not-a-real-action"})
    assert out.startswith("no such action"), out
    advertised = [a.strip().rstrip(".") for a in out.split("try:", 1)[1].split(",")]

    assert advertised, out
    for action in advertised:
        assert action in plugin.ACTIONS, f"{action} is recommended and does not exist"
        assert "no such action" not in str(plugin._handler({"action": action}))


def test_the_agent_cannot_enter_the_person_driven_map():
    """`/explore` has no dose and no provider and only the person can end it."""
    plugin = _plugin()

    out = plugin._handler({"action": "enter", "name": "explore"})

    assert out.startswith("explore is person-driven"), out


def test_the_command_still_enters_the_person_driven_map():
    """The refusal belongs to the tool, not to the state: `/explore` is a command a person types."""
    from core import engine

    out = engine.enter("explore")

    assert out.startswith("EXPLORING"), out


def test_the_palette_names_the_three_verbs():
    from core import states

    text = states.palette()

    for verb in ("/walk", "/explore", "/return"):
        assert verb in text, f"{verb} is missing from the state list"
