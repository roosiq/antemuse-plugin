"""A full-screen CLI takeover for Antemuse States.

Draws on the controlling terminal (/dev/tty) so it paints over the Hermes CLI
instead of being captured as command output: alternate screen, hidden cursor,
truecolor canvas, block-digit clock, live key handling. On exit the terminal is
restored exactly as it was.
"""
from __future__ import annotations

import os
import re
import select
import shutil
import sys
import termios
import time
import tty
from typing import Any, Dict, List

from . import atlas, definitions, engine, panel, three_backdrop

BG = (14, 12, 11)
INK = (242, 234, 225)
MUTED = (138, 128, 121)
FAINT = (54, 48, 44)
AMBER = (232, 163, 61)
TEAL = (111, 179, 168)
RED = (206, 106, 94)

RESET = "\x1b[0m"

FONT: Dict[str, List[str]] = {
    "0": ["███", "█ █", "█ █", "█ █", "███"],
    "1": [" █ ", "██ ", " █ ", " █ ", "███"],
    "2": ["███", "  █", "███", "█  ", "███"],
    "3": ["███", "  █", "███", "  █", "███"],
    "4": ["█ █", "█ █", "███", "  █", "  █"],
    "5": ["███", "█  ", "███", "  █", "███"],
    "6": ["███", "█  ", "███", "█ █", "███"],
    "7": ["███", "  █", "  █", "  █", "  █"],
    "8": ["███", "█ █", "███", "█ █", "███"],
    "9": ["███", "█ █", "███", "  █", "███"],
    ":": ["   ", " █ ", "   ", " █ ", "   "],
    " ": ["  ", "  ", "  ", "  ", "  "],
}

SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def fg(c: tuple[int, int, int]) -> str:
    return f"\x1b[38;2;{c[0]};{c[1]};{c[2]}m"


def bg(c: tuple[int, int, int]) -> str:
    return f"\x1b[48;2;{c[0]};{c[1]};{c[2]}m"


def strip(s: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def pad(s: str, n: int) -> str:
    visible = len(strip(s))
    return s + " " * max(0, n - visible)


def block_text(s: str, scale: int = 2) -> List[str]:
    """Render in block glyphs, doubled horizontally so the numerals read as type."""
    rows = ["" for _ in range(5)]
    for ch in s:
        glyph = FONT.get(ch, FONT[" "])
        for i in range(5):
            wide = "".join(c * scale for c in glyph[i])
            rows[i] += wide + "  "
    return [r.rstrip() for r in rows]


def clock_big(seconds: int) -> List[str]:
    seconds = max(0, int(seconds))
    return block_text(f"{seconds // 60:02d}:{seconds % 60:02d}")


def _clip(s: str, n: int) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: max(0, n - 1)] + "…"


def _wrap(text: str, width: int, limit: int) -> List[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:limit]


def _entries(journal: List[Dict[str, Any]], who: str, width: int, limit: int) -> List[List[str]]:
    out: List[List[str]] = []
    for e in [x for x in journal if x.get("who") == who][-limit:]:
        stamp = time.strftime("%H:%M", time.localtime(e["at"]))
        out.append([f"{stamp}  {e['state']}"] + _wrap(e["text"], width, 6))
    return out


def imagery_frame(state: Dict[str, Any], w: int, h: int, tick: int = 0, pan: int = 0) -> List[str]:
    """The person gets pictures. No labels, no counters, no explanation."""
    active = state.get("active") or {}
    canvas = bg(BG) + fg(INK)
    rows: List[str] = []
    if active.get("key") == "walk":
        art = atlas.render(state, w - 1, h, tick, pan=pan)
    else:
        art = []
        if active:
            bank = three_backdrop.frames(w - 1, h, active["key"])
            if bank:
                art = bank[tick % len(bank)]
        if not art:
            # nothing pre-rendered: a slow field of dust, still no words
            art = []
            for y in range(h):
                row = []
                for x in range(w - 1):
                    lit = (x * 7 + y * 13 + tick // 3) % 97 == 0
                    row.append("·" if lit else " ")
                art.append("".join(row))
    for row in art[:h]:
        rows.append(pad(canvas + row, w - 1))
    while len(rows) < h:
        rows.append(pad(canvas, w - 1))
    return rows[:h]


def render_frame(state: Dict[str, Any], w: int, h: int, tick: int = 0) -> List[str]:
    return imagery_frame(state, w, h, tick)


def _draw(tty_fd: int, w: int, h: int, frame: List[str]) -> None:
    body = [f + "\x1b[K" for f in frame[:h]]
    body += ["\x1b[K"] * max(0, h - len(body))
    os.write(tty_fd, ("\x1b[H" + "\r\n".join(body)).encode())


def _tty_fd() -> int | None:
    """Prefer the process's real terminal; Ink swaps sys.stdout but __stdout__ survives."""
    for stream in (getattr(sys, "__stdin__", None), getattr(sys, "__stdout__", None)):
        try:
            fd = stream.fileno()
            if os.isatty(fd):
                return fd
        except Exception:
            continue
    try:
        fd = os.open("/dev/tty", os.O_RDWR)
        return fd
    except OSError:
        return None


def _word_gloss(word: str) -> str:
    """One lookup so the person's own step carries a sense, like the walk's do."""
    try:
        from . import sources
        wn = sources._wn()
        syns = wn.synsets(word)
        if not syns:
            return " · no sense in wordnet"
        return " · " + (syns[0].definition() or "").split(";")[0][:70]
    except Exception:
        return ""


def run() -> str:
    """Take over the terminal until the user quits; return a one-line summary."""
    tty_fd = _tty_fd()
    if tty_fd is None:
        return panel.render(engine.watch_state())
    old = termios.tcgetattr(tty_fd)
    note_mode = False
    join_mode = False
    pan = 0
    buffer = ""
    frames = 0
    try:
        tty.setcbreak(tty_fd)
        os.write(tty_fd, b"\x1b[?1049h\x1b[?25l")
        while True:
            w, h = os.get_terminal_size(tty_fd)
            state = engine.watch_state()
            frame = imagery_frame(state, w, h, frames, pan=pan)
            if (state.get("active") or {}).get("key") != "walk":
                pan = 0
            if note_mode or join_mode:
                label = " your word › " if join_mode else " note › "
                frame[-1] = pad(bg(BG) + fg(AMBER) + label + buffer + "▏", w)
            _draw(tty_fd, w, h, frame)
            frames += 1

            ready, _, _ = select.select([tty_fd], [], [], 0.08)
            if not ready:
                continue
            ch = os.read(tty_fd, 1).decode("utf-8", "ignore")
            if note_mode or join_mode:
                if ch in ("\r", "\n"):
                    if join_mode and buffer.strip():
                        engine.record("person", buffer.strip() + _word_gloss(buffer.strip()),
                                      event="walk_person")
                    elif not join_mode:
                        engine.record("person", buffer)
                    buffer, note_mode, join_mode = "", False, False
                elif ch == "\x1b":
                    buffer, note_mode, join_mode = "", False, False
                elif ch in ("\x7f", "\b"):
                    buffer = buffer[:-1]
                elif ch.isprintable():
                    buffer += ch
                continue
            if ch in ("q", "Q", "\x1b"):
                break
            if ch == " ":
                engine.stop()
            elif ch == "n":
                note_mode, buffer = True, ""
            elif ch == "j":
                join_mode, buffer = True, ""
            elif ch in ("h", "H"):
                pan = min(120, pan + 6)
            elif ch in ("l", "L"):
                pan = max(0, pan - 6)
            elif ch == "0":
                pan = 0
            elif ch in "12345" and int(ch) <= len(definitions.STATES):
                engine.enter(list(definitions.STATES)[int(ch) - 1])
            elif ch in ("w", "W"):
                engine.enter("walk")
            elif ch in ("d", "D"):
                engine.enter("daydream")
            elif ch in ("i", "I"):
                engine.enter("dissociate")
            elif ch in ("m", "M"):
                engine.enter("dream")
            elif ch in ("k", "K"):
                engine.enter("doomscroll")
    finally:
        try:
            os.write(tty_fd, b"\x1b[?25h\x1b[?1049l")
        finally:
            termios.tcsetattr(tty_fd, termios.TCSADRAIN, old)
            os.close(tty_fd)
    return engine.status()
