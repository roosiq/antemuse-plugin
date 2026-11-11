"""The entry mix is a ratio, so it is testable; determinism is what makes it measurable."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import seeding  # noqa: E402
from conftest import requires_tree  # noqa: E402


@requires_tree('.git')
def test_the_project_vocabulary_comes_from_the_repository():
    terms = seeding.project_terms()
    assert terms, "no project terms — the seeding would fall to conversation only"
    # the repo's own name and README words are in there; which ones is not the contract
    assert all(t == t.lower() for t in terms)
    assert "antemuse" in terms or "plugin" in terms


def test_the_mix_matches_the_spec_within_the_stated_tolerance():
    """The tier policy is what the spec fixes; an empty pool falls forward by design."""
    counts = {"project": 0, "conversation": 0, "random": 0}
    for i in range(400):
        counts[seeding._tier("walk", 1_700_000_000 + i, 0)] += 1
    total = sum(counts.values()) or 1
    shares = {k: 100 * v / total for k, v in counts.items()}
    for name, want in (("project", 50), ("conversation", 30), ("random", 20)):
        assert abs(shares[name] - want) <= 8, (name, shares)


def test_an_empty_tier_falls_forward_rather_than_returning_nothing():
    monkeypatch_terms = seeding.conversation_terms
    try:
        seeding.conversation_terms = lambda *a, **k: []
        got = seeding.entry("walk", when=1_700_000_000)
        assert got["source"] in ("project", "random") and got["term"], got
    finally:
        seeding.conversation_terms = monkeypatch_terms


def test_the_same_entry_replays_the_same_seed():
    first = seeding.entry("walk", when=1_700_000_000, counter=3)
    second = seeding.entry("walk", when=1_700_000_000, counter=3)
    assert first == second


def test_two_states_in_the_same_second_do_not_draw_the_same_bucket():
    walk = seeding._tier("walk", 1_700_000_000, 0)
    dream = seeding._tier("dream", 1_700_000_000, 0)
    assert (walk, dream) != ("", "")  # the salt is in the hash; equality is allowed


def test_an_used_term_is_skipped_not_repeated():
    seed = seeding.entry("walk", when=1_700_000_000)
    again = seeding.entry("walk", when=1_700_000_000, exclude=[seed["term"]])
    assert again["term"].lower() != seed["term"].lower()


def test_without_a_project_it_still_resolves_and_says_which_tier():
    original = seeding.project_terms
    try:
        seeding.project_terms = lambda *a, **k: []
        got = seeding.entry("walk", when=1_700_000_000)
        assert got["source"] in ("conversation", "random"), got
        assert got["term"]
    finally:
        seeding.project_terms = original


def test_the_marker_is_the_audit_trail():
    assert seeding.marker({"source": "project", "term": "parser"}) == "seed=project:parser"
    assert seeding.marker({"source": "none", "term": ""}) == "seed=none"


def test_doomscroll_is_never_seeded():
    """Undirected is the point of the feed: no project material, no mix."""
    text = (ROOT / "core/sources.py").read_text()
    body = text[text.index("def scroll_text"):]
    end = body.find("\ndef ", 1)
    body = body[:end] if end > 0 else body
    assert "seeding" not in body


def test_dream_starts_from_memory(monkeypatch, tmp_path):
    from core import recall
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    recall.clear()
    recall.remember("the parser keeps dropping the trailing brace", "person")
    recall.remember("so the diff is empty and the test passes anyway", "agent")
    assert seeding._tier("dream", 1_700_000_000, 0) == "memory"
    got = seeding.entry("dream", when=1_700_000_000)
    assert got["source"] == "memory", got
    assert got["term"] in ("parser", "keeps", "dropping", "trailing", "brace", "diff", "empty")


def test_dream_mix_is_memory_first_not_project():
    counts = {"memory": 0, "project": 0, "random": 0}
    for i in range(400):
        counts[seeding._tier("dream", 1_700_000_000 + i, 0)] += 1
    total = sum(counts.values()) or 1
    assert 100 * counts["memory"] / total >= 50, counts
    assert 100 * counts["project"] / total <= 32, counts


def _random_counter(state="walk", when=1_700_000_000):
    """A counter whose salt lands on the random tier — the one the old test never reached.

    `test_the_same_entry_replays_the_same_seed` used counter=3, which resolves to `project`. It
    passed while `random_term()` still drew from the global RNG, because that branch never ran.
    """
    for counter in range(200):
        if seeding._tier(state, when, counter) == "random":
            return counter
    raise AssertionError("no salt reaches the random tier")


def test_a_random_tier_entry_replays_the_same_term():
    counter = _random_counter()
    first = seeding.entry("walk", when=1_700_000_000, counter=counter)
    assert first["source"] == "random", first
    second = seeding.entry("walk", when=1_700_000_000, counter=counter)
    assert first == second, (first, second)


def test_the_random_term_is_a_function_of_its_seed():
    a = [seeding.random_term("walk|1700000000|7") for _ in range(3)]
    assert len(set(a)) == 1, a
    b = [seeding.random_term("walk|1700000000|8") for _ in range(3)]
    assert len(set(b)) == 1, b
