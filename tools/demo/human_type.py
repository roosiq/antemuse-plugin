#!/usr/bin/env python3
"""Type at a human pace, with one honest correction, and make it visible.

The demo needs a person using Hermes, not a script emitting commands: varied
inter-key timing, longer pauses at word boundaries, one typo that is backspaced.

Two drivers:

- ``--via tmux`` writes to a tmux pane. Deterministic, but it never produces an X
  key event, so a keystroke overlay (screenkey) shows nothing.
- ``--via xdotool`` types into the focused X window, so every character is a real
  X key event: screenkey displays it and the recorded pointer stays live. The
  demo uses this one, because the keystrokes have to be visible on screen.

Usage:
    python3 tools/demo/human_type.py <tmux-session> "text" --via tmux [--typo]
    python3 tools/demo/human_type.py - "text" --via xdotool [--typo] [--enter]

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


def send(session: str, text: str, via: str = "tmux") -> None:
    if via == "tmux":
        subprocess.run(["tmux", "send-keys", "-t", session, "-l", text], check=True)
    else:
        subprocess.run(
            ["xdotool", "type", "--delay", "0", "--clearmodifiers", "--", text],
            check=True,
        )


def press(session: str, key: str, via: str = "tmux") -> None:
    if via == "tmux":
        subprocess.run(["tmux", "send-keys", "-t", session, key], check=True)
    else:
        subprocess.run(["xdotool", "key", "--clearmodifiers", key], check=True)


def human_type(session: str, text: str, seed: int = 7, typo: bool = False,
               via: str = "tmux") -> None:
    rng = random.Random(seed)
    typo_at: int | None = None
    if typo and len(text) > 12:
        # land the typo in the middle of a word, where real typos happen
        typo_at = rng.randrange(len(text) // 3, 2 * len(text) // 3)

    for i, ch in enumerate(text):
        if typo_at is not None and i == typo_at:
            wrong = rng.choice([c for c in string.ascii_lowercase if c != ch.lower()])
            send(session, wrong, via)
            time.sleep(rng.uniform(0.18, 0.34))   # notice it
            press(session, "BSpace" if via == "tmux" else "BackSpace", via)
            time.sleep(rng.uniform(0.10, 0.20))
        send(session, ch, via)
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
    p.add_argument("--via", choices=["tmux", "xdotool"], default="tmux",
                   help="tmux writes to the pty (no keystroke overlay); xdotool emits real X key events")
    a = p.parse_args(argv)
    human_type(a.session, a.text, a.seed, a.typo, a.via)
    if a.enter:
        time.sleep(random.Random(a.seed).uniform(0.35, 0.9))
        press(a.session, "Return" if a.via == "xdotool" else "Enter", a.via)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
