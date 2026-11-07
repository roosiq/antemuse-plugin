"""Distance and diversity metrics for candidate pools.

What this module measures
-------------------------
* Geometry of whatever vectors an embedder produced: cosine distance,
  pairwise distances, mean pairwise distance inside a pool, and mean
  nearest-baseline distance for candidates that were produced under some
  condition.
* Structure of explicitly declared mechanism tags: mean Jaccard distance
  between tag sets.

What this module does not measure
---------------------------------
* It does not embed anything.  Vectors are injected by the caller; this
  module never imports numpy or an embedding model and makes no network or
  LLM calls.
* Candidate-pool geometry is not response quality.  A high ``pool_diversity``
  says the candidate vectors are far apart, not that any of them is good,
  original, or useful.  Diversity must be reported next to a separate,
  blind quality measure (see :mod:`evaluation.judges`), never in place of it.
* ``structural_diversity`` only compares tags the caller declares.  It does
  not read the text, infer tags lexically, or decide whether a tag is apt.
  Two records with the same declared tags are structurally identical here
  even when their wording or vectors differ.
* No value returned by this module is a statistical claim.  Fixtures used in
  tests are known arithmetic, not evidence about any real condition.

All invalid numeric input raises ``ValueError`` (including wrong types, so a
caller can fail closed on one exception class).  NaN and infinity are rejected
rather than propagated.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Dict, List, Tuple

Vector = Sequence[float]
PairDistance = Tuple[int, int, float]


def _is_number(value: Any) -> bool:
    """True for real numeric scalars, excluding bools and strings."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_vector(value: Any, *, name: str) -> List[float]:
    """Validate one numeric, finite, non-empty vector and return floats."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a sequence of numbers, got {type(value).__name__}")
    if not value:
        raise ValueError(f"{name} must be non-empty")
    out: List[float] = []
    for index, item in enumerate(value):
        if not _is_number(item):
            raise ValueError(f"{name}[{index}] must be a real number, got {type(item).__name__}")
        number = float(item)
        if not math.isfinite(number):
            raise ValueError(f"{name}[{index}] must be finite, got {number!r}")
        out.append(number)
    return out


def _as_vectors(vectors: Any, *, name: str) -> List[List[float]]:
    """Validate a rectangular list of equal-length, non-empty vectors."""
    if isinstance(vectors, (str, bytes)) or not isinstance(vectors, Sequence):
        raise ValueError(f"{name} must be a sequence of vectors")
    rows = [_as_vector(vector, name=f"{name}[{i}]") for i, vector in enumerate(vectors)]
    if not rows:
        return []
    width = len(rows[0])
    for index, row in enumerate(rows[1:], start=1):
        if len(row) != width:
            raise ValueError(
                f"{name} is not rectangular: {name}[0] has length {width}, "
                f"{name}[{index}] has length {len(row)}"
            )
    return rows


def _cosine_distance(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError(f"vector lengths differ: {len(left)} != {len(right)}")
    dot = math.fsum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(math.fsum(a * a for a in left))
    right_norm = math.sqrt(math.fsum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        raise ValueError("cosine distance is undefined for a zero vector")
    # Floating point can push identical vectors a hair below zero; clamp to the
    # mathematical range [0, 2] rather than reporting a negative distance.
    return min(2.0, max(0.0, 1.0 - dot / (left_norm * right_norm)))


def cosine_distance(a: Vector, b: Vector) -> float:
    """Cosine distance ``1 - cos(a, b)`` in ``[0, 2]``.

    Raises ``ValueError`` for empty/mismatched/non-numeric/non-finite vectors
    and for a zero vector, where the angle is undefined.
    """
    left = _as_vector(a, name="a")
    right = _as_vector(b, name="b")
    return _cosine_distance(left, right)


def pairwise_distances(vectors: Sequence[Vector]) -> List[PairDistance]:
    """Return the upper triangle as ``(i, j, distance)`` for every ``i < j``.

    Order is row-major (``i`` ascending, then ``j`` ascending), so the result is
    deterministic.  The diagonal is not included and the triangle is not
    mirrored.
    """
    rows = _as_vectors(vectors, name="vectors")
    out: List[PairDistance] = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            out.append((i, j, _cosine_distance(rows[i], rows[j])))
    return out


def pool_diversity(vectors: Sequence[Vector]) -> float:
    """Mean pairwise cosine distance inside a candidate pool.

    Returns ``0.0`` when the pool has fewer than two vectors.  An empty pool is
    therefore not evidence of anything; callers must not read the zero as
    "homogeneous".
    """
    rows = _as_vectors(vectors, name="vectors")
    if len(rows) < 2:
        return 0.0
    distances = [_cosine_distance(rows[i], rows[j])
                 for i in range(len(rows)) for j in range(i + 1, len(rows))]
    return math.fsum(distances) / len(distances)


def novelty_against_baseline(candidate_vectors: Sequence[Vector],
                             baseline_vectors: Sequence[Vector]) -> float:
    """Mean distance from each candidate to its nearest baseline vector.

    This is a distance-to-nearest-baseline score, not a novelty verdict: a
    candidate can be far from every baseline and still be bad.  Both lists must
    be non-empty (``ValueError`` otherwise), and every vector must match the
    baseline dimensionality.
    """
    candidates = _as_vectors(candidate_vectors, name="candidate_vectors")
    baselines = _as_vectors(baseline_vectors, name="baseline_vectors")
    if not candidates:
        raise ValueError("candidate_vectors must be non-empty")
    if not baselines:
        raise ValueError("baseline_vectors must be non-empty")
    if len(candidates[0]) != len(baselines[0]):
        raise ValueError(
            "candidate and baseline vectors must share a dimension: "
            f"{len(candidates[0])} != {len(baselines[0])}"
        )
    nearest: List[float] = []
    for candidate in candidates:
        nearest.append(min(_cosine_distance(candidate, baseline) for baseline in baselines))
    return math.fsum(nearest) / len(nearest)


def _as_tag_set(value: Any, *, name: str) -> frozenset:
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable) or isinstance(value, Mapping):
        raise ValueError(f"{name} must be an iterable of mechanism tags, not a mapping or string")
    tags = set()
    for tag in value:
        if not isinstance(tag, str) or not tag.strip():
            raise ValueError(f"{name} contains an invalid tag: {tag!r}")
        tags.add(tag.strip())
    return frozenset(tags)


def structural_diversity(tag_sets: Sequence[Iterable[str]]) -> float:
    """Mean Jaccard distance between explicitly declared mechanism tag sets.

    ``J(A, B) = 1 - |A & B| / |A | B|``.  Two empty sets are treated as
    identical (distance 0); one empty set against a non-empty set is distance
    1.  Fewer than two tag sets returns ``0.0``.

    Tags must be supplied by the caller.  This function performs no lexical
    inference, so it can only distinguish mechanisms the records already name.
    """
    if isinstance(tag_sets, (str, bytes)) or not isinstance(tag_sets, Sequence):
        raise ValueError("tag_sets must be a sequence of tag sets")
    sets = [_as_tag_set(tags, name=f"tag_sets[{i}]") for i, tags in enumerate(tag_sets)]
    if len(sets) < 2:
        return 0.0
    distances: List[float] = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            union = sets[i] | sets[j]
            if not union:
                distances.append(0.0)
            else:
                distances.append(1.0 - len(sets[i] & sets[j]) / len(union))
    return math.fsum(distances) / len(distances)


def describe() -> Dict[str, str]:
    """Machine-readable statement of what is and is not measured."""
    return {
        "measures": "candidate-pool vector geometry and declared structural tags",
        "does_not_measure": "response quality, creativity, authorship, or statistical significance",
        "vectors": "injected by the caller; no embedder, numpy, LLM, or network call lives here",
        "structure": "explicit mechanism tags only; no lexical inference over response text",
    }
