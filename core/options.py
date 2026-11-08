"""Optional enter fields: method, seed, budget.

These are the experimental exploration options. They are validated here and
nowhere else, deterministically, so an invalid request never reaches an entry
and never leaves a half-open state behind.

Absent means today's behaviour: an entry with no options is the same walk,
daydream, doomscroll, or dream it has always been.
"""
from __future__ import annotations

from typing import Any, Dict

METHODS = ("collide", "deep", "chaos", "spark")

# (name, low, high) — bounded so a budget cannot become an unbounded run.
BUDGET_FIELDS = (("calls", 0, 32), ("tokens", 0, 200_000), ("seconds", 1, 900))

SEED_MAX_CHARS = 64


def parse(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return the normalised options, or raise ``ValueError`` naming the field."""
    out: Dict[str, Any] = {}

    method = str(args.get("method") or "").strip().lower()
    if method:
        if method not in METHODS:
            raise ValueError(f"method must be one of {', '.join(METHODS)}")
        out["method"] = method

    seed = args.get("seed")
    if seed not in (None, ""):
        if isinstance(seed, bool) or not isinstance(seed, (int, str)):
            raise ValueError("seed must be an integer or a string")
        text = str(seed).strip()
        if not text:
            raise ValueError("seed must not be blank")
        if len(text) > SEED_MAX_CHARS:
            raise ValueError(f"seed must be at most {SEED_MAX_CHARS} characters")
        out["seed"] = text

    budget = args.get("budget")
    if budget not in (None, ""):
        if not isinstance(budget, dict):
            raise ValueError("budget must be an object with calls, tokens, seconds")
        unknown = sorted(set(budget) - {name for name, _low, _high in BUDGET_FIELDS})
        if unknown:
            raise ValueError(f"budget does not take {', '.join(unknown)}")
        clean: Dict[str, int] = {}
        for name, low, high in BUDGET_FIELDS:
            if name not in budget:
                continue
            value = budget[name]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"budget.{name} must be an integer between {low} and {high}")
            if not low <= value <= high:
                raise ValueError(f"budget.{name} must be an integer between {low} and {high}")
            clean[name] = value
        if not clean:
            raise ValueError("budget must name at least one of calls, tokens, seconds")
        out["budget"] = clean

    # A state does not take tools away unless the caller said so. `block` is the
    # whole switch; `allow` exists so a caller can narrow the set without editing
    # core/states.py, and is meaningless (and refused) without `block`.
    block = args.get("block")
    if block not in (None, ""):
        if not isinstance(block, bool):
            raise ValueError("block must be true or false")
        out["block"] = block

    allow = args.get("allow")
    if allow not in (None, "", [], ()):
        if not out.get("block"):
            raise ValueError("allow needs block: true — without it every tool stays open")
        if isinstance(allow, str):
            allow = allow.split(",")
        if not isinstance(allow, (list, tuple)):
            raise ValueError("allow must be a list of tool names")
        names = [str(a).strip() for a in allow if str(a).strip()]
        if not names:
            raise ValueError("allow must name at least one tool")
        out["allow"] = names

    return out
