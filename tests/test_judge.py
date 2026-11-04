"""Judge behaviour: the game must be fair, deterministic, and not gameable by length."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kitchen import judge  # noqa: E402


def ctx(seed="a plugin that refuses to answer until it has asked one better question",
        move="flip", prior=None, hint=False):
    return {"seed": seed, "move": move, "prior": prior or [], "hint": hint, "word_budget": 60}


def test_strong_flip_scores_high():
    sub = {
        "title": "Answer only in questions until the problem is specific",
        "why": "Instead of assuming the user already knows what they want, the plugin reverses the default: it withholds output until one vague term has been made concrete, because the follow-up is the product.",
        "try_next": "Write one follow-up question for the next three requests and count how often it changes the answer.",
    }
    result = judge.score(sub, ctx())
    assert result["axes"]["move_discipline"] >= 18
    assert result["axes"]["mechanism"] >= 15
    assert result["axes"]["actionability"] >= 20
    assert result["total"] >= 72, result


def test_generic_advice_is_undercooked():
    sub = {
        "title": "Make it better and more engaging",
        "why": "It could potentially create synergy across the ecosystem.",
        "try_next": "Explore possibilities.",
    }
    result = judge.score(sub, ctx())
    assert result["total"] < 40, result
    assert any("slop" in p["reason"] for p in result["penalties"])


def test_one_dimension_beats_three():
    one = judge.score({
        "title": "Ship the empty version",
        "why": "Instead of assuming a launch needs features, reverse the success condition: the release is done when it does nothing yet.",
        "try_next": "Publish one page with a single button by Friday.",
    }, ctx())
    three = judge.score({
        "title": "Ship the empty version to a new actor at planetary scale",
        "why": "Instead of assuming a launch needs features, reverse the success condition, change the role and change the setting all at once.",
        "try_next": "Publish one page with a single button by Friday.",
    }, ctx())
    assert one["axes"]["move_discipline"] > three["axes"]["move_discipline"]
    assert any("three or more" in p["reason"] for p in three["penalties"])


def test_derivative_spark_scores_zero_novelty():
    prior = ["Answer only in questions until the problem is specific — Instead of assuming the user already knows what they want."]
    result = judge.score({
        "title": "Answer only in questions until the problem is specific",
        "why": "Instead of assuming the user already knows what they want, it withholds output until one vague term is concrete.",
        "try_next": "Write one follow-up question by Friday.",
    }, ctx(prior=prior))
    assert result["axes"]["novelty"] == 0
    assert result["total"] < 75


def test_connect_needs_source_and_mechanism():
    good = judge.score({
        "title": "Triage incoming requests like a hospital",
        "why": "Borrowed from how an emergency department routes patients by severity, the queue sorts new work by reversibility rather than by who asked.",
        "try_next": "Sort the next ten requests by how hard they are to undo.",
    }, ctx(move="connect"))
    bad = judge.score({
        "title": "Hospitals",
        "why": "Hospitals are interesting and relevant.",
        "try_next": "Sort ten requests.",
    }, ctx(move="connect"))
    assert good["axes"]["move_discipline"] == 25
    assert bad["axes"]["move_discipline"] == 0


def test_hint_costs_points():
    sub = {
        "title": "Ship the empty version",
        "why": "Instead of assuming a launch needs features, reverse the success condition.",
        "try_next": "Publish one page by Friday.",
    }
    plain = judge.score(sub, ctx())
    hinted = judge.score(sub, ctx(hint=True))
    assert hinted["total"] == plain["total"] - 8


def test_far_without_bridge_is_penalised():
    sub = {
        "title": "Borrow the migratory pattern of arctic terns",
        "why": "It is different and fresh.",
        "try_next": "Write one note by Friday.",
    }
    result = judge.score(sub, ctx(move="connect"))
    assert "unbridged" in " ".join(result["notes"]) or result["total"] < 60


def test_try_next_with_a_label_still_opens_with_a_verb():
    from kitchen import game
    parts = game._split(
        "Title: Charge for the second thought :: Why: the follow-up is the paid thought. :: "
        "Try next: add one line to the price page by Friday."
    )
    assert parts is not None
    title, why, nxt = parts
    assert title == "Charge for the second thought"
    assert why.startswith("the follow-up")
    result = judge.score({"title": title, "why": why, "try_next": nxt}, ctx())
    assert result["axes"]["actionability"] == 25, result
