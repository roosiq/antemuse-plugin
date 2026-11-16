"""Contract and acceptance tests for interchangeable walk graphs (R1–R11)."""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import engine, history, walks  # noqa: E402


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture()
def corpus(home):
    directory = home / "graphs"
    directory.mkdir()
    (directory / "onboarding.json").write_text(json.dumps({
        "name": "onboarding",
        "source": "Team handbook",
        "licence": "CC-BY-4.0",
        "nodes": {
            "carousel": {"label": "carousel", "pos": "n", "gloss": "an onboarding rotation"},
            "brief": {"label": "brief", "pos": "n", "gloss": "a short orientation"},
            "guide": {"label": "guide", "pos": "n", "gloss": "a person who helps"},
        },
        "edges": [
            {"from": "carousel", "to": "brief", "relation": "contains"},
            {"from": "brief", "to": "guide", "relation": "follows"},
            {"from": "guide", "to": "carousel", "relation": "relates"},
        ],
    }))
    return home


class StubGraph(walks.Graph):
    """Non-WordNet provider, deliberately unlike the shipped providers."""
    name = "stub"
    relations = {"points": "lateral"}
    capabilities = {"resume", "gloss", "seeds"}
    size = {"nodes": 2, "edges": 1}

    def __init__(self, **_kwargs):
        self.rng = random.Random(1)
        self._nodes = {
            "a": self.node("a", "alpha", gloss="first"),
            "b": self.node("b", "beta", gloss="second"),
        }

    def resolve(self, term):
        return self._nodes.get(str(term).removeprefix("stub:"))

    def random_node(self, relation_roles=None):
        return self._nodes["a"] if not relation_roles or "lateral" in relation_roles else None

    def edges(self, node):
        return [("points", self._nodes["b"])] if node["id"] == "stub:a" else []

    def resume(self, node_id):
        return self.resolve(node_id)


@pytest.fixture(autouse=True)
def stub_provider():
    walks.register_graph("stub", StubGraph)
    try:
        yield
    finally:
        walks.unregister_graph("stub")


@pytest.mark.parametrize("provider, term, role", [
    ("wordnet", "walk", "general"),
    ("corpus", "carousel", "sequence"),
    ("stub", "a", "lateral"),
])
def test_provider_contract_over_wordnet_corpus_and_stub(provider, term, role, corpus):
    """Acceptance 1 / R1, R4, R6: the common contract is provider-neutral."""
    graph = walks.make_graph(provider, corpus_name="onboarding")
    assert graph.name == provider
    assert graph.relations and set(graph.relations.values()) <= walks.ROLE_VOCABULARY
    assert isinstance(graph.capabilities, set)
    node = graph.resolve(term)
    if node is None and provider == "wordnet":
        pytest.skip("wordnet corpus not installed")
    assert node and set(node) == {"id", "label", "pos", "gloss", "source", "licence"}
    assert node["id"].startswith(f"{provider}:")
    resumed = graph.resume(node["id"])
    assert resumed == node
    start = graph.random_node({role})
    assert start is not None
    usable = [(rel, other) for rel, other in graph.edges(start)
              if graph.relations[rel] == role]
    assert usable, (provider, start, graph.edges(start))
    if "far" in graph.capabilities:
        response = graph.far_from(node, samples=4, avoid=[])
        assert response is None or isinstance(response, dict)
    else:
        assert "far" not in graph.capabilities


def test_registry_validates_unknown_graph_and_save_capability(corpus, tmp_path):
    """Acceptance 1 and 3 / R1, R3: reject errors before a turn begins."""
    with pytest.raises(ValueError, match=r"unknown graph 'missing' \(known: .+\)"):
        walks.save({"name": "bad", "graph": "missing"}, tmp_path / "cursor.json")
    with pytest.raises(ValueError, match=r"graph 'corpus' cannot jump.*wander"):
        walks.save({"name": "jump", "graph": "corpus", "corpus": "onboarding", "jump": "vault"},
                   tmp_path / "cursor.json")
    saved = walks.save({"name": "near", "graph": "corpus", "corpus": "onboarding",
                        "roles": ["sequence"], "seed": {"mode": "fixed", "node": "carousel"}},
                       tmp_path / "cursor.json")
    assert saved["graph"] == "corpus"


def test_builtin_role_translation_matches_legacy_relations(tmp_path):
    """Acceptance 2 / R2: translation proves all nine policies, not visual inspection."""
    legacy = {
        "outer": (walks.ALL_RELATIONS, "far", "continue"),
        "wander": (walks.ALL_RELATIONS, None, "continue"),
        "upward": (["hypernym", "holonym"], None, "continue"),
        "downward": (["hyponym", "meronym"], None, "continue"),
        "composite": (walks.ALL_RELATIONS, "composite", "continue"),
        "vault": (walks.ALL_RELATIONS, "vault", "continue"),
        "run3": (walks.ALL_RELATIONS, "run:3", "continue"),
        "orbit": (walks.ALL_RELATIONS, "orbit", "continue"),
        "lateral": (["similar", "also", "antonym"], None, "continue"),
    }
    assert set(walks.BUILTIN) == set(legacy)
    for name, (relations, jump, seed) in legacy.items():
        walk = walks.GraphWalk({"name": name, **walks.BUILTIN[name]}, tmp_path / f"{name}.json")
        assert walk.relations == relations
        assert walk.jump == jump
        assert walk.seed_spec["mode"] == seed


def test_namespaced_ids_and_provenance_reach_journal_and_ledger(corpus, tmp_path):
    """Acceptance 5 and 6 / R1, R6: two carousel concepts remain distinct."""
    cwalk = walks.GraphWalk({"name": "corpus-hop", "graph": "corpus", "corpus": "onboarding",
                             "roles": ["sequence"], "seed": {"mode": "fixed", "node": "carousel"}},
                            tmp_path / "cursor.json")
    lines = cwalk.step(1)
    assert "corpus" in lines[0]
    cnode = cwalk.graph.resolve("carousel")
    assert cnode["id"] == "corpus:carousel"
    # ``step`` writes the landing through the same ledger path used by a live state.
    bnode = cwalk.graph.resolve("brief")
    assert bnode is not None
    assert bnode["id"] == "corpus:brief"
    wgraph = walks.WordNetGraph()
    wnode = wgraph.resolve("carousel")
    if wnode is None:
        pytest.skip("wordnet corpus not installed")
    assert wnode["id"] == "wordnet:carousel.n.01"
    assert wnode["id"] != cnode["id"]
    rows = history._query("SELECT kind, key, source, licence FROM concepts WHERE key=?", (bnode["id"],))
    assert rows == [("corpus", "corpus:brief", "Team handbook", "CC-BY-4.0")]


def test_deterministic_seed_replays_the_same_path(corpus, tmp_path, monkeypatch):
    """Acceptance 4 / R5: every choice is driven by ANTEMUSE_GRAPH_SEED."""
    spec = {"name": "seeded", "graph": "corpus", "corpus": "onboarding", "roles": ["sequence", "lateral"],
            "seed": {"mode": "random"}}
    monkeypatch.setenv("ANTEMUSE_GRAPH_SEED", "7")
    first = walks.GraphWalk(spec, tmp_path / "one.json").step(3)
    second = walks.GraphWalk(spec, tmp_path / "two.json").step(3)
    assert first == second


@pytest.mark.parametrize("mode, graph, setup, expected", [
    ("unavailable", "corpus", lambda home: None, "unavailable"),
    ("empty", "corpus", lambda home: (home / "graphs").mkdir(), "empty"),
    ("too_large", "corpus", lambda home: (home / "graphs").mkdir(), "too_large"),
    ("no_far", "corpus", lambda home: (home / "graphs").mkdir(), "no_far"),
])
def test_graph_failure_modes_are_named_and_never_raise(mode, graph, setup, expected, home, tmp_path):
    """Acceptance 7 / R9: each provider failure becomes a state-voice line."""
    setup(home)
    graphs = home / "graphs"
    if mode == "empty":
        (graphs / "empty.json").write_text(json.dumps({"name": "empty", "source": "x", "licence": "y", "nodes": {}, "edges": []}))
        spec = {"name": "empty", "graph": graph, "corpus": "empty"}
    elif mode == "too_large":
        nodes = {str(i): {} for i in range(walks.MAX_GRAPH_NODES + 1)}
        (graphs / "large.json").write_text(json.dumps({"name": "large", "source": "x", "licence": "y", "nodes": nodes, "edges": []}))
        spec = {"name": "large", "graph": graph, "corpus": "large"}
    elif mode == "no_far":
        (graphs / "near.json").write_text(json.dumps({"name": "near", "source": "x", "licence": "y", "nodes": {"a": {}, "b": {}}, "edges": [{"from": "a", "to": "b", "relation": "next"}]}))
        spec = {"name": "near", "graph": graph, "corpus": "near", "jump": "far"}
    else:
        spec = {"name": "missing", "graph": graph, "corpus": "missing"}
    walk = walks.GraphWalk(spec, tmp_path / f"{mode}.json")
    lines = walk.step(1)
    assert lines and expected in lines[0]


def test_entry_refuses_far_provider_in_state_voice(corpus, tmp_path):
    """Acceptance 3 / R3: no far policy silently becomes a near step."""
    walks.save({"name": "corpus-vault", "graph": "corpus", "corpus": "onboarding", "jump": "vault"},
               tmp_path / "walk_cursor.json", validate=False)
    message = walks.entry_error("corpus-vault", tmp_path / "walk_cursor.json")
    assert message == "graph 'corpus' cannot jump (no_far) · use wander or supply far_from"
