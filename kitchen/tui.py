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


def walk_frame(state: Dict[str, Any], w: int, h: int, tick: int = 0, pan: int = 0) -> List[str]:
    """The walk gets the whole screen: a side-scrolling map instead of a backdrop."""
    active = state.get("active") or {}
    canvas = bg(BG) + fg(INK)
    inner = w - 4
    rows: List[str] = []

    def line(s: str = "") -> None:
        rows.append(pad(canvas + s, w - 1))

    brand = "A N T E M U S E"
    line(fg(MUTED) + " " + brand + " " * max(1, inner - len(brand) - len(active.get("label", "")))
         + fg(AMBER) + active.get("label", "") + fg(INK) + " ")
    line(fg(FAINT) + " " + "─" * inner)

    map_h = max(8, h - 12)
    for row in atlas.render(state, inner, map_h, tick):
        line(" " + row + fg(INK))

    mins, secs = divmod(int(active.get("seconds_left", 0)), 60)
    tools = "tools closed" if active.get("tools") == [] else "tools open"
    line()
    line(" " + fg(AMBER) + f"{mins:02d}:{secs:02d}" + fg(MUTED) + " left   "
         + fg(INK) + active.get("contract", "") + fg(FAINT) + "  ·  " + tools
         + f"  ·  {active.get('turns_left', 0)} turn(s)")

    journal = state.get("journal", [])
    recent = [e for e in journal if e.get("who") == "state"][-1:]
    for e in recent:
        stamp = time.strftime("%H:%M:%S", time.localtime(e["at"]))
        line(" " + fg(FAINT) + stamp + " " + fg(AMBER) + "· " + fg(MUTED) + _clip(e["text"], inner - 12))
    agent = [e for e in journal if e.get("who") == "agent"][-1:]
    person = [e for e in journal if e.get("who") == "person"][-1:]
    line(" " + fg(INK) + "AGENT " + fg(MUTED) + _clip(agent[0]["text"], inner // 2 - 8) if agent
         else " " + fg(FAINT) + "AGENT has not spoken yet")
    if person:
        line(" " + fg(INK) + "YOU   " + fg(MUTED) + _clip(person[0]["text"], inner - 8))
    while len(rows) < h:
        rows.append(pad(canvas, w - 1))
    return rows[:h]


def render_frame(state: Dict[str, Any], w: int, h: int, tick: int = 0) -> List[str]:
    active = state.get("active")
    if active and active.get("key") == "walk" and w >= 80 and h >= 20:
        return walk_frame(state, w, h, tick)
    canvas = bg(BG) + fg(INK)
    left = 3
    inner = w - left - 2
    rows: List[str] = []

    def line(s: str = "", colour: tuple[int, int, int] = INK) -> None:
        # one column short of the terminal width: writing exactly w chars leaves a
        # pending wrap that turns the next newline into an extra blank line
        rows.append(pad(canvas + fg(colour) + s, w - 1))

    brand = "A N T E M U S E"
    if active:
        right = f"{active['label']}   {int((time.time()*2)) % 9 * ' '}"
        head_right = active["label"]
        line(fg(MUTED) + brand + " " * max(1, inner - len(brand) - len(head_right) - 1)
             + fg(AMBER) + head_right)
    else:
        line(fg(MUTED) + brand + " " * max(1, inner - len(brand) - 5) + fg(MUTED) + "IDLE")
    line(fg(FAINT) + "─" * inner)
    line()

    art_cols = 44 if w >= 104 else 0
    art: List[str] = []
    if active and art_cols:
        bank = three_backdrop.frames(art_cols, 14, active["key"])
        if bank:
            art = bank[tick % len(bank)]

    if active:
        digits = clock_big(active["seconds_left"])
        width_digits = max(len(r) for r in digits)
        slot = (w - art_cols - 3) if art_cols else w
        x0 = max(4, (slot - width_digits) // 2)
        spin = SPINNER[tick % len(SPINNER)]
        hero: List[str] = []
        for i, row in enumerate(digits):
            gutter = fg(AMBER) + (spin if i == 2 else " ") + "  "
            hero.append(" " * max(1, (x0 - 3)) + gutter + fg(AMBER) + row)
        hero.append("")
        total = max(1, active.get("total_seconds") or active["seconds_left"])
        frac = active["seconds_left"] / total
        cells = min(slot - 8, width_digits + 12)
        filled = int(round(cells * frac))
        lead = " " * max(2, (slot - cells) // 2)
        hero.append(lead + fg(AMBER) + "█" * filled + fg(FAINT) + "░" * (cells - filled))
        hero.append("")
        tools = "tools closed" if active["tools"] == [] else (
            "tools open" if active["tools"] is None else "tools " + ", ".join(active["tools"]))
        hero.append("  " + fg(MUTED) + active["contract"] + "   " + fg(FAINT) + "·  " + tools
                    + f"  ·  {active['turns_left']} turn(s)")

        if art:
            left_w = w - art_cols - 3
            for i in range(max(len(hero), len(art))):
                l = hero[i] if i < len(hero) else ""
                r = art[i] if i < len(art) else ""
                line(pad(l, left_w) + "  " + r)
            # hero rows already drawn; skip the plain lines below
            rows_before_columns = True
        else:
            for h_ in hero:
                line(h_)
            rows_before_columns = True
    else:
        line("  " + fg(MUTED) + "no state running — pick one; you enter it at the same time as the agent")
        rows_before_columns = True

    line()

    journal = state.get("journal", [])
    stream = [e for e in journal if e.get("who") == "state"][-3:]
    if stream:
        line("  " + fg(FAINT) + "EVENTS")
        for e in stream:
            stamp = time.strftime("%H:%M:%S", time.localtime(e["at"]))
            line("  " + fg(FAINT) + stamp + "  " + fg(AMBER) + "· " + fg(MUTED)
                 + _clip(e["text"], inner - 14))
        line()

    colw = max(18, (inner - 5) // 2)
    line("  " + fg(INK) + "THE AGENT" + " " * (colw + 3 - 9) + fg(INK) + "YOU")
    a_rows = _entries(journal, "agent", colw - 2, 2)
    y_rows = _entries(journal, "person", colw - 2, 2)
    block: List[str] = []
    for i in range(max(len(a_rows), len(y_rows))):
        a = a_rows[i] if i < len(a_rows) else []
        y = y_rows[i] if i < len(y_rows) else []
        for j in range(max(len(a), len(y))):
            av = a[j] if j < len(a) else ""
            yv = y[j] if j < len(y) else ""
            colour_a = TEAL if j else FAINT
            colour_y = TEAL if j else FAINT
            line("  " + fg(colour_a) + pad(av, colw) + fg(FAINT) + " │ " + fg(colour_y) + yv)
    if not a_rows:
        line("  " + fg(FAINT) + pad("has not spoken yet", colw) + fg(FAINT) + " │ " + fg(FAINT)
             + "press n to write your side")
    while len(rows) < h - 4:
        line()
    line(fg(FAINT) + "─" * inner)

    residue = state.get("residue") or []
    if residue:
        line("  " + fg(FAINT) + "residue " + fg(MUTED) + " · ".join(residue))
    else:
        menu = "  ".join(f"{i} {k}" for i, k in enumerate(definitions.STATES, 1))
        line("  " + fg(FAINT) + menu + fg(MUTED) + "   n note   space snap   q quit")
    return rows


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
            frame = render_frame(state, w, h, frames)
            if not (state.get("active") or {}).get("key") == "walk":
                pan = 0
            if (state.get("active") or {}).get("key") == "walk":
                frame = walk_frame(state, w, h, frames, pan=pan)
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
