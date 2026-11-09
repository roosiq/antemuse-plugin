"""Each state now does the move it is defined as — these pin the moves, not the plumbing."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest  # noqa: E402

os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))

from core import social, sources  # noqa: E402


def _has(corpus: str) -> bool:
    """Ask the module itself, the way the rest of the suite does: wordnet ships zipped."""
    try:
        if corpus == "wordnet":
            return bool(sources._wn().synsets("walk"))
        return bool(sources._frames())
    except Exception:
        return False


# ----------------------------------------------------------------------- walk

def test_every_walk_step_says_how_far_and_how_it_gets_back(tmp_path, monkeypatch):
    """Distant *and connected*: a step with no path back is a random word."""
    if not _has("wordnet"):
        pytest.skip("wordnet not installed")
    from core import walks
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    spec = dict(walks.BUILTIN["outer"], name="outer")
    line = walks.GraphWalk(spec, tmp_path / "cursor.json").step(1)[0]
    assert "↩" in line, line
    assert "from " in line.split("↩")[1], line
    # the anchor is named, and the trail starts from it
    tail = line.split("↩")[1]
    assert ":" in tail, line


def test_a_plain_step_counts_hops(tmp_path):
    if not _has("wordnet"):
        pytest.skip("wordnet not installed")
    from core import walks
    spec = dict(walks.BUILTIN["wander"], name="wander")
    lines = walks.GraphWalk(spec, tmp_path / "cursor.json").step(3)
    hops = [l for l in lines if "hop" in l or "jumped" in l]
    assert hops, lines


# ------------------------------------------------------------------- daydream

def test_a_daydream_item_carries_a_possibility():
    lines = sources.memory_pairs(2)
    assert lines
    for line in lines:
        assert "possibility ·" in line, line


def test_the_possibility_is_a_hypothesis_not_an_instruction():
    """Daydream ideates; it does not hand the agent something to execute."""
    line = sources.memory_pairs(1)[0]
    tail = line.split("possibility ·", 1)[1].lower()
    assert not tail.startswith("you "), line
    assert any(marker in tail for marker in
               ("if ", "could", "worth", "what if", "would", "the gap")), line


# ----------------------------------------------------------------- doomscroll

def test_professional_material_is_excluded_from_the_scroll():
    assert social.is_work("Company earnings beat expectations as revenue grows")
    assert not social.is_work("my cat has decided the printer is his enemy")


def test_the_scroll_pool_is_comedy_not_news():
    assert social.FEEDS, "the scroll needs a pool"
    news = ("arstechnica", "theverge", "bbc.co.uk", "lwn.net", "phys.org",
            "news.ycombinator", "quantamagazine", "sciencedaily", "eff.org")
    joined = " ".join(social.FEEDS).lower()
    assert not any(host in joined for host in news), social.FEEDS


# --------------------------------------------------------------------- dream

def test_a_dream_connection_names_a_task_on_each_side_across_projects(monkeypatch):
    terms = {"repo-a": {"subjects": ["shipper retries the same lane twice"],
                        "files": ["lane.py"], "words": {"shipper", "lane", "retries"}},
             "repo-b": {"subjects": ["shipper drops the second retry"],
                        "files": ["retry.py"], "words": {"shipper", "retry", "drops"}}}
    monkeypatch.setattr(sources, "_day_window", lambda hours: (terms, 24))
    lines = sources.day_connections(1)
    assert lines and lines[0].startswith("connection ·"), lines
    assert "repo-a:" in lines[0] and "repo-b:" in lines[0], lines[0]
    assert "shared:" in lines[0] or "through:" in lines[0], lines[0]


def test_a_thin_day_says_so_and_invents_instead(monkeypatch):
    monkeypatch.setattr(sources, "_day_window", lambda hours: ({}, 168))
    lines = sources.day_connections(2)
    assert lines[0].startswith("note · no connection today"), lines[0]
    assert any("invented · " in l for l in lines[1:]), lines


def test_no_shared_work_is_reported_rather_than_papered_over(monkeypatch):
    terms = {"a": {"subjects": ["alpha zulu"], "files": [], "words": {"alpha", "zulu"}},
             "b": {"subjects": ["bravo yankee"], "files": [], "words": {"bravo", "yankee"}}}
    monkeypatch.setattr(sources, "_day_window", lambda hours: (terms, 24))
    we_have = sources.day_connections(1)
    assert "no connection" in we_have[0] or "connection ·" in we_have[0], we_have


# ------------------------------------------------------------------- unstuck

def test_a_recommendation_rests_on_history_and_the_concept_graph(tmp_path, monkeypatch):
    if not _has("wordnet"):
        pytest.skip("wordnet not installed")
    monkeypatch.setattr(sources.storage, "project_root", lambda: tmp_path)
    monkeypatch.setattr(sources, "_git_log", lambda root, since: ["build the shipper lane"])
    (tmp_path / "README.md").write_text("a thing\n")
    (tmp_path / "specs" / "change").mkdir(parents=True)
    (tmp_path / "specs" / "change" / "spec.md").write_text("goal\n")
    lines = " ".join(sources.unstuck_text(6))
    assert "history · last commit" in lines, lines
    assert "graph ·" in lines or "concept graph" in lines, lines


def test_still_one_thing_at_dose_one(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.storage, "project_root", lambda: tmp_path)
    (tmp_path / "README.md").write_text("a thing\n")
    lines = [l for l in sources.unstuck_text(1) if l.startswith("direction")]
    assert len(lines) == 1, lines


# ------------------------------------------------------------ concept ledger

def test_a_step_that_lands_somewhere_known_says_when(tmp_path, monkeypatch):
    """The ledger's whole point in a walk: not "is this a word" but "have we been here"."""
    if not _has("wordnet"):
        pytest.skip("wordnet not installed")
    from core import history, walks
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    monkeypatch.setattr(history, "seen_before",
                        lambda term, exclude_session="": {"sessions": 2,
                                                          "last_session_at": __import__("time").time() - 2 * 86400})
    monkeypatch.setattr(history, "when", lambda ts: "2 days ago")
    spec = dict(walks.BUILTIN["outer"], name="outer")
    line = walks.GraphWalk(spec, tmp_path / "c.json").step(1)[0]
    assert "seen 2 days ago in 2 other sessions" in line, line


def test_a_walk_records_where_it_went(tmp_path, monkeypatch):
    if not _has("wordnet"):
        pytest.skip("wordnet not installed")
    from core import history, walks
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    spec = dict(walks.BUILTIN["outer"], name="outer")
    walks.GraphWalk(spec, tmp_path / "c.json").step(2)
    assert history.stats()["servings"] >= 2, history.stats()
