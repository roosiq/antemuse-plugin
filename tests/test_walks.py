"""Walks are data: built-ins, user graphs, relations, and continuation."""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))

from kitchen import walks  # noqa: E402


@pytest.fixture()
def cursor(tmp_path):
    return tmp_path / "walk_cursor.json"


def _has_wordnet() -> bool:
    try:
        return bool(walks.WordNetGraph().wn().synsets("walk"))
    except Exception:
        return False


def test_builtins_are_listed_with_their_relations(cursor):
    listed = {w["name"]: w for w in walks.list_walks(cursor)}
    assert {"wander", "upward", "downward", "lateral"} <= set(listed)
    assert listed["upward"]["relations"] == ["hypernym", "holonym"]
    assert listed["lateral"]["graph"] == "wordnet"


def test_manual_walk_is_saved_and_walked(cursor):
    saved = walks.save({"name": "kitchen", "graph": "manual",
                        "edges": {"salt": ["brine"], "brine": ["fish"], "fish": ["salt"]},
                        "seed": {"mode": "fixed", "node": "salt"}}, cursor)
    assert saved["graph"] == "manual"
    walk = walks.get("kitchen", cursor)
    steps = walk.step(3)
    assert "salt" in steps[0] and "brine" in steps[0]
    assert "fish" in steps[2]


def test_manual_walk_continues_from_its_cursor(cursor):
    walks.save({"name": "loop", "graph": "manual", "edges": {"a": ["b"], "b": ["c"], "c": ["a"]},
                "seed": {"mode": "fixed", "node": "a"}}, cursor)
    walk = walks.get("loop", cursor)
    first = walk.step(1)[0]
    second = walk.step(1)[0]
    target = first.split(" → ")[1].split(" ")[0]
    assert second.startswith(target), (first, second)
    assert "a" not in second.split(" → ")[0]


def test_unknown_walk_falls_back_to_wander(cursor):
    assert walks.get("nope", cursor).name == "wander"


def test_builtin_names_cannot_be_overwritten(cursor):
    with pytest.raises(ValueError):
        walks.save({"name": "wander", "graph": "manual", "edges": {"a": ["b"]}}, cursor)


def test_manual_walk_requires_edges(cursor):
    with pytest.raises(ValueError):
        walks.save({"name": "empty", "graph": "manual"}, cursor)


def test_remove_only_touches_user_walks(cursor):
    walks.save({"name": "temp", "graph": "manual", "edges": {"a": ["b"]}}, cursor)
    assert walks.remove("temp", cursor) is True
    assert walks.remove("wander", cursor) is False


def test_relations_are_respected(cursor):
    if not _has_wordnet():
        pytest.skip("wordnet corpus not installed")
    walk = walks.get("upward", cursor)
    walk._write_cursor("dog.n.01", "")
    lines = walk.step(6)
    assert lines
    assert all(("hypernym" in l or "holonym" in l or "picks up again" in l or "dead end" in l
                or "only way back" in l) for l in lines), lines


def test_cursor_is_namespaced_per_walk(cursor):
    walks.save({"name": "one", "graph": "manual", "edges": {"a": ["b"], "b": ["a"]}}, cursor)
    walks.get("one", cursor).step(1)
    data = json.loads(cursor.read_text())
    assert "one" in data and "wander" not in data
