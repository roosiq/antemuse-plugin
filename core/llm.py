"""Auxiliary model calls: several branches, one small budget, no surprises.

A state may want three readings of the same material at once. The host owns
the model, the provider and the key; Antemuse owns only the shape of the ask
and the ceiling on what it may cost. Every call is bounded by a call count, an
output-token ceiling and a wall-clock timeout, and every branch comes back as
a result that names its own outcome -- including the branches that were never
run because the budget ran out.

Nothing here imports Hermes, registers a hook or reaches the network. The host
is injected: any object whose ``acomplete_structured`` matches ``ctx.llm``.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

#: Statuses a branch can end in. ``budget`` means it was never called.
OK = "ok"
INVALID = "invalid"
TIMEOUT = "timeout"
ERROR = "error"
BUDGET = "budget"
STATUSES = (OK, INVALID, TIMEOUT, ERROR, BUDGET)

#: Error strings are short enough to sit in a log line, and no longer.
MAX_ERROR_CHARS = 300

#: The schema is checked by hand. Only the first few required keys are read:
#: enough to catch a model that answered a different question, not a validator.
REQUIRED_KEY_LIMIT = 8

_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{6,}")
_API_KEY = re.compile(r"(?i)\bapi[_-]?key[\"']?\s*[:=]\s*[\"']?([^\s\"',;}]+)")
_SK_KEY = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}")


class BudgetError(ValueError):
    """The budget is not a budget."""


@dataclass(frozen=True)
class LlmBudget:
    """The ceiling for one ``generate_structured`` call.

    These are per-invocation limits on calls, output tokens and time. They are
    not a global quota, a spend cap or a financial claim.
    """

    max_calls: int
    max_output_tokens: int
    timeout_seconds: float
    max_concurrency: Optional[int] = None

    def __post_init__(self) -> None:
        if isinstance(self.max_calls, bool) or not isinstance(self.max_calls, int):
            raise BudgetError("max_calls must be an integer")
        if self.max_calls < 1:
            raise BudgetError("max_calls must be at least 1")
        if isinstance(self.max_output_tokens, bool) or not isinstance(
            self.max_output_tokens, int
        ):
            raise BudgetError("max_output_tokens must be an integer")
        if self.max_output_tokens < 1:
            raise BudgetError("max_output_tokens must be at least 1")
        if isinstance(self.timeout_seconds, bool) or not isinstance(
            self.timeout_seconds, (int, float)
        ):
            raise BudgetError("timeout_seconds must be a number")
        if self.timeout_seconds <= 0:
            raise BudgetError("timeout_seconds must be greater than 0")
        if self.max_concurrency is not None:
            if isinstance(self.max_concurrency, bool) or not isinstance(
                self.max_concurrency, int
            ):
                raise BudgetError("max_concurrency must be an integer or None")
            if self.max_concurrency < 1:
                raise BudgetError("max_concurrency must be at least 1")


@dataclass(frozen=True)
class Usage:
    """What the host says a call used. Unknown stays unknown.

    Missing fields become zero; missing provider or model become ``"unknown"``.
    A zero here means the host did not report it, never that the call was free.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: Optional[float] = None
    provider: str = "unknown"
    model: str = "unknown"

    def __post_init__(self) -> None:
        for name in ("input_tokens", "output_tokens", "total_tokens"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.cost_usd is not None:
            if isinstance(self.cost_usd, bool) or not isinstance(
                self.cost_usd, (int, float)
            ):
                raise ValueError("cost_usd must be a number or None")
            if self.cost_usd < 0:
                raise ValueError("cost_usd must be non-negative")
        for name in ("provider", "model"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")

    @classmethod
    def from_host_result(cls, result: Any) -> "Usage":
        """Read ``result.usage`` if it is there, and never fill in a number."""
        raw = _attr(result, "usage")
        if raw is None:
            return cls()

        input_tokens = _token_count(_attr(raw, "input_tokens"))
        output_tokens = _token_count(_attr(raw, "output_tokens"))
        reported_total = _token_count(_attr(raw, "total_tokens"))
        # A total the host did not report is the sum of the parts it did report.
        # With no parts, that sum is zero -- no number is invented.
        total_tokens = reported_total if reported_total is not None else (
            (input_tokens or 0) + (output_tokens or 0)
        )
        cost = _attr(raw, "cost_usd")
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0:
            cost = None

        return cls(
            input_tokens=input_tokens or 0,
            output_tokens=output_tokens or 0,
            total_tokens=total_tokens,
            cost_usd=float(cost) if cost is not None else None,
            provider=_name(_attr(result, "provider")),
            model=_name(_attr(result, "model")),
        )


@dataclass(frozen=True)
class BranchResult:
    """One branch's outcome, whatever it was.

    ``raw_text`` is the model's own text when the host returned one. It is
    never a prompt. ``error`` is sanitized: no keys, no tokens, no request.
    """

    branch_id: str
    status: str
    parsed: Optional[Any] = None
    raw_text: str = ""
    usage: Usage = field(default_factory=Usage)
    error: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"unknown branch status: {self.status!r}")
        if not isinstance(self.branch_id, str) or not self.branch_id:
            raise ValueError("branch_id must be a non-empty string")
        if not isinstance(self.raw_text, str):
            raise ValueError("raw_text must be a string")

    @property
    def ok(self) -> bool:
        return self.status == OK


# ------------------------------------------------------------------ normalize

InputBlock = Union[str, Mapping[str, Any]]


def _branch_ids(branches: Union[int, Sequence[str]]) -> List[str]:
    """Branch ids from a count or a sequence, in the order given."""
    if isinstance(branches, bool):
        raise ValueError("branches must be a count or a sequence of branch ids")
    if isinstance(branches, int):
        if branches < 1:
            raise ValueError("branches must be at least 1")
        return [f"branch-{i + 1}" for i in range(branches)]
    if isinstance(branches, (str, bytes)) or not isinstance(branches, Sequence):
        raise ValueError("branches must be a count or a sequence of branch ids")

    ids: List[str] = []
    for item in branches:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("each branch id must be a non-empty string")
        if item in ids:
            raise ValueError(f"duplicate branch id: {item!r}")
        ids.append(item)
    if not ids:
        raise ValueError("branches must not be empty")
    return ids


def _blocks_for(branch_id: str, item: Any) -> List[Dict[str, Any]]:
    """One branch's input blocks, normalized the way the host expects them."""
    if item is None:
        raise ValueError(f"branch {branch_id!r} has no input block")
    if isinstance(item, (str, bytes)):
        item = [item]

    if isinstance(item, Mapping):
        blocks = [item]
    elif isinstance(item, Sequence):
        blocks = list(item)
    else:
        raise ValueError(f"branch {branch_id!r} input must be text or input blocks")
    if not blocks:
        raise ValueError(f"branch {branch_id!r} has an empty input block list")

    out: List[Dict[str, Any]] = []
    for block in blocks:
        if isinstance(block, str):
            out.append({"type": "text", "text": block})
        elif isinstance(block, Mapping):
            out.append(dict(block))
        else:
            raise ValueError(
                f"branch {branch_id!r} input block must be text or an input block dict"
            )
    return out


def _branch_inputs(
    ids: Sequence[str], inputs: Union[Mapping[str, Any], Sequence[Any]]
) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """Pair each branch id with its own blocks. No sharing, no borrowing."""
    if isinstance(inputs, Mapping):
        pairs = []
        for branch_id in ids:
            if branch_id not in inputs:
                raise ValueError(f"no input block for branch {branch_id!r}")
            pairs.append((branch_id, _blocks_for(branch_id, inputs[branch_id])))
        return pairs

    if isinstance(inputs, (str, bytes)) or not isinstance(inputs, Sequence):
        raise ValueError("inputs must be a mapping of branch id to block, or a sequence")
    if len(inputs) != len(ids):
        raise ValueError(
            f"inputs has {len(inputs)} entries for {len(ids)} branches"
        )
    return [(branch_id, _blocks_for(branch_id, inputs[i])) for i, branch_id in enumerate(ids)]


def _branch_instructions(instructions: str, branch_id: str) -> str:
    """The shared ask plus which branch this is. Branches must not look alike."""
    return (
        f"{instructions.rstrip()}\n\n"
        f"Branch: {branch_id}\n"
        "Answer this branch only. Return one JSON object."
    )


# -------------------------------------------------------------------- results

def _attr(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)


def _token_count(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _name(value: Any) -> str:
    return value if isinstance(value, str) and value.strip() else "unknown"


def _required_keys(schema: Any) -> List[str]:
    """The first few top-level required keys, if the schema names any."""
    if not isinstance(schema, Mapping):
        return []
    required = schema.get("required")
    if not isinstance(required, Sequence) or isinstance(required, (str, bytes)):
        return []
    keys = [key for key in required if isinstance(key, str) and key]
    return keys[:REQUIRED_KEY_LIMIT]


def _result_from(branch_id: str, host_result: Any, schema: Any) -> BranchResult:
    """Trust the host's parsed object only if it is a JSON object of the right shape."""
    text = _attr(host_result, "text")
    raw_text = text if isinstance(text, str) else ""
    usage = Usage.from_host_result(host_result)

    if host_result is None:
        return BranchResult(
            branch_id, INVALID, raw_text=raw_text, usage=usage,
            error="host returned no result",
        )

    parsed = _attr(host_result, "parsed")
    if not isinstance(parsed, dict):
        return BranchResult(
            branch_id, INVALID, raw_text=raw_text, usage=usage,
            error="parsed result is not a JSON object",
        )

    missing = [key for key in _required_keys(schema) if key not in parsed]
    if missing:
        return BranchResult(
            branch_id, INVALID, raw_text=raw_text, usage=usage,
            error="missing required key(s): " + ", ".join(missing),
        )

    return BranchResult(branch_id, OK, parsed=parsed, raw_text=raw_text, usage=usage)


def _sanitize_error(exc: BaseException, hidden: Iterable[str] = ()) -> str:
    """An error line fit to log: short, prompt-free, key-free."""
    text = f"{type(exc).__name__}: {exc}"
    for secret in hidden:
        if isinstance(secret, str) and len(secret) >= 8:
            text = text.replace(secret, "[prompt]")
    text = _BEARER.sub("Bearer [redacted]", text)
    text = _API_KEY.sub("api_key=[redacted]", text)
    text = _SK_KEY.sub("[redacted]", text)
    if len(text) > MAX_ERROR_CHARS:
        text = text[: MAX_ERROR_CHARS - 3].rstrip() + "..."
    return text


# ------------------------------------------------------------------ the call

async def _invoke_host(
    host: Any,
    *,
    prompt: str,
    blocks: List[Dict[str, Any]],
    json_schema: Any,
    budget: LlmBudget,
    purpose: Optional[str],
    task: Optional[str],
) -> Any:
    """Make one host call and time it from the moment it is actually made.

    The coroutine is created here and handed straight to ``wait_for``, so it is
    driven on every path: completed, cancelled by the deadline, or drained when
    the caller cancels us. Nothing is created until a slot is already held, so
    a branch that is still queued cannot leave an un-awaited coroutine behind,
    and the deadline never covers time spent waiting for a slot.
    """
    pending = asyncio.ensure_future(
        host.acomplete_structured(
            instructions=prompt,
            input=blocks,
            json_schema=json_schema,
            max_tokens=budget.max_output_tokens,
            timeout=budget.timeout_seconds,
            purpose=purpose,
            task=task,
        )
    )
    try:
        return await asyncio.wait_for(pending, timeout=budget.timeout_seconds)
    finally:
        # ``wait_for`` cancels what it bounded; an outside cancellation may
        # arrive first, so close the call ourselves rather than leak it.
        if not pending.done():
            pending.cancel()
            try:
                await pending
            except (asyncio.CancelledError, Exception):
                pass


async def _call_one(
    host: Any,
    branch_id: str,
    blocks: List[Dict[str, Any]],
    *,
    instructions: str,
    json_schema: Any,
    budget: LlmBudget,
    purpose: Optional[str],
    task: Optional[str],
    semaphore: Optional[asyncio.Semaphore],
    hidden: Iterable[str],
) -> BranchResult:
    prompt = _branch_instructions(instructions, branch_id)

    try:
        if semaphore is None:
            host_result = await _invoke_host(
                host,
                prompt=prompt,
                blocks=blocks,
                json_schema=json_schema,
                budget=budget,
                purpose=purpose,
                task=task,
            )
        else:
            # The slot is taken first and only then is the call made, so the
            # timeout below is a per-call deadline, not a deadline from enqueue.
            async with semaphore:
                host_result = await _invoke_host(
                    host,
                    prompt=prompt,
                    blocks=blocks,
                    json_schema=json_schema,
                    budget=budget,
                    purpose=purpose,
                    task=task,
                )
    except asyncio.CancelledError:
        raise
    except (asyncio.TimeoutError, TimeoutError):
        return BranchResult(
            branch_id, TIMEOUT,
            error=f"timed out after {budget.timeout_seconds:g}s",
        )
    except Exception as exc:  # the host failed; that is a branch outcome, not a crash
        return BranchResult(branch_id, ERROR, error=_sanitize_error(exc, hidden))

    return _result_from(branch_id, host_result, json_schema)


async def generate_structured(
    host: Any,
    *,
    instructions: Union[str, Mapping[str, str]],
    inputs: Union[Mapping[str, Any], Sequence[Any]],
    json_schema: Any,
    branches: Union[int, Sequence[str]],
    budget: LlmBudget,
    purpose: Optional[str] = None,
    task: Optional[str] = None,
) -> List[BranchResult]:
    """Run up to ``budget.max_calls`` structured branches, concurrently.

    Each branch gets its own input blocks and its own branch marker in the
    instructions. Branches past ``max_calls`` are not run; each one still gets
    a ``budget`` result so the caller can tell skipped from failed.

    The host owns provider, model and key selection: those are never overridden
    here. The returned list is in the order the branches were asked for.
    """
    if not isinstance(host, object) or not callable(
        getattr(host, "acomplete_structured", None)
    ):
        raise TypeError("host must expose an async acomplete_structured method")
    if not isinstance(budget, LlmBudget):
        raise TypeError("budget must be an LlmBudget")
    if isinstance(instructions, str):
        if not instructions.strip():
            raise ValueError("instructions must be non-empty text")
    elif isinstance(instructions, Mapping):
        if not instructions:
            raise ValueError("instructions must not be empty")
        for branch_id, instruction in instructions.items():
            if not isinstance(branch_id, str) or not branch_id.strip():
                raise ValueError("each instruction branch id must be non-empty text")
            if not isinstance(instruction, str) or not instruction.strip():
                raise ValueError(f"instructions for {branch_id!r} must be non-empty text")
    else:
        raise TypeError("instructions must be text or a mapping of branch id to text")

    ids = _branch_ids(branches)
    paired = _branch_inputs(ids, inputs)
    if isinstance(instructions, Mapping):
        missing = [branch_id for branch_id in ids if branch_id not in instructions]
        if missing:
            raise ValueError("missing instructions for branch(es): " + ", ".join(missing))

    run, skipped = paired[: budget.max_calls], paired[budget.max_calls:]
    semaphore = (
        asyncio.Semaphore(budget.max_concurrency)
        if budget.max_concurrency is not None
        else None
    )

    hidden = [instructions] if isinstance(instructions, str) else list(instructions.values())
    for _, blocks in paired:
        hidden.extend(block.get("text", "") for block in blocks if isinstance(block.get("text"), str))

    results = await asyncio.gather(
        *(
            _call_one(
                host, branch_id, blocks,
                instructions=instructions if isinstance(instructions, str) else instructions[branch_id],
                json_schema=json_schema,
                budget=budget,
                purpose=purpose,
                task=task,
                semaphore=semaphore,
                hidden=hidden,
            )
            for branch_id, blocks in run
        )
    )

    out = list(results)
    for branch_id, _ in skipped:
        out.append(
            BranchResult(
                branch_id, BUDGET,
                error=(
                    f"not run: budget.max_calls={budget.max_calls} "
                    f"and {len(ids)} branches were asked for"
                ),
            )
        )
    return out
