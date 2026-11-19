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


def test_a_walk_that_repeats_its_last_hop_sets_out_again(monkeypatch):
    """The engine counts a repeat as drained material, so a walk must never repeat.

    A walk served `jog→motion`, then could not leave it: every later delivery handed back the same
    line, `served` climbed to 2, and the state closed as `dry` — "nothing new came up" — with four
    hops unspent. `walk_text` now resets the walk and steps again when the graph hands back the hop
    it just served.
    """
    from core import engine, sources, walks

    class Stub:
        def __init__(self):
            self.calls = 0
            self.resets = 0

        def step(self, _n: int = 1):
            self.calls += 1
            return ["jog → motion · took its far edge"] if self.calls < 3 else ["motion → gait · took its far edge"]

        def reset(self) -> None:
            self.resets += 1
            self.calls = 3

    stub = Stub()
    monkeypatch.setattr(walks, "get", lambda _name, *_a, **_k: stub)
    monkeypatch.setattr(engine, "watch_state",
                        lambda: {"active": {"walk": "outer",
                                            "shown": [sources._hop_key("jog (n) → motion (n) · took its far edge")]}})

    out = sources.walk_text(1)

    assert stub.resets == 1, "a repeated hop must make the walk set out again"
    assert out and "motion → gait" in out[0], out


def test_a_walk_that_keeps_repeating_sets_out_from_a_random_node(tmp_path, monkeypatch):
    """Two resets are not enough when the seed always resolves to the same start.

    Clearing the cursor and walking again picked the same word again, so the hop came back and the
    engine read it as drained material. The walk must set out from somewhere the graph can leave.
    """
    from core import sources, walks

    class Stub:
        def __init__(self):
            self.calls = 0
            self.cursor_written = None

        def step(self, _n):
            self.calls += 1
            if self.calls <= 3:
                return ["salt → brine · took its far edge"]
            return ["cure → smoke · took its far edge"]

        def reset(self):
            pass

        def _movable_start(self):
            return {"id": "elsewhere", "label": "elsewhere", "pos": "n", "gloss": "", "source": ""}

        def _write_cursor(self, node_id, prev, used=None, pairs=None):
            self.cursor_written = node_id

    stub = Stub()
    monkeypatch.setattr(walks, "get", lambda _name, _path=None: stub)
    monkeypatch.setattr(sources, "_recent_subjects", lambda: [])
    active = {"active": {"key": "walk", "walk": "outer", "shown": ["salt → brine · took its far edge"]}}
    monkeypatch.setattr(sources, "engine", None, raising=False)
    import core.engine as engine_mod
    monkeypatch.setattr(engine_mod, "watch_state", lambda: active)
    notes = []
    monkeypatch.setattr(engine_mod, "record", lambda *a, **k: notes.append(a[1] if len(a) > 1 else ""))

    out = sources.walk_text(1)
    assert out == ["cure → smoke · took its far edge"], out
    assert stub.cursor_written == "elsewhere", "the walk must start somewhere new"
    assert any("set out from" in n for n in notes), notes
