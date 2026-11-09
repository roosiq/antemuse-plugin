#!/usr/bin/env python3
"""Run one block of the state-settings experiment, entry by entry.

    python3 tools/experiment_run.py --state walk --block 0 --entries 8 --dry-run
    python3 tools/experiment_run.py --state walk --block 0 --entries 8

Each entry: clear the state, take the arm the preregistration assigns, enter the state at
that arm's dose, run the dose's turns as real `hermes chat -q` sessions in a scratch repo,
then compute the primary outcome with `tools/experiment_outcome.compute` and append one
ledger line.

The control arm enters no state. Its material is still generated and logged (with
`sources.PROVIDERS`) and discarded unshown, so its cost is comparable.

This runner does not decide anything statistical and never edits a default; it produces
ledger lines and refuses to produce a line it cannot defend.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))

from core import engine, sources, states  # noqa: E402
from tools import experiment_outcome  # noqa: E402

LEDGER = ROOT / "experiments" / "state-settings" / "ledger.jsonl"

# The preregistered seeds; a state's permutation is not chosen here.
SEEDS = {
    "walk": 3497679622,
    "daydream": 18095054,
    "doomscroll": 751586276,
    "dream": 3399968528,
    "unstuck": 1739374009,
}

# Crossed settings, alternated between blocks (preregistration §"Crossed settings").
CROSSED = [(45, 0), (120, 0), (45, 90), (120, 90)]

ARMS = ["half", "default", "double", "control"]

TASK = (
    "You are working in a small scratch repository. Pick one concrete improvement the code "
    "or docs need, make it, and say in one or two sentences what you changed. Work in this "
    "directory only."
)


def arms_for(state: str, block: int) -> list[str]:
    """Two entries per arm, order fixed by the preregistered seed."""
    pool = ARMS + ARMS
    if state == "unstuck":
        pool = ["default", "default", "double", "double", "control", "control"]
    rng = random.Random(SEEDS[state])
    rng.shuffle(pool)          # the whole permutation is fixed, not just this block
    start = (block * 8) % len(pool)
    chosen = pool[start:] + pool[:start]
    return chosen[: (8 if state != "unstuck" else 6)]


def dose_for(state: str, arm: str) -> int:
    n = int(states.STATES[state]["dose"]["n"])
    if arm == "half":
        return max(1, n // 2)
    if arm == "double":
        return n * 2
    if arm == "control":
        return 0
    return n


# Amendment 2026-11-08: the ceiling is a safety limit, not the treatment. At ~40-70 s per
# real turn a state's default ceiling truncates before its dose, so every arm runs at 2x.
CEILING_MULT = 2


def ceiling_for(state: str, arm: str) -> int:
    base = int(states.STATES[state]["minutes"]) * CEILING_MULT
    return base * 2 if arm == "double" else base


def run_turn(prompt: str, workdir: Path) -> tuple[str, dict, float]:
    cmd = ["hermes", "chat", "-q", prompt, "--format", "stream-json"]
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=900)
    text, tokens = "", {"input": 0, "output": 0}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "text":
            text += event.get("text") or ""
        elif event.get("type") == "result":
            text = event.get("text") or text
            tokens = event.get("tokens") or tokens
    return text, tokens, time.time() - t0


def material_lines(key: str, since: float) -> list[str]:
    data = engine.data_for_advice()
    return [e["text"] for e in (data.get("journal") or [])
            if e.get("who") == "state" and e.get("state") == key and e.get("at", 0) >= since]


def scratch_repo(path: Path) -> Path:
    if not (path / ".git").exists():
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        (path / "README.md").write_text("# scratch\n\nA small project used as the setting "
                                        "for an experiment.\n")
        (path / "app.py").write_text("def greet(name):\n    return 'hi ' + name\n")
    return path


def run_entry(state: str, arm: str, block: int, workdir: Path, model: str,
              provider: str, dry: bool) -> dict:
    dose = dose_for(state, arm)
    ceiling = ceiling_for(state, arm)
    cooling, stretch = CROSSED[block % len(CROSSED)]

    engine.clear()
    started = time.time()
    material: list[str] = []
    text = ""
    tokens = {"input": 0, "output": 0}
    turns = 0
    tool_failures = 0

    if arm == "control":
        provider_fn = sources.PROVIDERS.get(state)
        if provider_fn:
            try:
                material = list(provider_fn(1))     # generated, logged, never shown
            except Exception as exc:
                material = [f"{state} provider failed · {exc}"]
        if not dry:
            for _ in range(max(1, int(states.STATES[state]["dose"]["n"]))):
                out, tok, _ = run_turn(TASK, workdir)
                text += out
                tokens = {"input": tokens["input"] + tok.get("input", 0),
                          "output": tokens["output"] + tok.get("output", 0)}
                turns += 1
    else:
        os.environ["ANTEMUSE_EXPERIMENT"] = "1"     # the arm's dose, never the default
        engine.enter(state, ceiling, dose=dose)
        entered = time.time()
        for _ in range(dose):
            engine.note_turn()
            engine.deliver_if_due()
            if engine.peek() is None:
                break
            if dry:
                turns += 1
                continue
            out, tok, _ = run_turn(TASK, workdir)
            text += out
            tokens = {"input": tokens["input"] + tok.get("input", 0),
                      "output": tokens["output"] + tok.get("output", 0)}
            turns += 1
            if engine.peek() is None:
                break
        material = material_lines(state, entered)
        if engine.peek() is not None:
            engine.stop(engine.current_session(), reason="expired")

    ending = "complete"
    data = engine.data_for_advice()
    reports = [e for e in (data.get("journal") or []) if e.get("event") == "report"]
    if reports:
        ending = str(reports[-1].get("reason") or "expired")

    outcome = None
    if not dry:
        outcome = experiment_outcome.compute(state, text, material, {"direction": material[0] if material else ""})

    return {
        "session_id": f"exp-{state}-{block}-{arm}-{int(started)}",
        "model": model,
        "provider": provider,
        "state": state,
        "arm": arm,
        "ending_reason": "abandoned" if (not dry and turns == 0) else ending,
        "block_seed": SEEDS[state],
        "dose": dose,
        "ceiling_minutes": ceiling,
        "entered_at": started,
        "turns": turns,
        "seconds_to_dose": int(time.time() - started),
        "tokens_in": int(tokens.get("input") or (1 if dry else 0)),
        "tokens_out": int(tokens.get("output") or (1 if dry else 0)),
        "tool_failures": tool_failures,
        "tool_blocks": 0,
        "cooling_minutes": cooling,
        "long_stretch_minutes": stretch,
        "outcome": True if dry else outcome,
        "excluded": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True, choices=sorted(SEEDS))
    ap.add_argument("--block", type=int, default=0)
    ap.add_argument("--entries", type=int, default=8)
    ap.add_argument("--workdir", default="/tmp/antemuse-exp-scratch")
    ap.add_argument("--model", default=os.environ.get("HERMES_MODEL", "session-default"))
    ap.add_argument("--provider", default=os.environ.get("HERMES_PROVIDER", "session-default"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--label", default="", help="e.g. pilot — recorded in the ledger line")
    ap.add_argument("--start", type=int, default=0,
                    help="skip the first N entries of the block (resume after a crash)")
    args = ap.parse_args()

    workdir = scratch_repo(Path(args.workdir))
    assignment = arms_for(args.state, args.block)
    rows = []
    todo = assignment[args.start: args.start + args.entries]
    for i, arm in enumerate(todo, start=args.start):
        print(f"[{i + 1}/{args.start + len(todo)}] {args.state} · {arm}", flush=True)
        row = run_entry(args.state, arm, args.block, workdir, args.model, args.provider,
                        args.dry_run)
        if args.label:
            row["label"] = args.label
        rows.append(row)
        if not args.dry_run:
            LEDGER.parent.mkdir(parents=True, exist_ok=True)
            with LEDGER.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
        print(f"    outcome={row['outcome']} turns={row['turns']} "
              f"tokens={row['tokens_in']}/{row['tokens_out']}", flush=True)

    if args.dry_run:
        print(json.dumps(rows, indent=2)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
