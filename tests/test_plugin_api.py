"""The pane's payload is counts and glyphs — never the material a model reads.

The leak this guards against is not hypothetical: the state dict the model is
given carries ``directive``, and the engine's projection also carries a journal.
Handing either to a pane would put state machinery on a human surface, which is
exactly what the wordless-card rule exists to prevent. So the payload's keys are
asserted, not merely reviewed.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


def load(name: str):
    spec = importlib.util.spec_from_file_location(
        f"antemuse_test_{name}", DASHBOARD / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


projection = load("projection")
project = projection.project
tools_of = projection.tools_of

WALK = {
    "active": {
        "key": "walk", "walk": "wander", "label": "WALKING",
        "contract": "work continues · the frame is elsewhere",
        "directive": "SECRET MODEL INSTRUCTION",
        "ends_at": 1000.0, "seconds_left": 145, "total_seconds": 180, "turns_left": 4,
        "tools": None,
    },
    "journal": [{"kind": "walk", "text": "salt→ski parka [far]"}],
    "residue": [{"kind": "walk", "text": "residue line"}],
    "now": 855.0,
}


def test_idle_reports_nothing_running():
    payload = project({"active": None, "residue": [], "journal": []}, [], now=5.0)
    assert payload["active"] is None
    assert payload["generated_at"] == 5.0
    assert payload["frame"] == {"cols": 44, "rows": 12, "lines": []}
    assert payload["residue"] == {"count": 0, "kinds": []}


def test_active_state_reports_counts_and_contract():
    payload = project(WALK, ["line one"], now=855.0)
    active = payload["active"]
    assert active["key"] == "walk"
    assert active["label"] == "WALKING"
    assert active["seconds_left"] == 145
    assert active["total_seconds"] == 180
    assert active["turns_left"] == 4
    assert active["contract"] == "work continues · the frame is elsewhere"
    assert payload["frame"]["lines"] == ["line one"]
    assert payload["residue"] == {"count": 1, "kinds": ["walk"]}


def test_payload_never_carries_the_directive_or_the_journal():
    payload = project(WALK, [], now=855.0)
    dumped = json.dumps(payload)
    assert "SECRET MODEL INSTRUCTION" not in dumped
    assert "ski parka" not in dumped
    assert "directive" not in payload["active"]
    assert "journal" not in payload


def test_no_forbidden_key_appears_anywhere_including_nested():
    payload = project(WALK, ["a line"], now=1.0)
    found = set()

    def walk(value, path=""):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in projection.FORBIDDEN:
                    found.add(f"{path}/{key}")
                walk(item, f"{path}/{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")

    walk(payload)
    assert found == set()


def test_tool_modes_are_three_facts():
    assert tools_of(None) == {"mode": "all", "allowed": [], "blocked": []}
    assert tools_of([]) == {"mode": "none", "allowed": [], "blocked": []}
    some = tools_of(["web_search", "read_file"])
    assert some["mode"] == "some"
    assert some["allowed"] == ["read_file", "web_search"]


def test_residue_kinds_are_deduplicated_and_legacy_is_named():
    payload = project(
        {"active": None, "residue": [{"kind": "walk"}, {"kind": "walk"}, "an old string"], "journal": []}
    )
    assert payload["residue"] == {"count": 3, "kinds": ["legacy", "walk"]}


def test_a_missing_frame_is_an_empty_frame_not_an_error():
    payload = project({"active": WALK["active"], "residue": [], "journal": []}, None)
    assert payload["frame"]["lines"] == []


def test_the_route_is_declared_at_state():
    """The desktop half calls ctx.rest('/state'); the route must exist by that name."""
    api = pytest.importorskip("fastapi")  # noqa: F841 -- skip when the server env is absent
    module = load("plugin_api")
    paths = {route.path for route in module.router.routes}
    assert "/state" in paths
