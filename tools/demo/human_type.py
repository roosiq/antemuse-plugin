#!/usr/bin/env python3
"""Type into a tmux pane at a human pace, with one honest correction.

The demo needs a person using Hermes, not a script emitting commands: varied
inter-key timing, longer pauses at word boundaries, an occasional typo that is
backspaced. This drives the real session through `tmux send-keys`, so what the
camera sees is a real keystroke stream, not a pasted line.

Usage:
    python3 tools/demo/human_type.py <tmux-session> "text to type" [--seed 7] [--typo]

The typo is deterministic for a given seed and always corrected before Enter, so
a retake looks the same as the take.
"""
from __future__ import annotations

import argparse
import random
import string
import subprocess
import sys
import time


def send(session: str, text: str) -> None:
    subprocess.run(["tmux", "send-keys", "-t", session, "-l", text], check=True)


def press(session: str, key: str) -> None:
    subprocess.run(["tmux", "send-keys", "-t", session, key], check=True)


def human_type(session: str, text: str, seed: int = 7, typo: bool = False) -> None:
    rng = random.Random(seed)
    typo_at: int | None = None
    if typo and len(text) > 12:
        # land the typo in the middle of a word, where real typos happen
        typo_at = rng.randrange(len(text) // 3, 2 * len(text) // 3)

    for i, ch in enumerate(text):
        if typo_at is not None and i == typo_at:
            wrong = rng.choice([c for c in string.ascii_lowercase if c != ch.lower()])
            send(session, wrong)
            time.sleep(rng.uniform(0.18, 0.34))   # notice it
            press(session, "BSpace")
            time.sleep(rng.uniform(0.10, 0.20))
        send(session, ch)
        if ch == " ":
            time.sleep(rng.uniform(0.10, 0.26))
        elif ch in ".,;:/":
            time.sleep(rng.uniform(0.09, 0.18))
        else:
            time.sleep(rng.uniform(0.045, 0.145))


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("session")
    p.add_argument("text")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--typo", action="store_true")
    p.add_argument("--enter", action="store_true", help="press Enter after typing")
    a = p.parse_args(argv)
    human_type(a.session, a.text, a.seed, a.typo)
    if a.enter:
        time.sleep(a_random_pause())
        press(a.session, "Enter")
    return 0


def a_random_pause() -> float:
    return random.Random(time.time_ns() % 1000).uniform(0.35, 0.9)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
