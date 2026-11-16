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


def test_an_unknown_walk_is_refused_not_silently_replaced(cursor):
    """It used to become `wander`, so a typo entered a walk nobody asked for and said WALKING."""
    with pytest.raises(ValueError) as err:
        walks.get("nope", cursor)
    assert "no such walk" in str(err.value)


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
    # A dead end restarts the walk instead of stopping it, and that restart is a hop
    # too — it says so in its own words. What must never appear is a plain step.
    assert all("far edge" in s or "picks up again" in s for s in steps), steps

    graph = walks.WordNetGraph()
    node = graph.resume(wn.synsets("hand")[0].name())
    neighbours = {n["id"] for _, n in graph.edges(node)}
    far = graph.far_from(node)
    assert far is not None and far["id"] not in neighbours, "a far hop must not be an edge"


def test_an_outer_hop_is_a_jump_but_never_an_unrelated_word(cursor):
    """Outer used to mean "least similar word in the dictionary", which served
    `idea → zebra-tailed lizard`. A jump is now the rim of the neighbourhood:
    farther than a step, still reachable in two edges, and never 0.0.
    """
    import statistics
    from nltk.corpus import wordnet as wn

    graph = walks.WordNetGraph()
    node = graph.resolve("hand")
    assert node is not None
    cur = wn.synset(node["id"])

    def sim(other):
        if other is None:
            return None
        v = cur.path_similarity(wn.synset(other["id"]))
        return None if v is None else float(v)

    steps = [sim(graph.resume(child["id"])) for _rel, child in graph.edges(node)]
    steps = [s for s in steps if s is not None]
    jumps = [sim(graph.far_from(node)) for _ in range(20)]
    jumps = [j for j in jumps if j is not None]

    assert jumps, "the walk must be able to leave"
    assert statistics.mean(jumps) < statistics.mean(steps), (
        "a jump has to be farther than a step: "
        f"jumps {statistics.mean(jumps):.3f} steps {statistics.mean(steps):.3f}")
    unrelated = [j for j in jumps if j == 0.0]
    assert len(unrelated) <= 1, f"{len(unrelated)}/20 jumps went nowhere near the node"


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


# ------------------------------------------------------------------ the name is a filename

def test_a_walk_name_cannot_reach_outside_the_walks_directory(cursor):
    """The name comes from the model, and it is joined into a path.

    `name="../../../auth"` used to mean `HERMES_HOME/auth.json`: readable, overwritable, or
    deletable by a state argument. A name is lowercase letters, digits, '-' and '_' — no dots
    at all, so '..' cannot be spelled — and the resolved path must still be inside the walks
    directory before anything is read, written or unlinked.
    """
    outside = cursor.parent / "auth.json"
    outside.write_text('{"token": "must survive"}')

    bad = ["../auth", "../../auth", "..", ".", "a/b", "..\\auth", "/etc/passwd",
           "walk.json/../../auth", "x" * 65, ".. /auth", "a/.b"]
    for name in bad:
        with pytest.raises(ValueError):
            walks.get(name, cursor)
        with pytest.raises(ValueError):
            walks.save({"name": name, "graph": "manual", "edges": {"a": ["b"]}}, cursor)
        with pytest.raises(ValueError):
            walks.remove(name, cursor)
    # No name at all is not a traversal: it means the default walk, which is what the
    # provider asks for when a state recorded none.
    assert walks.get("", cursor).name == "wander"

    assert outside.read_text() == '{"token": "must survive"}'
    assert not (cursor.parent / "walks" / "..json").exists()


def test_the_three_entry_points_agree_on_what_a_name_means(cursor):
    """`save()` has always normalised case and spaces; get and remove agree with it now, so
    "/walk outward" and walk_new "outward" are the same walk rather than two different rules."""
    walks.save({"name": "Outward Sky", "graph": "manual", "edges": {"a": ["b"]}}, cursor)
    assert walks.get("outward sky", cursor).name == "outward-sky"
    assert walks.get("  OUTWARD SKY  ", cursor).name == "outward-sky"
    assert walks.valid_name("Outward Sky") is True
    assert walks.normalise("Outward Sky") == "outward-sky"
    assert walks.remove("Outward Sky", cursor) is True


def test_a_command_enters_the_normalised_name(cursor):
    """`/walk outward sky` must enter `outward-sky`, not refuse a name walk_new accepted."""
    import importlib.util
    import pathlib

    repo = pathlib.Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("antemuse_walkname", repo / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Ctx:
        def __init__(self):
            self.commands = {}

        def register_hook(self, *a, **k):
            pass

        def register_command(self, name, handler=None, **k):
            self.commands[name] = handler

        def register_tool(self, **kw):
            pass

        def register_auxiliary_task(self, *a, **k):
            pass

        def register_skill(self, *a, **k):
            pass

        def emit(self, *a, **k):
            pass

        def get_config(self, key, default=None):
            return default

    # Saved where the engine looks, not beside the fixture's cursor file: the entry now
    # checks the name against the walks that exist, so both must read the same directory.
    walks.save({"name": "Outward Sky", "graph": "manual", "edges": {"a": ["b"]}})
    ctx = Ctx()
    module.register(ctx)
    from core import engine
    engine.stop(reason="reset")
    out = ctx.commands["walk"]("outward sky", session_id="walk-name", platform="discord")
    assert "WALKING" in out.upper(), out
    assert engine.peek()["walk"] == "outward-sky", engine.peek()
    engine.stop(reason="reset")


def test_a_valid_name_still_saves_and_removes(cursor):
    for name in ("hearth", "two-words", "with_underscore", "n1"):
        walks.save({"name": name, "graph": "manual", "edges": {"a": ["b"]}}, cursor)
        assert walks.get(name, cursor).name == name
        assert walks.remove(name, cursor) is True


def test_the_second_resolution_point_refuses_it_too(cursor):
    """`walk_text()` reads the name off the active state, so the fallback was reachable twice."""
    with pytest.raises(ValueError):
        walks.get("no-such-walk", cursor)
