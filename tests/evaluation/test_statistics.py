"""Paired deltas, exact sign test, and task-cluster bootstrap.

Counts and fixtures are exact; intervals describe these toy records only.
"""
from __future__ import annotations

import json
import math

import pytest

from . import load

statistics = load("statistics")


def rec(task_id, condition, score):
    return {"task_id": task_id, "condition": condition, "score": score}


# ----------------------------------------------------------------- paired deltas

def test_paired_deltas_are_per_task_and_sorted():
    records = [
        rec("t2", "F", 0.4),
        rec("t1", "A", 0.2),
        rec("t2", "A", 0.4),
        rec("t1", "F", 0.5),
    ]
    assert statistics.paired_deltas(records, "score") == [
        {"task_id": "t1", "baseline": 0.2, "experimental": 0.5, "delta": pytest.approx(0.3)},
        {"task_id": "t2", "baseline": 0.4, "experimental": 0.4, "delta": pytest.approx(0.0)},
    ]


def test_paired_deltas_ignores_other_conditions():
    records = [rec("t1", "A", 1.0), rec("t1", "F", 2.0), rec("t1", "B", 99.0)]
    deltas = statistics.paired_deltas(records, "score")
    assert len(deltas) == 1
    assert deltas[0]["delta"] == pytest.approx(1.0)


def test_paired_deltas_fails_on_missing_partner_and_names_the_task():
    records = [rec("t1", "A", 1.0), rec("t1", "F", 2.0), rec("t2", "A", 3.0)]
    with pytest.raises(ValueError, match="t2"):
        statistics.paired_deltas(records, "score")
    with pytest.raises(ValueError, match="missing F"):
        statistics.paired_deltas(records, "score")


def test_paired_deltas_fails_on_duplicate_condition():
    records = [rec("t1", "A", 1.0), rec("t1", "A", 2.0), rec("t1", "F", 3.0)]
    with pytest.raises(ValueError, match="duplicate"):
        statistics.paired_deltas(records, "score")


def test_paired_deltas_rejects_empty_records_and_bad_values():
    with pytest.raises(ValueError, match="non-empty"):
        statistics.paired_deltas([], "score")
    with pytest.raises(ValueError, match="finite"):
        statistics.paired_deltas([rec("t1", "A", float("nan")), rec("t1", "F", 1.0)], "score")
    with pytest.raises(ValueError, match="score"):
        statistics.paired_deltas([rec("t1", "A", 1.0), {"task_id": "t1", "condition": "F"}], "score")


# -------------------------------------------------------------------- sign test

@pytest.mark.parametrize("wins,losses,expected", [
    (0, 0, 1.0),          # no evidence
    (3, 0, 0.25),         # 2 * C(3,0) / 2**3
    (8, 1, 0.0390625),    # 2 * (C(9,0)+C(9,1)) / 2**9 = 20/512
    (9, 0, 2.0 / 512.0),  # 2 * 1 / 512
    (5, 4, 1.0),          # two-sided tail capped at 1
    (0, 5, 0.0625),       # 2 * 1 / 32
])
def test_sign_test_exact_values(wins, losses, expected):
    assert statistics.sign_test(wins, losses) == pytest.approx(expected)


def test_sign_test_ties_do_not_enter_the_binomial():
    assert statistics.sign_test(8, 1, ties=100) == pytest.approx(0.0390625)
    assert statistics.sign_test(0, 0, ties=7) == 1.0


def test_sign_test_is_symmetric():
    assert statistics.sign_test(7, 2) == pytest.approx(statistics.sign_test(2, 7))


@pytest.mark.parametrize("args", [(-1, 0), (0, -1), (1.5, 0), (True, 0), (0, False)])
def test_sign_test_rejects_invalid_counts(args):
    with pytest.raises(ValueError):
        statistics.sign_test(*args)


def test_sign_test_rejects_negative_ties():
    with pytest.raises(ValueError, match="ties"):
        statistics.sign_test(1, 1, ties=-1)


@pytest.mark.parametrize("wins,losses", [(512, 512), (1000, 900)])
def test_sign_test_large_counts_do_not_overflow(wins, losses):
    p_value = statistics.sign_test(wins, losses)
    assert math.isfinite(p_value)
    assert 0.0 <= p_value <= 1.0


def test_sign_test_extreme_asymmetric_large_counts_is_finite():
    p_value = statistics.sign_test(2000, 0)
    assert math.isfinite(p_value)
    assert 0.0 <= p_value <= 1.0


# ------------------------------------------------------------- cluster bootstrap

def bootstrap_records():
    # One heavy task with ten zeros, one light task with a single 100.
    return ([rec("heavy", "A", 0.0) for _ in range(10)] + [rec("light", "A", 100.0)])


def test_bootstrap_reports_observed_and_interval_on_clusters():
    result = statistics.cluster_bootstrap(bootstrap_records(), "score",
                                          iterations=500, seed=0)
    assert result.clusters == 2
    assert result.observed == pytest.approx(100.0 / 11.0)
    assert 0.0 <= result.lower <= result.observed <= result.upper <= 100.0


def test_bootstrap_resamples_whole_clusters_not_observations():
    # With clusters {heavy: ten 0s} and {light: one 100}, every cluster-level
    # resample has mean 0, 50, or 100.  Observation-level resampling could not
    # reach 100 at the top of the interval (it would top out near 100 * 2/11).
    result = statistics.cluster_bootstrap(bootstrap_records(), "score",
                                          iterations=1000, seed=0)
    assert result.lower == 0.0
    assert result.upper == 100.0


def test_bootstrap_is_reproducible_and_order_independent():
    records = bootstrap_records()
    first = statistics.cluster_bootstrap(records, "score", iterations=300, seed=11)
    second = statistics.cluster_bootstrap(records, "score", iterations=300, seed=11)
    shuffled = list(reversed(records))
    third = statistics.cluster_bootstrap(shuffled, "score", iterations=300, seed=11)
    assert first == second
    assert first == third
    assert first.to_dict()["seed"] == 11


def test_bootstrap_seed_changes_the_resample_draws():
    # Not a guarantee that every seed differs, but seed 0 vs 1 on these records
    # must be recorded and independently reproducible.
    a = statistics.cluster_bootstrap(bootstrap_records(), "score", iterations=50, seed=0)
    b = statistics.cluster_bootstrap(bootstrap_records(), "score", iterations=50, seed=1)
    assert (a.seed, b.seed) == (0, 1)


def test_bootstrap_median_statistic():
    records = [rec("t1", "A", 0.0), rec("t2", "A", 10.0), rec("t3", "A", 100.0)]
    result = statistics.cluster_bootstrap(records, "score", statistic="median",
                                          iterations=200, seed=3)
    assert result.observed == pytest.approx(10.0)
    assert result.statistic == "median"
    assert 0.0 <= result.lower <= 10.0 <= result.upper <= 100.0


def test_bootstrap_result_is_strict_json():
    result = statistics.cluster_bootstrap(bootstrap_records(), "score",
                                          iterations=100, seed=0)
    payload = json.dumps(result.to_dict(), allow_nan=False)
    assert json.loads(payload)["clusters"] == 2


@pytest.mark.parametrize("kwargs", [
    {"iterations": 0},
    {"iterations": -5},
    {"iterations": True},
    {"statistic": "mode"},
    {"seed": "0"},
])
def test_bootstrap_rejects_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        statistics.cluster_bootstrap(bootstrap_records(), "score", **kwargs)


def test_bootstrap_rejects_empty_records():
    with pytest.raises(ValueError, match="non-empty"):
        statistics.cluster_bootstrap([], "score")


def test_bootstrap_rejects_non_finite_values():
    with pytest.raises(ValueError, match="finite"):
        statistics.cluster_bootstrap([rec("t1", "A", float("inf"))], "score")


def test_percentile_interpolates_between_ranks():
    assert statistics.percentile([0.0, 10.0], 0.5) == 5.0
    assert statistics.percentile([0.0, 10.0], 0.0) == 0.0
    assert statistics.percentile([0.0, 10.0], 1.0) == 10.0
    assert statistics.percentile([7.0], 0.5) == 7.0
    with pytest.raises(ValueError):
        statistics.percentile([], 0.5)
    with pytest.raises(ValueError):
        statistics.percentile([1.0], 1.5)
