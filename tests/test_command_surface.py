"""The public verbs are a contract, so an undefined verb is a test failure.

Three things went wrong here that no test caught: `/states` was described as listing
states while rendering a picture, `/keep #2` was documented against a numbering no
surface published, and `/break walk` was a second spelling of `/walk`. Each is a
definition defect, so each gets an assertion rather than a memory.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "specs/changes/command-surface/spec.md"

import sys
sys.path.insert(0, str(ROOT))
from core import states  # noqa: E402


def registered_commands() -> set[str]:
    src = (ROOT / "__init__.py").read_text()
    named = set(re.findall(r'register_command\(name="([a-z_]+)"', src))
    assert "for key in states.STATES" in src, "state commands are not loop-registered"
    return named | set(states.STATES)


def documented_commands() -> set[str]:
    """First column of any table row: `/walk` and `enter` are both verbs."""
    text = SPEC.read_text()
    return set(re.findall(r"^\| `/?([a-z_]+)", text, re.M))


def schema_actions() -> set[str]:
    src = (ROOT / "__init__.py").read_text()
    m = re.search(r'"enum": \[([^\]]+)\]', src)
    assert m, "no action enum in the schema"
    return set(re.findall(r'"([a-z_]+)"', m.group(1)))


def test_every_registered_command_is_defined():
    missing = sorted(registered_commands() - documented_commands())
    assert not missing, f"commands with no definition in the command-surface spec: {missing}"


def test_every_schema_action_is_defined():
    missing = sorted(schema_actions() - documented_commands())
    assert not missing, f"tool actions with no definition: {missing}"


def test_commands_do_not_differ_only_by_plurality():
    names = registered_commands()
    for name in names:
        if name + "s" in names:
            # allowed only if the spec says which is the frame and which is the catalogue
            assert f"`/{name}s`" in SPEC.read_text(), f"/{name} and /{name}s are undocumented neighbours"


def test_the_public_surface_is_six():
    assert registered_commands() == {"walk", "daydream", "doomscroll", "dream", "trailhead",
                                     "return"}


def test_a_person_message_becomes_a_note_without_a_command():
    import importlib
    module = importlib.import_module("__init__")
    src = (ROOT / "__init__.py").read_text()
    assert "def _person_text" in src, "no automatic capture of the person's side"
    assert 'engine.record("person", said)' in src
    # the capture is bounded and only runs inside a state
    assert "text[:400]" in src
    body = src[src.index("def _pre_llm_call"):src.index("def _post_tool_call")]
    assert "if engine.peek():" in body
    # the host's real kwarg is `user_message` (agent/turn_context.py); messages and
    # conversation_history are fallbacks for older hosts
    assert module._person_text(
        {"user_message": "the build keeps failing on the same test"}
    ) == "the build keeps failing on the same test"
    assert module._person_text({"messages": [
        {"role": "user", "content": "fallback path"},
    ]}) == "fallback path"
    assert module._person_text({"conversation_history": [
        {"role": "assistant", "content": "x"},
        {"role": "user", "content": [{"type": "text", "text": "block content"}]},
    ]}) == "block content"
    assert module._person_text({"messages": [{"role": "assistant", "content": "x"}]}) == ""
    assert module._person_text({}) == ""


def test_break_does_not_enter_a_state():
    src = (ROOT / "__init__.py").read_text()
    assert 'register_command(name="break"' not in src, "/break is a command again"
    handler = src[src.index("def _handler"):src.index("# ------------------------------------------------------------------ hooks")]
    assert 'if action == "break":' in handler, "the recommendation must still be reachable as a tool action"




def test_a_recommendation_is_posted_once_through_the_host():
    import importlib
    module = importlib.import_module("__init__")

    posted = []

    class Host:
        def post_message(self, text):
            posted.append(text)

    module._HOST = Host()
    module._LAST_UPDATE = ""
    assert module._post("this looks like a walk · same tool failed 3× · /walk 5") is True
    assert len(posted) == 1 and "walk" in posted[0]
    # no host, no crash
    module._HOST = object()
    assert module._post("anything") is False
