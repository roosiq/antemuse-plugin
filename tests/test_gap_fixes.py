"""The three gaps the review found: dream's empty day, walk's repeats, unstuck's quotes."""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))

from core import history, sources, walks  # noqa: E402


def _has(wordnet: str = "wordnet") -> bool:
    try:
        sources._wn()
        return True
    except Exception:
        return False


# ------------------------------------------------------------------- dream

def test_a_day_with_two_projects_makes_a_connection_naming_both_sides(monkeypatch):
    terms = {
        "antemuse": {"subjects": ["docs: the states do the moves now"],
                     "files": ["core/states.py"], "words": {"states", "moves", "workshop"}},
        "ryancook.name": {"subjects": ["agents: refresh workshop snapshot"],
                          "files": ["workshop.py"], "words": {"workshop", "snapshot", "agents"}},
    }
    monkeypatch.setattr(sources, "_day_window", lambda hours: (terms, 24))
    lines = sources.day_connections(1)
    assert lines and lines[0].startswith("connection ·"), lines
    assert "antemuse" in lines[0] and "ryancook.name" in lines[0]
    assert "window:" not in lines[0], "a real day must not be reported as a wide window"


def test_a_thin_day_looks_further_back_and_says_which_window(monkeypatch):
    terms = {
        "antemuse": {"subjects": ["docs: states"], "files": [], "words": {"states", "specs"}},
        "antemuse-plugin": {"subjects": ["repair the spec"], "files": [], "words": {"specs", "repair"}},
    }
    monkeypatch.setattr(sources, "_day_window", lambda hours: (terms, 168))
    line = sources.day_connections(1)[0]
    assert line.startswith("connection ·")
    assert "window: 7 days" in line, line


def test_one_project_still_joins_two_of_its_own_pieces(monkeypatch):
    """A dream over a single project is a dream over two of its pieces, not a refusal.

    The old build answered "no connection today · only 1 project", which is the state
    declaring it cannot do the one thing it was entered to do.
    """
    terms = {"antemuse": {"subjects": ["ship the walk pane", "ship the dream pane"],
                          "files": [], "words": {"ship", "pane", "walk", "dream"}}}
    monkeypatch.setattr(sources, "_day_window", lambda hours: (terms, 168))
    line = sources.day_connections(1)[0]
    assert line.startswith("connection · antemuse:"), line
    assert "↔" in line, line
    assert "no connection" not in line, line


# -------------------------------------------------------------------- walk

def test_a_walk_still_delivers_when_every_concept_is_known(tmp_path, monkeypatch):
    if not _has():
        pytest.skip("wordnet not installed")
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    monkeypatch.setattr(history, "known", lambda term, exclude_session="": True)
    spec = dict(walks.BUILTIN["outer"], name="outer")
    lines = walks.GraphWalk(spec, tmp_path / "c.json").step(3)
    assert len(lines) == 3, "a known graph must not stall the walk"
    assert all("→" in line for line in lines)


def test_the_ledger_steers_the_walk_away_from_a_known_concept(tmp_path, monkeypatch):
    """When one neighbour is known and the rest are not, the known one is not chosen."""
    if not _has():
        pytest.skip("wordnet not installed")
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    known = {"agent"}
    monkeypatch.setattr(history, "known",
                        lambda term, exclude_session="": term.lower() in known)
    spec = dict(walks.BUILTIN["wander"], name="wander")
    destinations = []
    for i in range(12):
        lines = walks.GraphWalk(spec, tmp_path / f"w{i}.json").step(2)
        for line in lines:
            destinations.append(line.split("·")[0].split("→")[-1].split("(")[0].strip().lower())
    repeats = [d for d in destinations if d in known]
    assert len(repeats) <= len(destinations) // 4, repeats


# ----------------------------------------------------------------- unstuck

def test_a_quote_is_cut_at_a_word_boundary():
    text = "docs: the states do the moves now, so the spec says so"
    clipped = sources._clip(text, 40)
    assert clipped.endswith("…")
    body = clipped.rstrip("…")
    assert text.startswith(body), "a clip must not rewrite the words"
    assert not body.endswith("says s"), "a clip must not end mid-word"
    assert text[len(body)] in (" ",), clipped


def test_a_short_dictionary_noun_is_not_a_recommendation(tmp_path, monkeypatch):
    """Old ledger rows hold words like 'drops'; they are not concepts to build on."""
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    history.notice("drops", move="session", session="old")
    history.notice("shipper", move="session", session="old")
    unused = history.unused(days=7)
    assert "shipper" in unused, unused
    assert "drops" not in unused, unused
