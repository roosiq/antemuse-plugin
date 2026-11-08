"""One bounded exploration run, and the two audiences it serves.

A run produces two different things on purpose:

* the **model** gets candidates — mechanisms, a bridge question, a first step.
  That is the injected material, and it is not for the person to read;
* the **person** gets an account — what ran, how much came back, what was kept,
  what failed. One line, words, no candidate bodies.

Nothing raw crosses over. The account is built from counts and statuses, never
from candidate text, so there is no path where an injected mechanism leaks into
a human surface.

Deterministic by default: planning and selection here make no model call. The
branch runner (which does call the host) is a separate, explicitly awaited
entry, and nothing in a synchronous hook reaches for it.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from . import collider, collision, feedback, llm, orchestrator, selection, session

logger = logging.getLogger("antemuse")

DEFAULT_SEED = "spark"
DEFAULT_BUDGET = {"calls": 2, "tokens": 4000, "seconds": 60}
HUMAN_MAX_CHARS = 240
MODEL_MAX_CANDIDATES = 3

STATUS_OK = "ok"
STATUS_PARTIAL = "partial"
STATUS_ERROR = "error"
STATUS_DISABLED = "disabled"

_LOCK = threading.RLock()          # these books are read and written by hooks and by commands
_ACCOUNTS: Dict[str, str] = {}
_FEEDBACK: Dict[str, feedback.FeedbackStore] = {}
_LAST: Dict[str, List[str]] = {}
_GOAL: Dict[str, str] = {}
_SRC: Dict[str, Dict[str, List[str]]] = {}   # session -> candidate id -> source ids


@dataclass
class Run:
    """What one run did, in the two shapes its audiences need."""

    run_id: str
    method: str
    goal: str
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    kept: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    status: str = STATUS_OK
    selection_status: str = "unjudged"
    usage: Dict[str, Any] = field(default_factory=dict)
    branches: int = 0
    failed: int = 0
    skipped: int = 0
    error: str = ""

    def account(self) -> str:
        """The person's line: counts and statuses only, never candidate text."""
        # `/keep love #2` is unusable if no surface ever shows a number: the account
        # line publishes the range, the count stays the only quantity, and no candidate
        # text crosses to the person.
        n = len(self.candidates)
        listed = f"#{1}–#{n}" if n > 1 else ("#1" if n == 1 else "")
        parts = [f"{self.method} · {n} candidate(s)" + (f" {listed}" if listed else "")]
        if self.branches:
            parts.append(f"{self.branches} branch(es)")
        if self.failed:
            parts.append(f"{self.failed} failed")
        if self.skipped:
            parts.append(f"{self.skipped} skipped by budget")
        if self.kept:
            parts.append(f"{len(self.kept)} kept")
        if self.sources:
            parts.append(f"{len(self.sources)} source(s)")
        if self.selection_status != "judged":
            parts.append("unjudged")
        if self.status != STATUS_OK:
            parts.append(self.status)
        if self.usage.get("total_tokens"):
            parts.append(f"{int(self.usage['total_tokens'])} tokens")
        if self.error:
            parts.append(self.error[:60].rstrip() + ("…" if len(self.error) > 60 else ""))
        return " · ".join(parts)[:HUMAN_MAX_CHARS]

    def for_model(self) -> str:
        """The injected block. Bounded, attributed, and explicitly a candidate."""
        lines = [
            f"[EXPLORATION: {self.method} · {self.run_id} · the person sees only pictures]",
            f"Goal: {self.goal}",
        ]
        for candidate in self.kept[:MODEL_MAX_CANDIDATES]:
            thesis = str(candidate.get("thesis") or "").strip()
            mechanism = str(candidate.get("mechanism") or "").strip()
            step = str(candidate.get("first_step") or "").strip()
            lines.append(f"· {thesis}")
            if mechanism:
                lines.append(f"  mechanism: {mechanism[:240]}")
            if step:
                lines.append(f"  first step: {step[:200]}")
        lines.append(
            "Use, combine, or reject these. They are candidates from a transfer "
            "source, not findings; verify before asserting anything factual."
        )
        return "\n".join(lines)


def _budget(options: Mapping[str, Any]) -> llm.LlmBudget:
    raw = dict(options.get("budget") or {})
    merged = {**DEFAULT_BUDGET, **raw}
    return llm.LlmBudget(
        max_calls=int(merged["calls"]),
        max_output_tokens=int(merged["tokens"]),
        timeout_seconds=float(merged["seconds"]),
    )


def plan(goal: str, *, method: str = DEFAULT_SEED, options: Optional[Mapping[str, Any]] = None,
         artifacts: Optional[Sequence[Mapping[str, Any]]] = None,
         count: int = 2, strategy: str = "fresh",
         loved: Sequence[str] = (), liked: Sequence[str] = ()) -> Run:
    """The deterministic half: collide, clean up, select. No model call."""
    text = (goal or "").strip()
    if not text:
        raise ValueError("a run needs a goal")
    options = dict(options or {})
    seed = str(options.get("seed") or DEFAULT_SEED)
    bank = list(artifacts if artifacts is not None else collider.load_bank())

    result = collision.collide(
        {"id": text[:120], "brief": text}, bank, seed=seed, count=count,
        strategy=strategy, loved=loved, liked=liked,
    )
    selection_result = selection.select_for_synthesis(
        [c.to_dict() for c in result.candidates], count=min(count, len(result.candidates))
    )
    kept = list(selection_result.get("selected") or [])
    return Run(
        run_id=result.run_id,
        method=method,
        goal=text[:400],
        candidates=[c.to_dict() for c in result.candidates],
        kept=kept,
        sources=list(result.source_ids),
        status=STATUS_OK if kept else STATUS_PARTIAL,
        selection_status=str(selection_result.get("selection_status") or "unjudged"),
        usage=dict(result.usage or {}),
        error=str(selection_result.get("error") or ""),
    )


def _usage_dict(usage: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name in ("input_tokens", "output_tokens", "total_tokens", "cost_usd", "provider", "model"):
        value = getattr(usage, name, None)
        if value is not None:
            out[name] = value
    return out


async def run_branches(host: Any, goal: str, *, options: Optional[Mapping[str, Any]] = None,
                       artifacts: Optional[Sequence[Mapping[str, Any]]] = None,
                       method: str = DEFAULT_SEED, strategy: str = "fresh",
                       loved: Sequence[str] = (), liked: Sequence[str] = ()) -> Run:
    """The half that calls the host: one independent branch per selected source.

    This is the only place in the runtime that reaches for a model, and it is
    never called from a hook: `run_sync` is the entry point, and callers must
    have decided to spend a call before they get here.
    """
    text = (goal or "").strip()
    if not text:
        raise ValueError("a run needs a goal")
    if not callable(getattr(host, "acomplete_structured", None)):
        raise TypeError("host must expose an async acomplete_structured method")

    options = dict(options or {})
    seed = str(options.get("seed") or DEFAULT_SEED)
    budget = _budget(options)
    bank = list(artifacts if artifacts is not None else collider.load_bank())
    task = {"id": text[:120], "brief": text}

    result = await orchestrator.orchestrate(
        host,
        task=task,
        sources=bank,
        budget=budget,
        seed=seed,
        purpose="antemuse exploration",
        task_name="antemuse_generate",
        strategy=strategy,
        loved=loved,
        liked=liked,
    )

    parsed: List[Dict[str, Any]] = []
    for branch in result.branches:
        if not (branch.ok and isinstance(branch.parsed, dict)):
            continue
        candidate = dict(branch.parsed)
        # Provenance is the orchestrator's, never the model's: a branch that
        # writes its own source_ids or id must not be able to rewrite where it
        # came from. Both are assigned, not defaulted.
        candidate["candidate_id"] = branch.branch_id
        candidate["source_ids"] = list(branch.source_ids)
        parsed.append(candidate)
    failed = sum(1 for b in result.branches if not b.ok and b.status != llm.BUDGET)
    skipped = sum(1 for b in result.branches if b.status == llm.BUDGET)
    selection_result = selection.select_for_synthesis(parsed, count=min(2, len(parsed))) if parsed else {"selected": []}
    kept = list(selection_result.get("selected") or [])

    return Run(
        run_id=result.run_id,
        method=method,
        goal=text[:400],
        candidates=parsed,
        kept=kept,
        sources=[sid for b in result.branches for sid in b.source_ids],
        status=str(result.status),
        selection_status=str(selection_result.get("selection_status") or "unjudged"),
        usage=_usage_dict(result.usage),
        branches=len(result.branches),
        failed=failed,
        skipped=skipped,
        error=str(selection_result.get("error") or result.error or ""),
    )


def run_sync(host: Any, goal: str, *, options: Optional[Mapping[str, Any]] = None,
             artifacts: Optional[Sequence[Mapping[str, Any]]] = None,
             method: str = DEFAULT_SEED, strategy: str = "fresh",
             loved: Sequence[str] = (), liked: Sequence[str] = (),
             timeout_slack: float = 30.0) -> Run:
    """Run the branch path from synchronous code.

    A hook may already be inside an event loop; ``asyncio.run`` there would
    raise. In that case the coroutine is driven on its own loop in a worker
    thread, so the caller still gets a result and the host's loop is untouched.
    """
    def drive() -> Run:
        return asyncio.run(run_branches(
            host, goal, options=options, artifacts=artifacts, method=method,
            strategy=strategy, loved=loved, liked=liked,
        ))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return drive()

    # Inside a loop we cannot await, and a pool future cannot be cancelled: its
    # timeout fires and the pool's exit then blocks until the worker finishes
    # anyway, so the timeout would be decorative. The work runs on a daemon
    # thread and the caller waits a real deadline. A run that overruns has its
    # *result* discarded and says so, but a call already issued to the host
    # cannot be recalled: it finishes, and the host must tolerate that. This
    # path only happens when the caller is inside an event loop; command
    # handlers run on the gateway's pool thread, so they take the plain path.
    budget = _budget(dict(options or {}))
    deadline = float(budget.max_calls) * float(budget.timeout_seconds) + float(timeout_slack)
    box: Dict[str, Any] = {}
    done = threading.Event()

    def drive_bounded() -> None:
        try:
            box["run"] = drive()
        except BaseException as exc:  # noqa: BLE001 - handed back to the caller below
            box["error"] = exc
        finally:
            done.set()

    worker = threading.Thread(target=drive_bounded, name="antemuse-branches", daemon=True)
    worker.start()
    if not done.wait(deadline):
        raise TimeoutError(
            f"branches did not finish within {deadline:.0f}s; the result is discarded "
            "(a call already issued to the host still finishes)"
        )
    if "error" in box:
        raise box["error"]
    return box["run"]


def prepare(session_id: str, run: Run, origin: Optional[Mapping[str, Any]] = None) -> bool:
    """Bind a finished run to the session that asked for it.

    A run is only ever bound to a named session. There is no shared slot and no
    adoption: when the caller does not know which session it is in, the run is
    reported as unbound rather than parked where the next session could claim
    it. The host passes ``session_id`` to command handlers, so a real command
    always has one; an empty id means the caller had no session at all.
    """
    handles = " · ".join(f"#{i + 1}" for i in range(len(run.kept)))
    account = run.account() + (f" · kept {handles}" if handles else "")
    payload = {"run": run, "model": run.for_model(), "account": account,
               "origin": dict(origin or {})}

    key = (session_id or "").strip()
    if not key:
        logger.warning("antemuse: run %s prepared with no session id; not bound", run.run_id[:16])
        return False
    with _LOCK:
        _GOAL[key] = run.goal
        _LAST[key] = [str(c.get("candidate_id") or "") for c in run.kept]
        _SRC[key] = {str(c.get("candidate_id") or ""): list(c.get("source_ids") or [])
                     for c in list(run.kept) + list(run.candidates)}
    return session.bind(key, payload)


def injection(session_id: str, origin: Optional[Mapping[str, Any]] = None) -> Optional[str]:
    """Consume this session's prepared material for the model.

    The account is left behind for the reply footer: the model is handed the
    candidates, the person is handed the count.
    """
    key = (session_id or "").strip()
    if not key:
        return None
    payload = session.take(key)
    if not payload:
        return None

    prepared = payload.get("origin") or {}
    arrived = dict(origin or {})
    if (prepared.get("project") and arrived.get("project")
            and prepared["project"] != arrived["project"]):
        # Dropped, not rerouted: the run belongs to the project that asked for
        # it, and another project's turn must not receive its candidates.
        logger.warning("antemuse: dropping run prepared in %r, turn arrived in %r",
                       prepared["project"], arrived["project"])
        return None

    with _LOCK:
        _ACCOUNTS[key] = str(payload.get("account") or "")
    return str(payload.get("model") or "") or None


def take_account(session_id: str) -> Optional[str]:
    key = (session_id or "").strip()
    with _LOCK:
        return _ACCOUNTS.pop(key, None)


def keep(session_id: str, verdict: str, ref: str, note: str = "") -> str:
    """Record what the person thought of one candidate.

    The person never sees candidate text, so they address one by its handle
    (`#1`) from the run's account. A full candidate id still works.
    """
    key = (session_id or "").strip()
    candidate_id = (ref or "").strip()
    with _LOCK:
        if candidate_id.startswith("#") or candidate_id.isdigit():
            index = int(candidate_id.lstrip("#")) - 1
            known = _LAST.get(key) or []
            if not 0 <= index < len(known):
                return f"no candidate {ref} · the last run offered {len(known)}"
            candidate_id = known[index]
        store = _FEEDBACK.setdefault(key, feedback.FeedbackStore())
    try:
        store.record(candidate_id, verdict, note)
    except ValueError as exc:
        return f"not kept · {exc}"
    return f"kept as {verdict} · {ref} → {candidate_id}"


def last_goal(session_id: str) -> Optional[str]:
    """The goal of this session's most recent run, so feedback can re-run it."""
    key = (session_id or "").strip()
    with _LOCK:
        return _GOAL.get(key) if key else None


def feedback_ids(session_id: str) -> Dict[str, List[str]]:
    """The source ids the person has backed, in the shape the strategies filter by.

    A verdict is recorded against a candidate id, and those read
    ``<task>::<source>``; selection filters by the bank's own artifact ids, so
    the mapping is resolved here rather than guessed by the caller.
    """
    key = (session_id or "").strip()
    with _LOCK:
        store = _FEEDBACK.get(key)
        sources = dict(_SRC.get(key) or {})

    def resolve(ids: Any) -> List[str]:
        out: List[str] = []
        for candidate_id in sorted(ids):
            out.extend(sources.get(candidate_id) or [])
        return sorted(set(out))

    if store is None:
        return {"loved": [], "liked": []}
    return {"loved": resolve(store.ids(loved=True)), "liked": resolve(store.ids(liked=True))}


def next_strategy(session_id: str) -> Optional[str]:
    """What the person's feedback routes to next, or None when there is none.

    Routing is decided here; *generating* from it is the branch runner's job and
    is not wired yet, so this reports rather than runs.
    """
    key = (session_id or "").strip()
    if not key:
        return None
    with _LOCK:
        store = _FEEDBACK.get(key)
    if store is None:
        return None
    if store.ids(loved=True):
        return "deepen"
    if store.ids(liked=True):
        return "refresh"
    return None


def release(session_id: str) -> None:
    """Forget everything this session prepared: material, verdicts, goal, account.

    It releases the bound material as well as the runtime's own books, so one
    call is the whole cleanup and a caller cannot leave half of it behind.
    """
    key = (session_id or "").strip()
    with _LOCK:
        for book in (_ACCOUNTS, _FEEDBACK, _LAST, _GOAL, _SRC):
            book.pop(key, None)
    if key:
        session.release(key)


def clear(session_id: str = "") -> None:
    """Forget this session's runs, accounts, and feedback."""
    with _LOCK:
        if session_id:
            for book in (_ACCOUNTS, _FEEDBACK, _LAST, _GOAL, _SRC):
                book.pop(session_id, None)
            return
        _ACCOUNTS.clear()
        _FEEDBACK.clear()
        _LAST.clear()
        _GOAL.clear()
        _SRC.clear()

