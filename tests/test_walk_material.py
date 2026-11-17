"""A hop has to be somewhere the walk could have got to.

The `far` policy used to sample `wordnet.words()` and keep the least similar
candidate, which guaranteed an unrelated word: `idea → zebra-tailed lizard →
Hydra → brown creeper`. These guards keep a hop connected, keep the walk from
doubling back, and keep a broken walk out of the transcript.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="material-test-")

from core import engine, sources, walks  # noqa: E402


def setup_function(_):
    engine.clear()


def within(graph, node, target_id, depth=2):
    """Is `target_id` reachable from `node` in `depth` edges or fewer?"""
    frontier, seen = {node["id"]}, {node["id"]}
    for _ in range(depth):
        nxt = set()
        for nid in frontier:
            cur = graph.resume(nid)
            if cur is None:
                continue
            for _rel, child in graph.edges(cur):
                if child["id"] == target_id:
                    return True
                if child["id"] not in seen:
                    seen.add(child["id"])
                    nxt.add(child["id"])
        frontier = nxt
        if not frontier:
            return False
    return False


def test_a_far_hop_is_two_steps_out_and_never_a_neighbour():
    graph = walks.WordNetGraph()
    node = graph.resolve("memory")
    assert node is not None
    neighbours = {c["id"] for _rel, c in graph.edges(node)}
    seen_connected = 0
    for _ in range(12):
        hop = graph.far_from(node)
        assert hop is not None
        assert hop["id"] not in neighbours, f"a jump must not be an edge: {hop['label']}"
        if within(graph, node, hop["id"], depth=2):
            seen_connected += 1
    assert seen_connected == 12, "every jump has to be reachable, or it is a random word"


def test_a_walk_never_lands_where_it_has_already_stood():
    from nltk.corpus import wordnet as wn
    cursor = tempfile.mkdtemp()
    path = os.path.join(cursor, "c.json")
    with open(path, "w") as fh:
        json.dump({"outer": {"node": wn.synsets("design")[0].name(), "prev": "", "at": 0}}, fh)
    # Fixed start: the property under test is "no repeats", not which seed the tier picked.
    # Ambient seeding made this test pass or fail with the working directory.
    spec = dict(walks.BUILTIN["outer"], name="outer", seed={"mode": "fixed", "node": "design"})
    walk = walks.GraphWalk(spec, __import__("pathlib").Path(path))
    steps = walk.step(5)
    chain = []
    for line in steps:
        head = line.split(" · ")[0]
        if "→" not in head:
            continue
        left, right = (p.strip() for p in head.split("→", 1))
        if not chain:
            chain.append(left)
        elif chain[-1] != left:
            chain.append(left)          # a restarted walk says where it picked up
        chain.append(right)
    assert len(chain) >= 4, steps
    assert len(chain) == len(set(chain)), f"the walk doubled back: {chain}"


def test_an_old_cursor_is_not_where_you_left_off():
    """A day-old cursor kept the walk in leftover WordNet space instead of
    setting out from the work in front of the person."""
    from nltk.corpus import wordnet as wn
    from pathlib import Path

    old = wn.synsets("finback")[0].name()
    path = Path(tempfile.mkdtemp()) / "c.json"

    path.write_text(json.dumps({"outer": {"node": old, "prev": "", "at": 0}}))
    stale = walks.GraphWalk({"name": "outer", **walks.BUILTIN["outer"]}, path)
    first = stale.start_node()
    assert first is not None and first["id"] != old, "a cursor from days ago is not a place to resume"

    import time
    path.write_text(json.dumps({"outer": {"node": old, "prev": "", "at": time.time()}}))
    fresh = walks.GraphWalk({"name": "outer", **walks.BUILTIN["outer"]}, path)
    again = fresh.start_node()
    assert again is not None and again["id"] == f"wordnet:{old}", "a cursor from this sitting still resumes"


def test_a_walk_that_raises_serves_no_material(monkeypatch):
    class Broken:
        name = "outer"

        def step(self, _n=1):
            raise RuntimeError("a synset that no longer resolves")

        def reset(self):
            return None

    monkeypatch.setattr(walks, "get", lambda name: Broken())
    monkeypatch.setattr(engine, "watch_state", lambda: {"active": {"walk": "outer"}})
    assert sources.walk_text(1) == [], "a traceback is not material"


def test_edges_of_an_id_that_is_not_a_synset_are_empty_not_an_error():
    """A cursor can hold a label where an id belongs.

    WordNet answers that with None, and every probe then raised
    `'NoneType' object has no attribute '_hypernyms'` — which a walk printed as
    material, in the app, under the words "walk 'outer' failed".
    """
    graph = walks.WordNetGraph()
    assert graph.edges({"id": "harbor seal", "label": "harbor seal"}) == []
    assert graph.far_from({"id": "harbor seal", "label": "harbor seal"}) is None


def test_a_providers_own_failure_is_not_a_hop():
    """`walk 'outer' failed · …` used to reach the account as the first step of a
    walked path. A line that opens with the state and "failed" is a diagnostic."""
    assert engine._is_failure_line("walk 'outer' failed · RuntimeError: synset")
    assert engine._is_failure_line("walk provider failed · KeyError")
    # A real headline that happens to mention failure is still material.
    assert not engine._is_failure_line("Failed startup raises $2M · the founders say")
    assert not engine._is_failure_line("design (n) → plan (n) · took its hypernym")


def test_a_pane_cannot_spend_a_walk_before_the_person_speaks():
    queue = [f"hop {i}" for i in range(1, 7)]

    def provider(_n):
        return [queue.pop(0)] if queue else []

    original = sources.PROVIDERS.get("walk")
    sources.PROVIDERS["walk"] = provider
    try:
        engine.enter("walk", session="pane-test")
        for _ in range(6):
            engine.deliver_if_due(source="pane")
        active = engine.watch_state()["active"]
        assert int(active.get("served") or 0) == 1, (
            "the pane spent the dose while nobody was typing: "
            f"served={active.get('served')} turns={active.get('turns')}")

        engine.note_turn(session="pane-test")
        engine.deliver_if_due(source="pane")
        active = engine.watch_state()["active"]
        assert int(active.get("served") or 0) == 2, "one turn earns one more hop"
    finally:
        if original is not None:
            sources.PROVIDERS["walk"] = original
        engine.clear()
