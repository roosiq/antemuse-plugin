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


def test_states_description_matches_what_it_returns():
    src = (ROOT / "__init__.py").read_text()
    row = re.search(r'register_command\(name="states".*?description="([^"]+)"', src, re.S)
    assert row, "/states is not registered"
    description = row.group(1).lower()
    found = re.search(r'def _states\(_raw: str\) -> str:\n(.*?)\n\n', src, re.S)
    assert found, "no _states handler"
    handler = found.group(1)
    if "tui.run()" in handler or "surfaces.card" in handler:
        assert "picture" in description or "takeover" in description, (
            "/states renders the picture but is described as something else"
        )


def test_break_does_not_enter_a_state():
    src = (ROOT / "__init__.py").read_text()
    found = re.search(r'def _break\(raw: str\) -> str:\n(.*?)\n\n\n', src, re.S)
    assert found, "no _break handler"
    body = found.group(1)
    assert "engine.enter" not in body, "/break enters a state; that is /walk's job"
    assert "it does not enter" in body, "/break must say what it is not"
