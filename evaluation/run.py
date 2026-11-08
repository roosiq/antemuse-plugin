"""Offline runner for the Antemuse baseline conditions A, B, and C.

The runner is transport-agnostic by construction: callers pass a callable that
accepts a structured request dict and returns a structured response dict, so
tests and later measurement harnesses can drive it with fakes and no provider
SDK, network socket, or wall clock is involved here.

Conditions:

  A  ordinary request, one model call.
  B  one model call with a creativity instruction matched in length to A's, so
     the only difference between A and B is what the instruction asks for.
  D  ordinary request plus deterministic Antemuse transfer material: the
     collider bank is selected, collided and cleaned up with no model call, and
     the resulting block rides along with A's instruction. D is not "D with a
     branch model" — nothing is inferred before the single answer call, which is
     what makes A vs D a test of the material rather than of extra compute.
  E  separated branches with no transfer material and no selection: N
     independent calls at N different seeds, each with A's instruction and no
     source. This is the plain branching control. It was chosen deliberately
     over inventing an angle list: nothing in the code separates branches except
     a source, so E separates them only by independence. The consequence is
     recorded rather than hidden — F vs E therefore bundles material *and*
     selection, and the material question is carried by D vs B/A, not by F vs E.
  F  separated branches with Collider sources and selection: one branch per
     selected source, built by ``orchestrator.branch_plan`` so the runner cannot
     drift from production, then the injected selector picks one. F is not yet
     compared against E — E has no separation mechanism that is not the Collider,
     and inventing one would decide what the experiment measures.
  C  baseline best-of-N: N independent calls with A's own instruction, then one
     selector call over the candidates. C is not "best" because it sampled N
     times; the record reports whichever candidate the selector named, and the
     default selector is a deterministic first-ok choice, not a judgment.

Cache and records:

  Cache keys come from :func:`evaluation.cache.condition_cache_key`, so a
  record can only be replayed for the exact model, condition, task, prompt
  version, source version, and seed that produced it. C's N branches live
  inside one condition run and produce one cache entry, not N.

  ``run_id`` is derived from the cache key alone (no clock, no task text), so a
  replay reconstructs the same identity. Exact hits return the stored record
  with ``cache_status: "hit"`` and make zero transport calls.

Failure policy:

  An unknown condition is data, not a crash: it returns a named
  ``invalid_condition`` record with no run id and no calls. A malformed task is
  a broken fixture, so it raises ``ValueError`` before any call. Transport
  exceptions and malformed responses become ``transport_error`` / ``partial``
  records with ``text: None`` — never a fabricated candidate — and failed runs
  are not cached, so a retry can still succeed. A selector that raises, names
  an unknown candidate, or names a failed candidate yields ``selector_error``.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union

from evaluation.cache import JsonlCache, condition_cache_key

__all__ = [
    "CONDITIONS",
    "N",
    "INSTRUCTIONS",
    "run_condition",
    "select_first",
    "validate_task",
    "USAGE_FIELDS",
]

CONDITIONS = frozenset({"A", "B", "C", "D", "E", "F"})
N = 3
BRANCHES = tuple(range(N))

# A and C share the baseline instruction: C is best-of-N over the same request
# A makes, so any difference between them comes from sampling, not prompting.
BASELINE_INSTRUCTION = "Answer the brief as you normally would."
CREATIVITY_INSTRUCTION = "Answer the brief, but make it creative."

# D keeps A's instruction on purpose: the only difference between A and D is
# that D carries deterministic transfer material, so the contrast isolates the
# material rather than the wording.
INSTRUCTIONS = {
    "A": BASELINE_INSTRUCTION,
    "B": CREATIVITY_INSTRUCTION,
    "C": BASELINE_INSTRUCTION,
    "D": BASELINE_INSTRUCTION,
    "E": BASELINE_INSTRUCTION,   # no material: only the seed separates a branch
    "F": BASELINE_INSTRUCTION,   # each branch replaces this with its own instruction
    # F's final answer is written from the selected candidate, so the outcome is
    # a response comparable with A-E rather than an intermediate artifact.
    "F:synthesis": (
        "Answer the brief as you normally would. You may use the candidate "
        "approach below if it helps, ignore it if it does not, and you may "
        "disagree with it.\n\nCandidate approach:\n"
    ),
}

USAGE_FIELDS = ("input_tokens", "output_tokens", "total_tokens")

ZERO_USAGE = {field: 0 for field in USAGE_FIELDS}

TASK_FIELDS = (
    "id",
    "brief",
    "good_idea_qualities",
    "forbidden_topics",
    "reference_text",
)

RUN_ID_NAMESPACE = "antemuse-eval-run-v1"


class _MalformedResponse(Exception):
    """A transport response that cannot be recorded as a real candidate."""


def validate_task(task: Any) -> None:
    """Validate one development task, raising ``ValueError`` naming the field.

    Tasks are fixtures, not experiment data: a task missing its brief cannot be
    measured at all, so it fails loudly before a transport is touched rather
    than producing a run record with an empty request.
    """
    if not isinstance(task, dict):
        raise ValueError(f"task must be an object, got {type(task).__name__}")

    missing = [field for field in TASK_FIELDS if field not in task]
    if missing:
        raise ValueError(f"task is missing required field(s): {', '.join(missing)}")

    for field in ("id", "brief", "reference_text"):
        value = task[field]
        if not isinstance(value, str):
            raise ValueError(
                f"task['{field}'] must be a string, got {type(value).__name__}"
            )
        if not value.strip():
            raise ValueError(f"task['{field}'] must be non-empty")

    for field in ("good_idea_qualities", "forbidden_topics"):
        value = task[field]
        if not isinstance(value, list):
            raise ValueError(
                f"task['{field}'] must be a list, got {type(value).__name__}"
            )
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                raise ValueError(
                    f"task['{field}'][{index}] must be a non-empty string"
                )

    if not task["good_idea_qualities"]:
        raise ValueError("task['good_idea_qualities'] must name at least one quality")


def select_first(candidates: Sequence[Mapping[str, Any]]) -> Optional[str]:
    """Return the first candidate that actually answered, or ``None``.

    This is the default selector and deliberately not a quality judgment: it
    reads no text, compares nothing, and cannot rank. It only refuses to select
    a candidate that failed, so a caller cannot mistake "first" for "best".
    """
    for candidate in candidates:
        if candidate.get("status") == "ok":
            return candidate["candidate_id"]
    return None


def _run_id(cache_key: str) -> str:
    digest = hashlib.sha256(
        f"{RUN_ID_NAMESPACE}:{cache_key}".encode("utf-8")
    ).hexdigest()
    return "run-" + digest[:32]


def _failed_usage() -> Dict[str, int]:
    return dict(ZERO_USAGE)


def _normalize_usage(raw: Any) -> Dict[str, int]:
    """Read a response's usage strictly, or raise ``_MalformedResponse``."""
    if raw is None:
        # A transport that reports no usage is recorded as zero rather than
        # having a number guessed for it.
        return _failed_usage()
    if not isinstance(raw, dict):
        raise _MalformedResponse(
            f"response usage must be an object, got {type(raw).__name__}"
        )

    usage: Dict[str, int] = {}
    for field in ("input_tokens", "output_tokens"):
        value = raw.get(field, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise _MalformedResponse(
                f"response usage['{field}'] must be a non-negative int, "
                f"got {value!r}"
            )
        usage[field] = value

    total = raw.get("total_tokens")
    if total is None:
        total = usage["input_tokens"] + usage["output_tokens"]
    elif isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise _MalformedResponse(
            f"response usage['total_tokens'] must be a non-negative int, "
            f"got {total!r}"
        )
    usage["total_tokens"] = total
    return usage


def _candidate_from_response(
    condition: str, branch: int, response: Any
) -> Dict[str, Any]:
    """Turn one transport response into a candidate record, or raise."""
    if not isinstance(response, dict):
        raise _MalformedResponse(
            f"response must be an object, got {type(response).__name__}"
        )
    text = response.get("text")
    if not isinstance(text, str) or not text.strip():
        raise _MalformedResponse(
            f"response text must be a non-empty string, got {text!r}"
        )
    usage = _normalize_usage(response.get("usage"))
    return {
        "candidate_id": f"{condition}-{branch}",
        "branch": branch,
        "text": text,
        "usage": usage,
        "status": "ok",
        "error": None,
    }


def _synthesize(
    transport: Callable[[Dict[str, Any]], Any],
    *,
    task: Mapping[str, Any],
    model: str,
    prompt_version: str,
    source_version: str,
    seed: int,
    candidate: Mapping[str, Any],
) -> Dict[str, Any]:
    """Turn F's selected candidate into a final answer — one more call, counted.

    The synthesis request carries only the selected candidate. Sibling
    candidates are deliberately absent: if they leaked in, F would quietly
    become best-of-N-with-all-material and the branch comparison would be void.
    """
    request = {
        "condition": "F",
        "stage": "synthesis",
        "task_id": task["id"],
        "brief": task["brief"],
        "model": model,
        "instruction": INSTRUCTIONS["F:synthesis"] + str(candidate.get("text") or ""),
        "prompt_version": prompt_version,
        "source_version": source_version,
        "seed": seed + 1000,          # a different draw from any branch
        "candidate_id": candidate["candidate_id"],
    }
    try:
        response = transport(request)
    except Exception as exc:  # noqa: BLE001 - recorded, never swallowed
        return {"status": "transport_error", "text": None, "usage": _failed_usage(),
                "error": f"{type(exc).__name__}: {exc}", "candidate_id": candidate["candidate_id"]}
    try:
        built = _candidate_from_response("F", 0, response)
    except _MalformedResponse as exc:
        return {"status": "transport_error", "text": None, "usage": _failed_usage(),
                "error": f"MalformedResponse: {exc}", "candidate_id": candidate["candidate_id"]}
    return {"status": "ok", "text": built["text"], "usage": built["usage"],
            "error": None, "candidate_id": candidate["candidate_id"]}


def _failed_candidate(condition: str, branch: int, error: str) -> Dict[str, Any]:
    return {
        "candidate_id": f"{condition}-{branch}",
        "branch": branch,
        "text": None,
        "usage": _failed_usage(),
        "status": "transport_error",
        "error": error,
    }


def _core_modules():
    """The plugin's own core package, resolved even when the runner is loaded alone.

    evaluation is imported both as a package and, in the offline harness, by
    file path; the second case has no parent on sys.path, so the sibling is
    found from where this file actually lives rather than assumed.
    """
    import sys
    from pathlib import Path

    root = str(Path(__file__).resolve().parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)
    from core import collider, runtime

    return collider, runtime


def deterministic_material(brief: str, *, seed: int,
                           artifacts: Optional[Sequence[Mapping[str, Any]]] = None) -> Dict[str, Any]:
    """The real deterministic path: collider bank → collision → selection.

    No model call happens here. If the bank cannot be read this raises, because
    a D run without its material is not a D run — substituting invented material
    would destroy the only thing the condition measures.
    """
    collider, runtime = _core_modules()
    bank = list(artifacts) if artifacts is not None else list(collider.load_bank())
    if not bank:
        raise ValueError("condition D needs a source bank; the collider bank is empty")
    run = runtime.plan(str(brief), method="collide", artifacts=bank,
                       options={"seed": str(seed)}, count=2)
    if not run.kept:
        raise ValueError(f"condition D produced no candidates for this brief (run {run.run_id[:16]})")
    return {
        "run_id": run.run_id,
        "sources": list(run.sources),
        "candidates": [str(c.get("candidate_id") or "") for c in run.kept],
        "block": run.for_model(),
    }


def branch_material(brief: str, *, seed: int, count: int = 3,
                    artifacts: Optional[Sequence[Mapping[str, Any]]] = None
                    ) -> List[Dict[str, Any]]:
    """The branches for F, from ``orchestrator.branch_plan`` — production's own path."""
    from core import collider, orchestrator

    bank = list(artifacts) if artifacts is not None else list(collider.load_bank())
    if not bank:
        raise ValueError("condition F needs a source bank; the collider bank is empty")
    plan = orchestrator.branch_plan({"id": "eval-task", "brief": str(brief)}, bank,
                                    seed=seed, count=count)
    if not plan:
        raise ValueError("condition F selected no sources for this brief")
    return plan


def _branch_request(
    *,
    condition: str,
    task: Mapping[str, Any],
    model: str,
    prompt_version: str,
    source_version: str,
    seed: int,
    branch: int,
    material: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    # Branch b is drawn with seed + b so the N samples in C are independent
    # draws rather than N retries of one request.
    request = {
        "condition": condition,
        "task_id": task["id"],
        "brief": task["brief"],
        "model": model,
        "instruction": INSTRUCTIONS[condition],
        "prompt_version": prompt_version,
        "source_version": source_version,
        "seed": seed + branch,
        "branch_index": branch,
    }
    if material is not None:
        if "branches" in material:
            branch = material["branches"][branch]
            request["instruction"] = branch["instruction"]
            request["inputs"] = branch["inputs"]
            request["sources"] = [branch["source_id"]]
            request["branch_id"] = branch["branch_id"]
        else:
            request["material"] = str(material.get("block") or "")
            request["sources"] = list(material.get("sources") or [])
    return request


def _call_branch(
    transport: Callable[[Dict[str, Any]], Any],
    *,
    condition: str,
    task: Mapping[str, Any],
    model: str,
    prompt_version: str,
    source_version: str,
    seed: int,
    branch: int,
    material: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    request = _branch_request(
        condition=condition,
        task=task,
        model=model,
        prompt_version=prompt_version,
        source_version=source_version,
        seed=seed,
        branch=branch,
        material=material,
    )
    try:
        response = transport(request)
    except Exception as exc:  # noqa: BLE001 - recorded, never swallowed silently
        return _failed_candidate(
            condition, branch, f"{type(exc).__name__}: {exc}"
        )
    try:
        return _candidate_from_response(condition, branch, response)
    except _MalformedResponse as exc:
        return _failed_candidate(condition, branch, f"MalformedResponse: {exc}")


def _choose(
    selector: Callable[[Sequence[Mapping[str, Any]]], Any],
    candidates: Sequence[Mapping[str, Any]],
) -> tuple[Optional[str], Optional[str]]:
    """Run the selector once; return ``(chosen_id, error)``.

    The selector receives copies and only the candidate ids it may legally pick
    are accepted, so a selector cannot mutate the record or promote a branch
    that never answered.
    """
    ok_ids = {
        candidate["candidate_id"]
        for candidate in candidates
        if candidate.get("status") == "ok"
    }
    try:
        choice = selector([copy.deepcopy(c) for c in candidates])
    except Exception as exc:  # noqa: BLE001
        return None, f"selector failed: {type(exc).__name__}: {exc}"

    if choice is None:
        if not ok_ids:
            return None, None
        return None, "selector returned no candidate id"
    if not isinstance(choice, str) or choice not in ok_ids:
        return None, (
            f"selector chose {choice!r}, which is not an ok candidate id "
            f"(ok ids: {sorted(ok_ids)})"
        )
    return choice, None


def _aggregate_usage(candidates: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    usage = _failed_usage()
    for candidate in candidates:
        for field in USAGE_FIELDS:
            usage[field] += candidate["usage"][field]
    return usage


def _record(
    *,
    run_id: Optional[str],
    condition: Optional[str],
    task: Mapping[str, Any],
    model: Any,
    seed: Any,
    prompt_version: Any,
    source_version: Any,
    instruction: Optional[str],
    candidates: List[Dict[str, Any]],
    synthesis: Optional[Dict[str, Any]] = None,
    selected_candidate_id: Optional[str],
    sources: Optional[List[str]] = None,
    transport_calls: int,
    status: str,
    error: Optional[str],
) -> Dict[str, Any]:
    """Assemble the one immutable shape every outcome is reported in."""
    record = {
        "run_id": run_id,
        "condition": condition,
        "task_id": task["id"],
        "model": model,
        "seed": seed,
        "prompt_version": prompt_version,
        "source_version": source_version,
        "instruction": instruction,
        "task": copy.deepcopy(dict(task)),
        "candidates": candidates,
        "selected_candidate_id": selected_candidate_id,
        "transport_calls": transport_calls,
        "usage": _aggregate_usage(candidates),
        "status": status,
        "cache_status": "miss",
        "created_by": "offline_runner",
        "error": error,
    }
    if synthesis is not None:
        record["synthesis"] = synthesis
    if sources is not None:
        # Provenance only: which sources were used, never their bodies.
        record["sources"] = list(sources)
    return record


def _invalid_condition_record(
    condition: Any,
    task: Mapping[str, Any],
    *,
    model: Any,
    seed: Any,
    prompt_version: Any,
    source_version: Any,
) -> Dict[str, Any]:
    record = _record(
        run_id=None,
        condition=condition if isinstance(condition, str) else None,
        task=task,
        model=model,
        seed=seed,
        prompt_version=prompt_version,
        source_version=source_version,
        instruction=None,
        candidates=[],
        selected_candidate_id=None,
        transport_calls=0,
        status="invalid_condition",
        error=f"condition {condition!r} is not one of {sorted(CONDITIONS)}",
    )
    # Nothing was run, so nothing can be replayed: a failed condition is never
    # written under a key that a real condition might own.
    return record


def run_condition(
    condition: str,
    task: Mapping[str, Any],
    *,
    model: str,
    prompt_version: str,
    source_version: str,
    seed: int,
    transport: Callable[[Dict[str, Any]], Any],
    cache_path: Union[str, Path],
    selector: Optional[Callable[[Sequence[Mapping[str, Any]]], Any]] = None,
) -> Dict[str, Any]:
    """Run one condition for one task and return an immutable run record.

    ``transport`` is the only way this function reaches a model: it receives a
    JSON-compatible request dict and must return a response dict with ``text``
    and optional ``usage``. ``selector`` is equally injectable and runs once,
    only for C; it receives the candidate records and returns a candidate id.
    """
    if not callable(transport):
        raise TypeError(
            f"transport must be callable, got {type(transport).__name__}"
        )
    if selector is not None and not callable(selector):
        raise TypeError(f"selector must be callable, got {type(selector).__name__}")

    validate_task(task)

    if not isinstance(condition, str) or condition not in CONDITIONS:
        return _invalid_condition_record(
            condition,
            task,
            model=model,
            seed=seed,
            prompt_version=prompt_version,
            source_version=source_version,
        )

    cache_key = condition_cache_key(
        model=model,
        condition=condition,
        task_id=task["id"],
        prompt_version=prompt_version,
        source_version=source_version,
        seed=seed,
    )
    run_id = _run_id(cache_key)
    cache = JsonlCache(cache_path)

    stored = cache.get(cache_key)
    if stored is not None:
        # Replay returns the stored record unchanged except for the cache
        # verdict, and reaches for neither the transport nor the selector.
        replay = copy.deepcopy(stored)
        replay["cache_status"] = "hit"
        return replay

    if condition == "D":
        material: Optional[Mapping[str, Any]] = deterministic_material(task["brief"], seed=seed)
    elif condition == "F":
        material = {"branches": branch_material(task["brief"], seed=seed, count=N)}
    else:
        material = None

    chosen_selector = selector if selector is not None else select_first
    branches = BRANCHES if condition in ("C", "E", "F") else (0,)

    candidates = [
        _call_branch(
            transport,
            condition=condition,
            task=task,
            model=model,
            prompt_version=prompt_version,
            source_version=source_version,
            seed=seed,
            branch=branch,
            material=material,
        )
        for branch in branches
    ]

    failures = [c for c in candidates if c["status"] != "ok"]
    if not failures:
        status = "ok"
    elif len(failures) == len(candidates):
        status = "transport_error"
    else:
        status = "partial"

    error = "; ".join(
        f"branch {c['branch']}: {c['error']}" for c in failures if c["error"]
    ) or None

    if condition == "E":
        # Nobody chooses here: E exists to show what branches do without a
        # selector. A blind judge compares the candidates later; the record says
        # plainly that no candidate was promoted.
        selected = None
    elif condition in ("C", "F"):
        selected, selector_error = _choose(chosen_selector, candidates)
        if selector_error:
            if status == "transport_error":
                # There was never a candidate to choose; keep the transport
                # verdict and add the selector complaint to the account.
                error = f"{error}; {selector_error}" if error else selector_error
            else:
                status = "selector_error"
                selected = None
                error = selector_error
    else:
        selected = (
            candidates[0]["candidate_id"] if candidates[0]["status"] == "ok" else None
        )

    synthesis: Optional[Dict[str, Any]] = None
    if condition == "F" and selected:
        synthesis = _synthesize(
            transport,
            task=task,
            model=model,
            prompt_version=prompt_version,
            source_version=source_version,
            seed=seed,
            candidate=next(c for c in candidates if c["candidate_id"] == selected),
        )
        if synthesis["status"] != "ok":
            status = "synthesis_error"
            error = f"{error}; synthesis: {synthesis['error']}" if error else f"synthesis: {synthesis['error']}"

    record = _record(
        run_id=run_id,
        condition=condition,
        task=task,
        model=model,
        seed=seed,
        prompt_version=prompt_version,
        source_version=source_version,
        instruction=INSTRUCTIONS[condition],
        sources=(
            [b["source_id"] for b in material["branches"]]
            if material and "branches" in material
            else (list(material.get("sources") or []) if material else None)
        ),
        candidates=candidates,
        synthesis=synthesis,
        selected_candidate_id=selected,
        transport_calls=len(branches) + (1 if synthesis is not None else 0),
        status=status,
        error=error,
    )

    # Only a clean run is evidence. Caching a failure would turn a transient
    # socket error into a permanent "result" that no retry could correct.
    if status == "ok":
        cache.put(cache_key, copy.deepcopy(record))

    return record
