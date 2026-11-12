"""Sources are real corpora, and say so when they are not there."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))

from core import sources  # noqa: E402


def _has(corpus: str) -> bool:
    try:
        if corpus == "wordnet":
            return bool(sources._wn().synsets("walk"))
        return bool(sources._frames())
    except Exception:
        return False


def test_walk_steps_use_named_relations(tmp_path, monkeypatch):
    if not _has("wordnet"):
        pytest.skip("wordnet corpus not installed")
    monkeypatch.setattr(sources, "WALK_CURSOR", tmp_path / "cursor.json")
    steps = sources.walk_step(3)
    assert steps and len(steps) <= 3
    for line in steps:
        assert "→" in line
        assert any(rel in line for rel in ("hypernym", "hyponym", "holonym", "meronym",
                                           "similar", "also", "antonym"))
    # the walk continues from where it ended
    assert sources.cursor()


def test_walk_survives_a_broken_cursor(tmp_path, monkeypatch):
    if not _has("wordnet"):
        pytest.skip("wordnet corpus not installed")
    cursor = tmp_path / "cursor.json"
    cursor.write_text('{"synset": "not.a.synset"}')
    monkeypatch.setattr(sources, "WALK_CURSOR", cursor)
    assert sources.walk_step(1)


def test_dream_recombines_frames():
    if not _has("framenet"):
        pytest.skip("framenet corpus not installed")
    lines = sources.dream_recombine(3)
    assert len(lines) == 3
    # a memory seed may prefix the first line now that the seed path reads lexical units
    assert all("invented · " in l for l in lines), lines
    assert len({l for l in lines}) >= 2


def test_memory_pairs_report_the_join():
    lines = sources.memory_pairs(2)
    assert lines
    assert all(l.startswith(("JOINED", "adjacent", "no memories")) for l in lines)


def test_providers_cover_every_state():
    from core import states
    assert set(sources.PROVIDERS) == set(states.STATES)


# ------------------------------------------------------- which projects a dream may read

def test_a_dream_reads_the_project_you_are_in(monkeypatch, tmp_path):
    """No list of somebody's repositories is baked into the source.

    Empty `dream_projects` means the repository the working directory belongs to, found by
    walking up from a subdirectory so a dream read from inside a checkout still sees it.
    """
    from core import settings, sources

    repo = tmp_path / "proj"
    (repo / ".git").mkdir(parents=True)
    deep = repo / "src" / "inner"
    deep.mkdir(parents=True)
    monkeypatch.chdir(deep)
    settings.override(dream_projects="")
    try:
        assert sources.projects() == [repo.resolve()]
    finally:
        settings.clear_overrides()


def test_a_dream_reads_the_projects_the_person_names(monkeypatch, tmp_path):
    from core import settings, sources

    a, b = tmp_path / "alpha", tmp_path / "beta"
    (a / ".git").mkdir(parents=True)
    (b / ".git").mkdir(parents=True)
    settings.override(dream_projects=f"{a}, {b}\n{a}")
    try:
        assert sources.projects() == [a.resolve(), b.resolve()]
    finally:
        settings.clear_overrides()


def test_the_source_carries_no_hardcoded_project_names():
    from core import sources

    text = open(sources.__file__).read()
    assert "concept.cooking" not in text and "slopslingers-infra" not in text
    assert "brand-agents" not in text and "toslop-model" not in text
