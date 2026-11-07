"""Walks are data: built-ins, user graphs, relations, and continuation."""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))

from core import walks  # noqa: E402


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
    saved = walks.save({"name": "hearth", "graph": "manual",
                        "edges": {"salt": ["brine"], "brine": ["fish"], "fish": ["salt"]},
                        "seed": {"mode": "fixed", "node": "salt"}}, cursor)
    assert saved["graph"] == "manual"
    walk = walks.get("hearth", cursor)
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


def test_the_outer_walk_jumps_instead_of_stepping(cursor):
    """The default walk goes far on every hop, and never to a neighbour."""
    import json
    from nltk.corpus import wordnet as wn
    from core import walks
    cursor.write_text(json.dumps({"outer": {"node": wn.synsets("hand")[0].name(), "prev": "", "at": 0}}))
    walk = walks.GraphWalk({"name": "outer", **walks.BUILTIN["outer"]}, cursor)
    steps = walk.step(6)
    assert all("far edge" in s for s in steps), steps

    graph = walks.WordNetGraph()
    node = graph.resume(wn.synsets("hand")[0].name())
    neighbours = {n["id"] for _, n in graph.edges(node)}
    far = graph.far_from(node)
    assert far is not None and far["id"] not in neighbours, "a far hop must not be an edge"


def test_outer_hops_are_farther_than_wander_hops(cursor):
    import json
    import re
    import statistics
    from nltk.corpus import wordnet as wn
    from core import walks
    STEP = re.compile(r"^(?P<a>.+?) \([a-z]+\) → (?P<b>.+?) \([a-z]+\)")

    def mean_similarity(name, n=16, seed="hand"):
        cursor.write_text(json.dumps({name: {"node": wn.synsets(seed)[0].name(), "prev": "", "at": 0}}))
        walk = walks.GraphWalk({"name": name, **walks.BUILTIN[name]}, cursor)
        sims = []
        for step in walk.step(n):
            m = STEP.match(step)
            if not m:
                continue
            a, b = wn.synsets(m.group("a")), wn.synsets(m.group("b"))
            if not a or not b:
                continue
            v = a[0].path_similarity(b[0])
            sims.append(0.0 if v is None else v)
        if len(sims) < 3:                      # a dead-end start yields no pairs
            return mean_similarity(name, n, seed="river")
        return statistics.mean(sims)

    assert mean_similarity("outer") + 0.1 < mean_similarity("wander")


def test_artifacts_follow_the_project(tmp_path, monkeypatch):
    """A walk taken in a repository resumes there, not in the plugin's home."""
    import os
    from core import storage
    repo = tmp_path / "some-project"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.delenv("ANTEMUSE_STATES_HOME", raising=False)
    monkeypatch.chdir(repo)
    assert storage.project_root() == repo.resolve()
    local = storage.project_dir()
    assert local == repo.resolve() / ".antemuse" and local.is_dir()
    assert walks.cursor_path_default().parent == local
