"""The CLI panel: one frame the person can watch, and take part in.

Rendered as plain text with ANSI colour, so it survives the Hermes CLI, tmux,
SSH, and a screenshot. The left column is what the agent produced in the state;
the right column is what the person put down while taking the same state.
"""
from __future__ import annotations

import os
import shutil
import textwrap
import time
from typing import Any, Dict, List

AMBER = "\x1b[38;5;215m"
TEAL = "\x1b[38;5;116m"
DIM = "\x1b[38;5;244m"
FAINT = "\x1b[38;5;238m"
BOLD = "\x1b[1m"
RESET = "\x1b[0m"

MIN_WIDTH = 64


def _color_on() -> bool:
    return not os.environ.get("NO_COLOR") and os.environ.get("TERM", "") != "dumb"


def width(default: int | None = None) -> int:
    cols = shutil.get_terminal_size((92, 24)).columns
    return max(MIN_WIDTH, min(cols, 110)) if default is None else default


def clock(seconds: int) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def bar(fraction: float, cells: int) -> str:
    fraction = min(1.0, max(0.0, fraction))
    filled = int(round(cells * fraction))
    return "█" * filled + "░" * (cells - filled)


def _paint(s: str, code: str, on: bool) -> str:
    return f"{code}{s}{RESET}" if on else s


def _clip(s: str, n: int) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _block(entries: List[Dict[str, Any]], cw: int, empty: str, colour: str, on: bool) -> List[str]:
    if not entries:
        return [_paint(empty, DIM, on)]
    lines: List[str] = []
    for e in entries[-4:]:
        stamp = time.strftime("%H:%M", time.localtime(e["at"]))
        head = _paint(f"{stamp}  {e['state']}", FAINT, on)
        body = textwrap.wrap(_clip(e["text"], cw * 5), cw)[:4] or [""]
        lines.append(head)
        lines += ["  " + _paint(b, colour, on) if i else "  " + _paint(b, colour, on) for i, b in enumerate(body)]
    return lines


def render(state: Dict[str, Any], w: int | None = None, color: bool | None = None) -> str:
    """Fallback surface: the same imagery, no words, for anywhere without a tty."""
    from . import atlas, three_backdrop
    on = _color_on() if color is None else color
    w = width(w)
    h = 18
    active = state.get("active") or {}
    if active.get("key") == "walk" or not active:
        rows = atlas.render(state, w - 1, h, 0)
    else:
        bank = three_backdrop.frames(w - 1, h, active.get("key", ""))
        rows = bank[0] if bank else [" " * (w - 1)] * h
    if not on:
        import re
        rows = [re.sub(r"\x1b\[[0-9;]*m", "", r) for r in rows]
    return "\n".join(rows)


def debug(state: Dict[str, Any], w: int | None = None, color: bool | None = None) -> str:
    on = _color_on() if color is None else color
    w = width(w)
    inner = w - 2
    active = state.get("active")
    out: List[str] = []

    left = _paint("ANTEMUSE · STATES", BOLD, on)
    if active:
        right = _paint(f"{active['label']}  {clock(active['seconds_left'])}", AMBER, on)
    else:
        right = _paint("no state", DIM, on)
    gap = max(1, inner - 16 - len(active["label"] if active else "no state") - 6)
    out.append(" " + left + " " * gap + right)
    out.append(_paint("─" * inner, FAINT, on))

    if active:
        pct = active["seconds_left"] / max(1, active.get("total_seconds") or active["seconds_left"])
        out.append(" " + _paint(bar(pct, inner - 2), AMBER, on))
        out.append(" " + _paint(active["contract"], DIM, on))
    else:
        out.append(" " + _paint("nothing is running. /walk /daydream /dissociate /dream /doomscroll", DIM, on))

    out.append("")

    cw = max(20, (inner - 5) // 2)
    journal = state.get("journal", [])
    stream = [e for e in journal if e.get("who") == "state"][-3:]
    for e in stream:
        out.append(" " + _paint("· " + _clip(e["text"], inner - 4), DIM, on))
    if stream:
        out.append("")
    agent = [e for e in journal if e.get("who") == "agent"]
    person = [e for e in journal if e.get("who") == "person"]
    head_a = _paint("THE AGENT", BOLD, on)
    head_y = _paint("YOU", BOLD, on)
    out.append(" " + head_a + " " * (cw + 3 - 9) + head_y)

    a_lines = _block(agent, cw, "has not spoken in this state", TEAL, on)
    y_lines = _block(person, cw, "nothing put down yet — /note <text>", TEAL, on)
    for i in range(max(len(a_lines), len(y_lines))):
        a = a_lines[i] if i < len(a_lines) else ""
        y = y_lines[i] if i < len(y_lines) else ""
        pad = " " * max(0, cw + 3 - len(_strip(a)))
        out.append(" " + a + pad + y)

    out.append(_paint("─" * inner, FAINT, on))

    if active:
        closes = "closed" if active["tools"] == [] else ("open" if active["tools"] is None else ", ".join(active["tools"]))
        out.append(" " + _paint("tools  ", FAINT, on) + _paint(closes, DIM, on))
        out.append(" " + _paint("turns  ", FAINT, on) + _paint(str(active["turns_left"]), DIM, on))
    residue = [r.get("text", "") if isinstance(r, dict) else str(r) for r in (state.get("residue") or [])]
    if residue:
        out.append(" " + _paint("residue ", FAINT, on) + _paint(" · ".join(residue), DIM, on))
    out.append(" " + _paint("/note <text>  /snap  /states", FAINT, on))
    return "\n".join(out)


def _strip(s: str) -> str:
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def live(seconds: int = 20, interval: float = 1.0) -> str:
    """Redraw in place until the state ends or the window closes."""
    import sys

    end = time.time() + max(3, seconds)
    first = True
    frames = 0
    try:
        while time.time() < end:
            frame = render(engine_state())
            if not first:
                sys.stdout.write("\x1b[2J\x1b[H")
            sys.stdout.write(frame + "\n")
            sys.stdout.flush()
            first = False
            frames += 1
            time.sleep(interval)
            st = engine_state().get("active")
            if st is None:
                break
    except KeyboardInterrupt:
        pass
    return f"\nwatched {frames} frame(s)."


def engine_state() -> Dict[str, Any]:
    from . import engine
    return engine.watch_state()
