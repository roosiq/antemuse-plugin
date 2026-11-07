"""Task-clustered paired analysis.

Records are per-task observations: ``{"task_id": ..., "condition": ..., <value_key>: ...}``.
Pairing happens inside a task, because two conditions applied to different tasks
are not a pair.  Every function fails closed: a missing partner, a duplicate
condition, or a non-finite value raises instead of being dropped or imputed.

Nothing here asserts significance on its own.  ``sign_test`` returns an exact
two-sided binomial p-value for the counts it is given; ``cluster_bootstrap``
returns an interval for a resampling statistic.  Both are descriptions of the
observed fixture-sized data, not evidence about a population, and neither is a
creativity measure.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Dict, List, Mapping, Sequence, Tuple

STATISTICS = ("mean", "median")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _finite(value: Any, *, field: str) -> float:
    if not _is_number(value):
        raise ValueError(f"{field} must be a real number, got {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite, got {number!r}")
    return number


def _task_id(record: Mapping[str, Any], *, index: int) -> str:
    try:
        task_id = record["task_id"]
    except (KeyError, TypeError):
        raise ValueError(f"record {index} has no task_id") from None
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError(f"record {index} task_id must be a non-empty string")
    return task_id


def _condition(record: Mapping[str, Any], *, index: int) -> str:
    try:
        condition = record["condition"]
    except (KeyError, TypeError):
        raise ValueError(f"record {index} has no condition") from None
    if not isinstance(condition, str) or not condition.strip():
        raise ValueError(f"record {index} condition must be a non-empty string")
    return condition


def _value(record: Mapping[str, Any], value_key: str, *, index: int) -> float:
    if value_key not in record:
        raise ValueError(f"record {index} has no {value_key!r}")
    return _finite(record[value_key], field=f"record {index} {value_key}")


def paired_deltas(records: Sequence[Mapping[str, Any]], value_key: str,
                  baseline_key: str = "A", experimental_key: str = "F") -> List[Dict[str, Any]]:
    """Per-task ``experimental - baseline`` deltas.

    Returns one dict per complete task, sorted by ``task_id``:
    ``{"task_id", "baseline", "experimental", "delta"}``.

    Requires both conditions exactly once per non-empty task group.  A task with
    only one side, a duplicate condition, or no usable value raises
    ``ValueError`` naming every offending task, so incomplete pairing cannot
    silently shrink the sample.
    """
    if not isinstance(value_key, str) or not value_key:
        raise ValueError("value_key must be a non-empty string")
    for key, label in ((baseline_key, "baseline_key"), (experimental_key, "experimental_key")):
        if not isinstance(key, str) or not key:
            raise ValueError(f"{label} must be a non-empty string")
    if baseline_key == experimental_key:
        raise ValueError("baseline_key and experimental_key must differ")
    if isinstance(records, (str, bytes)) or not isinstance(records, Sequence):
        raise ValueError("records must be a sequence of mappings")
    if not records:
        raise ValueError("records must be non-empty")

    grouped: Dict[str, Dict[str, float]] = {}
    duplicates: List[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValueError(f"record {index} must be a mapping")
        task_id = _task_id(record, index=index)
        condition = _condition(record, index=index)
        grouped.setdefault(task_id, {})
        if condition in grouped[task_id]:
            duplicates.append(task_id)
            continue
        if condition in (baseline_key, experimental_key):
            grouped[task_id][condition] = _value(record, value_key, index=index)

    if duplicates:
        raise ValueError(f"duplicate condition within task(s): {', '.join(sorted(set(duplicates)))}")

    incomplete: List[str] = []
    out: List[Dict[str, Any]] = []
    for task_id in sorted(grouped):
        cells = grouped[task_id]
        missing = [key for key in (baseline_key, experimental_key) if key not in cells]
        if missing:
            incomplete.append(f"{task_id} (missing {', '.join(missing)})")
            continue
        baseline = cells[baseline_key]
        experimental = cells[experimental_key]
        out.append({
            "task_id": task_id,
            "baseline": baseline,
            "experimental": experimental,
            "delta": experimental - baseline,
        })
    if incomplete:
        raise ValueError("missing paired observation for task(s): " + "; ".join(incomplete))
    if not out:
        raise ValueError(f"no records for conditions {baseline_key!r} or {experimental_key!r}")
    return out


def sign_test(wins: int, losses: int, ties: int = 0) -> float:
    """Exact two-sided sign-test p-value from win/loss counts.

    Ties are reported but carry no direction, so they do not enter ``n``.  The
    p-value is ``2 * sum_{i=0}^{min(w, l)} C(n, i) / 2**n`` capped at 1.0, using
    exact rational arithmetic (``fractions.Fraction``) so the conversion to
    float happens only after the final division.  With no non-tied pairs the
    result is 1.0 (no evidence either way).
    """
    for name, value in (("wins", wins), ("losses", losses), ("ties", ties)):
        if not _is_int(value):
            raise ValueError(f"{name} must be an integer, got {type(value).__name__}")
        if value < 0:
            raise ValueError(f"{name} must be non-negative, got {value}")
    n = wins + losses
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(wins, losses) + 1))
    p_value = Fraction(2 * tail, 2 ** n)
    return float(min(Fraction(1, 1), p_value))


def _mean(values: Sequence[float]) -> float:
    return math.fsum(values) / len(values)


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def percentile(sorted_values: Sequence[float], q: float) -> float:
    """Linear-interpolated percentile (``q`` in ``[0, 1]``) of sorted values."""
    if not sorted_values:
        raise ValueError("cannot take a percentile of no values")
    if not 0.0 <= q <= 1.0:
        raise ValueError(f"q must be in [0, 1], got {q!r}")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


@dataclass(frozen=True)
class BootstrapResult:
    """Observed statistic plus a percentile interval over resampled clusters."""

    statistic: str
    observed: float
    lower: float
    upper: float
    confidence: float
    iterations: int
    seed: int
    clusters: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statistic": self.statistic,
            "observed": self.observed,
            "lower": self.lower,
            "upper": self.upper,
            "confidence": self.confidence,
            "iterations": self.iterations,
            "seed": self.seed,
            "clusters": self.clusters,
        }


def cluster_bootstrap(records: Sequence[Mapping[str, Any]], value_key: str,
                      statistic: str = "mean", iterations: int = 1000,
                      seed: int = 0) -> BootstrapResult:
    """Resample whole task clusters with replacement, 95% percentile interval.

    All observations belonging to a sampled task travel together, which keeps
    within-task correlation and prevents a task with many records from being
    treated as many independent tasks.  Cluster order is sorted before
    resampling and the RNG is seeded, so the result is reproducible for the same
    records and seed; record order in the input does not matter.
    """
    if statistic not in STATISTICS:
        raise ValueError(f"statistic must be one of {STATISTICS}, got {statistic!r}")
    if not _is_int(iterations) or iterations < 1:
        raise ValueError(f"iterations must be a positive integer, got {iterations!r}")
    if not _is_int(seed):
        raise ValueError(f"seed must be an integer, got {type(seed).__name__}")
    if isinstance(records, (str, bytes)) or not isinstance(records, Sequence):
        raise ValueError("records must be a sequence of mappings")
    if not records:
        raise ValueError("records must be non-empty")

    clusters: Dict[str, List[float]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValueError(f"record {index} must be a mapping")
        task_id = _task_id(record, index=index)
        clusters.setdefault(task_id, []).append(_value(record, value_key, index=index))

    task_ids = sorted(clusters)
    all_values = [value for task_id in task_ids for value in clusters[task_id]]
    reduce = _mean if statistic == "mean" else _median
    observed = reduce(all_values)

    rng = random.Random(seed)
    sample_statistics: List[float] = []
    for _ in range(iterations):
        drawn: List[float] = []
        for _ in range(len(task_ids)):
            drawn.extend(clusters[task_ids[rng.randrange(len(task_ids))]])
        sample_statistics.append(reduce(drawn))

    sample_statistics.sort()
    return BootstrapResult(
        statistic=statistic,
        observed=observed,
        lower=percentile(sample_statistics, 0.025),
        upper=percentile(sample_statistics, 0.975),
        confidence=0.95,
        iterations=iterations,
        seed=seed,
        clusters=len(task_ids),
    )
