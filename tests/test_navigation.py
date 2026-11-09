"""Going further out, drawing from a wider pool, and asking memory for a direction."""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import social, sources, walks  # noqa: E402


# --------------------------------------------------------------- navigation


def _walk(name, tmp_path):
    return walks.get(name, tmp_path / "cursors.json")


def test_vault_jumps_twice_and_says_how_far_it_went(tmp_path):
    lines = _walk("vault", tmp_path).step(3)
    assert lines and all("vaulted past" in l for l in lines), lines


def test_run3_reports_one_arc_not_one_edge(tmp_path):
    """A fixed graph, so the assertion is about the policy and not about WordNet's shape."""
    spec = {"name": "chain", "graph": "manual", "jump": "run:3",
            "relations": ["next"], "avoid_backtrack": True,
            "edges": {"a": ["b", "c"], "b": ["c"], "c": ["d"], "d": ["a"]}}
    lines = walks.GraphWalk(spec, tmp_path / "cursors.json").step(1)
    assert lines and " ran " in lines[0], lines
    assert lines[0].count("→") >= 2, lines[0]


def test_orbit_alternates_near_and_far(tmp_path):
    lines = _walk("orbit", tmp_path).step(4)
    far = [l for l in lines if "far edge" in l]
    assert far, lines


def test_composite_walk_uses_every_navigation_in_one_walk(tmp_path):
    # twelve steps, because a stub synset can still degrade one arc even after the retry;
    # the assertion is about the policy rotation, not about one unlucky node
    lines = _walk("composite", tmp_path).step(12)
    joined = " | ".join(lines)
    assert " ran " in joined, lines          # run:3
    assert "far edge" in joined, lines       # far / orbit
    assert "vaulted past" in joined, lines   # vault
    assert any("took its" in l for l in lines), lines   # a plain adjacent step


def test_composite_reports_which_navigation_each_step_took(tmp_path):
    w = _walk("composite", tmp_path)
    assert len(w.rotation) >= 4
    assert w.rotation[0] == "run:3" and "vault" in w.rotation


def test_outer_can_look_wider_than_the_default_sample(tmp_path):
    w = _walk("outer", tmp_path)
    assert w.samples == 32            # declared by the walk, not hard-coded in the graph
    assert _walk("vault", tmp_path).samples == 64


def test_a_named_walk_is_available_without_being_the_active_one(tmp_path):
    for name in ("wander", "outer", "vault", "run3", "orbit", "upward", "downward", "lateral"):
        assert _walk(name, tmp_path).step(1)


# ------------------------------------------------------------------- feeds


def _fake_fetch(monkeypatch, items):
    monkeypatch.setattr(social, "fetch_all",
                        lambda: {"at": time.time(), "items": items, "failed": []})
    monkeypatch.setattr(social, "CACHE", social.storage.data_dir() / "social-test.json")
    try:
        social.CACHE.unlink()
    except OSError:
        pass


def test_a_scroll_does_not_repeat_what_it_already_served(monkeypatch):
    items = [{"source": "hn", "author": "a", "text": f"story {i}",
              "url": f"https://example.com/{i}"} for i in range(6)]
    _fake_fetch(monkeypatch, items)
    first = social.pick(3)
    second = social.pick(3)
    assert not set(first) & set(second), (first, second)


def test_when_the_pool_runs_dry_it_refetches_rather_than_repeating(monkeypatch):
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return {"at": time.time(), "failed": [],
                "items": [{"source": "hn", "author": "a", "text": f"gen{calls['n']}-{i}",
                           "url": f"https://example.com/{calls['n']}/{i}"} for i in range(2)]}

    monkeypatch.setattr(social, "fetch_all", fetch)
    monkeypatch.setattr(social, "CACHE", social.storage.data_dir() / "social-test.json")
    try:
        social.CACHE.unlink()
    except OSError:
        pass
    first = social.pick(2)
    second = social.pick(2)
    assert calls["n"] >= 2, "a dose the cache cannot fill must refetch"
    assert not set(first) & set(second)


def test_sources_are_a_pool_not_a_fixed_pair():
    # the goal is distraction via comedy, so the pool is satire lanes and nothing else
    assert len(social.FEEDS) >= 5
    assert list(social.FETCHERS) == ["satire"], social.FETCHERS
    assert len(set(social.FEEDS)) == len(social.FEEDS), "no lane listed twice"


# ----------------------------------------------------------------- unstuck


def test_a_direction_carries_its_evidence_and_a_first_move(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.storage, "project_root", lambda: tmp_path)
    lines = sources.unstuck_text(2)
    directions = [l for l in lines if l.startswith("direction ")]
    assert directions, lines
    for line in directions:
        assert " · because " in line and " · first: " in line, line


def test_the_dose_changes_how_many_directions_are_offered(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.storage, "project_root", lambda: tmp_path)
    one = [l for l in sources.unstuck_text(1) if l.startswith("direction ")]
    two = [l for l in sources.unstuck_text(2) if l.startswith("direction ")]
    assert len(two) >= len(one) >= 1


def test_zero_dose_offers_no_direction(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.storage, "project_root", lambda: tmp_path)
    lines = sources.unstuck_text(0)
    assert not [l for l in lines if l.startswith("direction ")]


def test_memory_is_an_input_and_its_absence_is_named(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.storage, "project_root", lambda: tmp_path)
    monkeypatch.setattr(sources, "memory_pool", lambda: [])
    # the missing inputs are listed together now (history, graph, memory), so the
    # assertion is about memory being named, not about it being first
    assert any(l.startswith("missing input") and "memory" in l
               for l in sources.unstuck_text(2))

    monkeypatch.setattr(sources, "memory_pool", lambda: ["the tile renderer kept stalling"])
    lines = sources.unstuck_text(6)
    assert any("from memory" in l for l in lines), lines
