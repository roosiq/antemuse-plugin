"""Two states were failing their own goals for mechanical reasons; these pin the fixes."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import sources  # noqa: E402


# ------------------------------------------------------------------ daydream


def _pool(monkeypatch, items):
    monkeypatch.setattr(sources, "memory_pool", lambda: list(items))


def test_a_join_rests_on_distinctive_terms_not_on_the_projects_own_boilerplate(monkeypatch):
    pool = ["the plugin state machine is slow", "the plugin state machine is fine",
            "the plugin state machine again", "the plugin state machine today",
            "sawhorse carving in the alps", "sawhorse carving with an axe"]
    _pool(monkeypatch, pool)
    joined = [l for l in sources.memory_pairs(3) if l.startswith("JOINED")]
    assert joined, "two sawhorse memories share distinctive words and must join"
    assert "sawhorse" in joined[0] or "carving" in joined[0], joined[0]
    assert not any("plugin state machine" in l for l in joined), joined


def test_the_pool_comes_from_the_whole_ring_not_the_last_six():
    assert "recall.CAP" in open(os.path.join(ROOT, "core", "sources.py")).read()


def test_when_nothing_holds_the_state_says_how_many_pairs_it_looked_at(monkeypatch):
    _pool(monkeypatch, ["alpha one", "beta two", "gamma three", "delta four"])
    lines = sources.memory_pairs(1)
    assert lines[0].startswith("adjacent"), lines
    assert "best of 6 pairs" in lines[0], lines[0]


def test_the_threshold_was_not_lowered(monkeypatch):
    """Two memories with nothing in common must still be reported as adjacent."""
    _pool(monkeypatch, ["alpha one", "zebra nine"])
    line = sources.memory_pairs(1)[0]
    assert line.startswith("adjacent") and "needs 2" in line, line


# --------------------------------------------------------------------- dream


def test_a_recombination_crosses_two_frames_and_names_both():
    line = sources.dream_recombine(1)[0]
    assert "[" in line and "×" in line, line
    a, b = line.split("[")[-1].rstrip("]").split(" × ")
    assert a != b, line


def test_lexical_units_are_read_from_the_frame_instead_of_falling_back():
    frames = sources._frames()
    words = sources._frame_words(frames[0])
    assert words, "a frame must yield lexical units"
    assert all("." not in w for w in words), words       # `abandon.v` -> `abandon`
    assert not all(w == "thing" for w in words)


def test_a_recombination_uses_real_words_not_placeholders():
    for line in sources.dream_recombine(6):
        assert "thing thing" not in line
        assert " {a}" not in line and "{b}" not in line, line


def test_dream_can_start_from_a_memory():
    """The seed path read `lexical_units`, which NLTK raises KeyError for — silently."""
    text = open(os.path.join(ROOT, "core", "sources.py")).read()
    assert 'getattr(candidate, "lexical_units"' not in text
    assert "frame.get(\"lexUnit\")" in text
