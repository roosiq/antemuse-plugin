"""Distance/diversity and blind-judge tests on tiny known fixtures.

Every fixture here is arithmetic, not evidence.  A pass says the functions
compute what they claim; it says nothing about any real condition's creativity
or about significance.
"""
from __future__ import annotations

import json
import math

import pytest

from . import load

judges = load("judges")
metrics = load("metrics")


# --------------------------------------------------------------- cosine distance

def test_identical_vectors_have_zero_distance():
    assert metrics.cosine_distance([1, 0], [1, 0]) == 0.0
    assert metrics.cosine_distance([3, 4], [3, 4]) == pytest.approx(0.0, abs=1e-12)


def test_orthogonal_vectors_have_distance_one():
    assert metrics.cosine_distance([1, 0], [0, 1]) == pytest.approx(1.0)


def test_opposite_vectors_have_distance_two():
    assert metrics.cosine_distance([1, 0], [-1, 0]) == pytest.approx(2.0)


def test_cosine_distance_matches_the_definition():
    a, b = [1.0, 2.0, 3.0], [4.0, 5.0, 6.0]
    dot = sum(x * y for x, y in zip(a, b))
    expected = 1.0 - dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))
    assert metrics.cosine_distance(a, b) == pytest.approx(expected, rel=1e-12)


def test_zero_vector_is_an_error_not_a_distance():
    with pytest.raises(ValueError, match="zero vector"):
        metrics.cosine_distance([0, 0], [1, 0])
    with pytest.raises(ValueError, match="zero vector"):
        metrics.cosine_distance([1, 0], [0.0, 0.0])


@pytest.mark.parametrize("bad", [
    [],
    [1.0],
    [1, 2, 3, 4],
    [1, float("nan")],
    [1, float("inf")],
    [1, float("-inf")],
    [1, True],
    [1, "2"],
    [1, None],
    "not a vector",
    None,
])
def test_cosine_distance_rejects_invalid_numbers(bad):
    with pytest.raises(ValueError):
        metrics.cosine_distance(bad, [1, 2, 3])


def test_cosine_distance_requires_rectangular_input():
    with pytest.raises(ValueError, match="lengths differ"):
        metrics.cosine_distance([1, 2], [1, 2, 3])


# ----------------------------------------------------------- pairwise distances

def test_pairwise_distances_returns_only_the_upper_triangle():
    vectors = [[1, 0], [0, 1], [-1, 0]]
    expected = [
        (0, 1, metrics.cosine_distance(vectors[0], vectors[1])),
        (0, 2, metrics.cosine_distance(vectors[0], vectors[2])),
        (1, 2, metrics.cosine_distance(vectors[1], vectors[2])),
    ]
    assert metrics.pairwise_distances(vectors) == expected


def test_pairwise_distances_has_n_choose_2_pairs_and_no_diagonal():
    vectors = [[1, 0], [0, 1], [-1, 0], [1, 1]]
    pairs = metrics.pairwise_distances(vectors)
    assert len(pairs) == 6
    assert all(i < j for i, j, _ in pairs)
    assert all(distance >= 0.0 for _, _, distance in pairs)
    assert all(0 <= i < len(vectors) and 0 <= j < len(vectors) for i, j, _ in pairs)


def test_pairwise_distances_of_empty_pool_is_empty():
    assert metrics.pairwise_distances([]) == []
    assert metrics.pairwise_distances([[1, 0]]) == []


def test_pairwise_distances_rejects_ragged_pools():
    with pytest.raises(ValueError, match="not rectangular"):
        metrics.pairwise_distances([[1, 0], [1, 0, 0]])


def test_pairwise_distances_rejects_zero_vector_member():
    with pytest.raises(ValueError, match="zero vector"):
        metrics.pairwise_distances([[1, 0], [0, 0]])


# ---------------------------------------------------------------- pool diversity

def test_pool_diversity_is_the_mean_pairwise_distance():
    # Distances 1, 2, 1 -> mean 4/3.
    assert metrics.pool_diversity([[1, 0], [0, 1], [-1, 0]]) == pytest.approx(4.0 / 3.0)


def test_pool_diversity_of_fewer_than_two_is_zero():
    assert metrics.pool_diversity([]) == 0.0
    assert metrics.pool_diversity([[1, 0]]) == 0.0


def test_pool_diversity_rejects_invalid_vectors():
    with pytest.raises(ValueError):
        metrics.pool_diversity([[1, 0], [0, float("nan")]])


# ------------------------------------------------------------- baseline novelty

def test_novelty_is_mean_nearest_baseline_distance():
    # Candidates (1,0) and (0,1) against baseline (1,0): distances 0 and 1 -> 0.5.
    assert metrics.novelty_against_baseline(
        [[1, 0], [0, 1]], [[1, 0]]) == pytest.approx(0.5)


def test_novelty_uses_the_nearest_of_several_baselines():
    # Nearest baseline to (1,0) is (1,0), not the orthogonal (0,1).
    assert metrics.novelty_against_baseline(
        [[1, 0]], [[0, 1], [1, 0]]) == pytest.approx(0.0)


def test_novelty_requires_a_nonempty_baseline():
    with pytest.raises(ValueError, match="baseline_vectors must be non-empty"):
        metrics.novelty_against_baseline([[1, 0]], [])


def test_novelty_requires_nonempty_candidates():
    with pytest.raises(ValueError, match="candidate_vectors must be non-empty"):
        metrics.novelty_against_baseline([], [[1, 0]])


def test_novelty_rejects_dimension_mismatch():
    with pytest.raises(ValueError, match="share a dimension"):
        metrics.novelty_against_baseline([[1, 0, 0]], [[1, 0]])


# --------------------------------------------------------- structural diversity

def test_structural_diversity_is_mean_jaccard_distance():
    # {m,r} vs {m}: 1 - 1/2 = 0.5.
    assert metrics.structural_diversity([{"metaphor", "rhyme"}, {"metaphor"}]) == pytest.approx(0.5)


def test_structural_diversity_averages_over_all_pairs():
    tag_sets = [{"metaphor", "rhyme"}, {"metaphor"}, {"rhyme"}]
    # .5, .5, 1.0 -> 2/3.
    assert metrics.structural_diversity(tag_sets) == pytest.approx(2.0 / 3.0)


def test_structural_diversity_of_fewer_than_two_is_zero():
    assert metrics.structural_diversity([]) == 0.0
    assert metrics.structural_diversity([{"metaphor"}]) == 0.0


def test_structural_diversity_handles_empty_tag_sets():
    assert metrics.structural_diversity([set(), set()]) == 0.0
    assert metrics.structural_diversity([set(), {"walk"}]) == pytest.approx(1.0)


def test_structure_and_geometry_are_independent_measures():
    # Same declared mechanism, different vectors: structural distance 0,
    # pool distance positive.  The two numbers answer different questions.
    tags = [{"graph_step", "corpus:wordnet"}, {"graph_step", "corpus:wordnet"}]
    vectors = [[1, 0], [0, 1]]
    assert metrics.structural_diversity(tags) == 0.0
    assert metrics.pool_diversity(vectors) > 0.0

    # Same vectors, different declared mechanism: geometry 0, structure positive.
    assert metrics.pool_diversity([[1, 0], [1, 0]]) == 0.0
    assert metrics.structural_diversity([{"graph_step"}, {"corpus:wordnet"}]) > 0.0


def test_structural_diversity_never_reads_text():
    # There is no text parameter and no lexical inference hook: tags must be
    # supplied explicitly.  Identical tag sets stay identical even when the
    # records' wording would differ.
    assert metrics.structural_diversity([{"a"}, {"a"}]) == 0.0
    assert not hasattr(metrics, "infer_tags")
    assert not hasattr(metrics, "tags_from_text")


@pytest.mark.parametrize("bad", [
    "metaphor",                     # a bare string is not a tag set
    [{"ok"}, "rhyme"],              # bare string inside
    [{"ok"}, {"bad", ""}],          # empty tag
    [{"ok"}, {"bad", 3}],           # non-string tag
    [{"ok"}, None],
    None,
])
def test_structural_diversity_rejects_implicit_or_invalid_tags(bad):
    with pytest.raises(ValueError):
        metrics.structural_diversity(bad)


def test_metrics_document_what_they_do_not_measure():
    described = metrics.describe()
    assert "quality" in described["does_not_measure"]
    assert "explicit mechanism tags" in described["structure"]


# ------------------------------------------------------------- judge records

def verdict(**overrides):
    fields = {
        "task_id": "t1",
        "left_condition": "baseline-verbose",
        "right_condition": "treatment-lexical",
        "winner": "left",
        "axis": "quality",
        "judge_id": "j1",
    }
    fields.update(overrides)
    return judges.PairwiseVerdict(**fields)


def test_verdict_accepts_the_three_winners_and_optional_pair_id():
    assert verdict(winner="left").winner == "left"
    assert verdict(winner="right").winner == "right"
    assert verdict(winner="tie").winner == "tie"
    assert verdict(blind_pair_id="pair-abc").blind_pair_id == "pair-abc"
    assert verdict(winner="tie").to_dict()["winner"] == "tie"


@pytest.mark.parametrize("field,value", [
    ("task_id", ""),
    ("left_condition", ""),
    ("right_condition", "   "),
    ("axis", ""),
    ("judge_id", ""),
    ("winner", "draw"),
    ("winner", "LEFT"),
    ("task_id", None),
    ("blind_pair_id", ""),
])
def test_verdict_rejects_invalid_fields(field, value):
    with pytest.raises(ValueError):
        verdict(**{field: value})


def test_verdict_rejects_identical_conditions():
    with pytest.raises(ValueError, match="must differ"):
        verdict(left_condition="same", right_condition="same")


def test_pair_id_is_deterministic_and_order_independent():
    first = judges.randomized_pair_id("t1", "baseline-verbose", "treatment-lexical", seed=5)
    second = judges.randomized_pair_id("t1", "baseline-verbose", "treatment-lexical", seed=5)
    swapped = judges.randomized_pair_id("t1", "treatment-lexical", "baseline-verbose", seed=5)
    assert first == second == swapped
    assert judges.randomized_pair_id("t1", "baseline-verbose", "treatment-lexical", seed=6) != first


def test_pair_id_never_reveals_condition_names():
    pair_id = judges.randomized_pair_id("t1", "baseline-verbose", "treatment-lexical", seed=0)
    assert "baseline" not in pair_id
    assert "treatment" not in pair_id
    assert "verbose" not in pair_id
    assert pair_id.startswith("pair-")
    assert len(pair_id) <= 32


def test_blinding_swaps_slots_and_keeps_the_mapping_separate():
    original = verdict(winner="left")
    blinded, mapping = judges.blind_pairs([original], seed=0)

    assert len(blinded) == 1
    assert len(mapping) == 1
    (blinded_verdict,) = blinded
    assert blinded_verdict.blind_pair_id in mapping
    entry = mapping[blinded_verdict.blind_pair_id]

    if entry["swapped"]:
        assert blinded_verdict.left_condition == original.right_condition
        assert blinded_verdict.right_condition == original.left_condition
        assert blinded_verdict.winner == "right"
    else:
        assert blinded_verdict.left_condition == original.left_condition
        assert blinded_verdict.right_condition == original.right_condition
        assert blinded_verdict.winner == "left"

    assert entry["left_condition"] == original.left_condition
    assert entry["right_condition"] == original.right_condition
    assert entry["task_id"] == original.task_id
    # The mapping is not embedded in the blinded record.
    assert blinded_verdict.to_dict()["blind_pair_id"] == blinded_verdict.blind_pair_id


def test_judge_projection_omits_original_condition_names():
    original = verdict(winner="left")
    blinded, mapping = judges.blind_pairs([original], seed=0)
    (record,) = blinded
    projection = record.to_judge_dict()
    payload = json.dumps(projection, allow_nan=False)
    assert "baseline-verbose" not in payload
    assert "treatment-lexical" not in payload
    assert "baseline" not in payload
    assert "treatment" not in payload
    assert projection["left_response_slot"] == "left"
    assert projection["right_response_slot"] == "right"
    assert projection["winner"] == record.winner
    assert projection["axis"] == original.axis
    assert projection["judge_id"] == original.judge_id
    assert projection["blind_pair_id"] == record.blind_pair_id
    assert "left_condition" not in projection
    assert "right_condition" not in projection


def test_judge_projection_survives_slot_swap_and_unblinding():
    records = [verdict(task_id=f"t{i}", winner="left") for i in range(4)]
    blinded, mapping = judges.blind_pairs(records, seed=9)
    for record in blinded:
        projection = record.to_judge_dict()
        assert "baseline-verbose" not in json.dumps(projection)
        assert "treatment-lexical" not in json.dumps(projection)
        assert judges.unblind_winner(record, mapping) == "baseline-verbose"


def test_blinding_is_deterministic_and_uses_both_orders():
    records = [verdict(task_id=f"t{i}", axis="quality", judge_id="j1") for i in range(8)]
    first, mapping_a = judges.blind_pairs(records, seed=3)
    second, mapping_b = judges.blind_pairs(records, seed=3)
    assert first == second
    assert mapping_a == mapping_b
    # Over eight independent pairs a seed-stable coin should not land only one way.
    assert {entry["swapped"] for entry in mapping_a.values()} == {True, False}


def test_blind_pair_ids_are_addressable_for_repeated_pairs():
    records = [verdict(), verdict()]
    blinded, mapping = judges.blind_pairs(records, seed=1)
    assert len(mapping) == 2
    assert {record.blind_pair_id for record in blinded} == set(mapping)


def test_tie_survives_a_swap():
    for seed in range(6):
        blinded, mapping = judges.blind_pairs([verdict(winner="tie")], seed=seed)
        assert blinded[0].winner == "tie"
        assert judges.unblind_winner(blinded[0], mapping) == "tie"


def test_unblinding_recovers_the_winning_condition_for_both_orders():
    records = [verdict(task_id=f"t{i}", winner="left") for i in range(4)]
    blinded, mapping = judges.blind_pairs(records, seed=9)
    for record in blinded:
        assert judges.unblind_winner(record, mapping) == "baseline-verbose"
    # And a right-slot win maps to the condition that occupied the right slot.
    swapped_any = [r for r in blinded if mapping[r.blind_pair_id]["swapped"]]
    assert swapped_any  # seed 9 must swap at least one of four pairs
    assert judges.unblind_winner(swapped_any[0], mapping) == "baseline-verbose"


def test_blinding_rejects_already_blinded_records_and_bad_input():
    with pytest.raises(ValueError, match="already blinded"):
        judges.blind_pairs([verdict(blind_pair_id="pair-x")], seed=0)
    with pytest.raises(ValueError, match="missing fields"):
        judges.blind_pairs([{"task_id": "t1"}], seed=0)
    with pytest.raises(ValueError):
        judges.blind_pairs(["not a record"], seed=0)
    with pytest.raises(ValueError):
        judges.blind_pairs([verdict()], seed=True)


def test_unblinding_rejects_missing_mapping():
    blinded, _ = judges.blind_pairs([verdict()], seed=2)
    with pytest.raises(ValueError, match="no mapping"):
        judges.unblind_winner(blinded[0], {})


def test_unblinding_refuses_a_tampered_slot_assignment():
    blinded, mapping = judges.blind_pairs([verdict()], seed=4)
    entry = mapping[blinded[0].blind_pair_id]
    tampered = judges.PairwiseVerdict(
        task_id=blinded[0].task_id,
        left_condition=entry["left_condition"],
        right_condition=entry["right_condition"],
        winner=blinded[0].winner,
        axis=blinded[0].axis,
        judge_id=blinded[0].judge_id,
        blind_pair_id=blinded[0].blind_pair_id,
    )
    if entry["swapped"]:
        with pytest.raises(ValueError, match="do not match"):
            judges.unblind_winner(tampered, mapping)
    else:
        assert judges.unblind_winner(tampered, mapping) == "baseline-verbose"
