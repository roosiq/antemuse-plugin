"""A full-screen CLI takeover for Antemuse.

Draws on the controlling terminal (/dev/tty) so it paints over the Hermes CLI
instead of being captured as command output: alternate screen, hidden cursor,
truecolor canvas, block-digit clock, live key handling. On exit the terminal is
restored exactly as it was.
"""
from __future__ import annotations

import json
import os
import re
import select
import subprocess
import shutil
import sys
import time
from typing import Any, Dict, List

# The takeover needs a POSIX terminal. Windows has no termios, and importing this module at plugin
# load time made the whole plugin fail to register there — every tool and hook lost, for a
# full-screen feature that only matters in a terminal. Imported defensively: the module loads
# everywhere, and the takeover itself says what it needs.
try:
    import termios  # type: ignore[import-not-found]
    import tty  # type: ignore[import-not-found]
    POSIX_TTY = True
except Exception:  # pragma: no cover - only on Windows
    termios = None  # type: ignore[assignment]
    tty = None  # type: ignore[assignment]
    POSIX_TTY = False

from . import backdrop, engine, panel, photographs, states, storage, walk_map

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


_LAST: Dict[str, Any] = {"key": None, "cells": None}
_FADE = 12          # ticks a dissolve lasts (~1s at the loop rate)


def _scene_pngs(key: str) -> List[Any]:
    base = backdrop._dir()
    sub = base / key
    pngs = sorted(sub.glob("*.png")) if key and sub.is_dir() else []
    return pngs or sorted(base.glob("*.png"))


def _overlay(state: Dict[str, Any], cols: int, rows: int, tick: int, pan: int) -> List[str] | None:
    """The walk's path, drawn over its scene — shapes only, never words."""
    if (state.get("active") or {}).get("key") != "walk":
        return None
    import re
    return [re.sub(r"\x1b\[[0-9;]*m", "", r) for r in
            walk_map.render(state, cols, rows, tick, pan=pan)]


def imagery_frame(state: Dict[str, Any], w: int, h: int, tick: int = 0, pan: int = 0) -> List[str]:
    """A full image, then a dissolve when the state changes."""
    active = state.get("active") or {}
    key = active.get("key") or "idle"
    cols, height = w - 1, h
    seconds = tick / 10.0

    # photographs first: they are the point of the thing
    if active.get("key") and photographs.available(active["key"]):
        shot = photographs.frame(active["key"], cols, height, seconds)
        if shot is not None:
            photographs.remember(active["key"], shot, seconds)
            return photographs.to_rows(shot)

    pngs = _scene_pngs(active.get("key") or "")
    if pngs:
        frame = photographs.cells(pngs[tick % len(pngs)], cols, height)
    else:
        frame = photographs.solid((14, 12, 11), cols, height)

    if _LAST["key"] is not None and _LAST["key"] != key and _LAST["cells"] is not None:
        _LAST["transition"] = (_LAST["cells"], tick)
    if _LAST.get("transition"):
        prev, start = _LAST["transition"]
        t = (tick - start) / _FADE
        frame = photographs.blend(prev, frame, min(1.0, t))
        if t >= 1:
            _LAST["transition"] = None

    _LAST["key"], _LAST["cells"] = key, frame
    return photographs.to_rows(frame, _overlay(state, cols, height, tick, pan))


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


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "tools", "term_scene.cjs")


def _scene_file() -> str:
    path = os.path.join(str(storage.data_dir()), "scene.json")
    return path


def _write_scene(key: str) -> None:
    try:
        with open(_scene_file(), "w") as fh:
            json.dump({"scene": key or "walk"}, fh)
    except Exception:
        pass


def _keyframed(key: str | None) -> bool:
    """Photographs win: only fall back to the live 3D scene when none exist."""
    return bool(key) and not photographs.available(key)


def _spawn_renderer(tty_fd: int, w: int, h: int, key: str):
    """three.js, rendered live by the software rasteriser in node."""
    node = shutil.which("node")
    if not node or not os.path.exists(LIVE):
        return None
    _write_scene(key)
    try:
        return subprocess.Popen(
            [node, LIVE, "--watch", _scene_file(), "--cols", str(w - 1),
             "--rows", str(h), "--fps", "12"],
            stdout=tty_fd, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
            close_fds=True, start_new_session=True,
        )
    except Exception as exc:
        try:
            with open(os.path.join(str(storage.data_dir()), "render_error.txt"), "w") as fh:
                fh.write(f"{type(exc).__name__}: {exc}\n")
        except Exception:
            pass
        return None


def _kill_renderer(proc) -> None:
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=2)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run() -> str:
    """Take over the terminal until the user quits; return a one-line summary."""
    tty_fd = _tty_fd()
    if tty_fd is None or not POSIX_TTY:
        # No terminal, or a platform without termios: print the frame instead of failing.
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
        w, h = os.get_terminal_size(tty_fd)
        # A pty with no window size reports 0x0, and a zero-width grid draws nothing:
        # the takeover looked like a blank screen with a hidden cursor.
        w, h = max(w, 40), max(h, 12)
        live_key = (engine.watch_state().get("active") or {}).get("key")
        renderer = _spawn_renderer(tty_fd, w, h, live_key) if _keyframed(live_key) else None
        typed = False
        while True:
            w, h = os.get_terminal_size(tty_fd)
            w, h = max(w, 40), max(h, 12)
            state = engine.watch_state()
            key = (state.get("active") or {}).get("key")
            if renderer and (key != live_key):
                _write_scene(key or "walk")
                live_key = key
            if renderer and key and not typed:
                # the renderer owns the screen; we only watch for keys
                ready, _, _ = select.select([tty_fd], [], [], 0.08)
                if not ready:
                    continue
                ch = os.read(tty_fd, 1).decode("utf-8", "ignore")
                if ch in ("q", "Q", "\x1b"):
                    break
                if ch == " ":
                    engine.stop()
                    key = None
                elif ch == "n":
                    note_mode, buffer, typed = True, "", True
                    _kill_renderer(renderer)
                    renderer = None
                elif ch == "j":
                    join_mode, buffer, typed = True, "", True
                    _kill_renderer(renderer)
                    renderer = None
                elif ch in "12345" and int(ch) <= len(states.STATES):
                    engine.enter(list(states.STATES)[int(ch) - 1])
                continue
            if not renderer and _keyframed(key) and not typed:
                renderer = _spawn_renderer(tty_fd, w, h, key)
                live_key = key
                if renderer:
                    continue
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
                    typed = False
                    if join_mode and buffer.strip():
                        engine.record("person", buffer.strip() + _word_gloss(buffer.strip()),
                                      event="walk_person")
                    elif not join_mode:
                        engine.record("person", buffer)
                    buffer, note_mode, join_mode = "", False, False
                elif ch == "\x1b":
                    buffer, note_mode, join_mode, typed = "", False, False, False
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
            elif ch in "12345" and int(ch) <= len(states.STATES):
                engine.enter(list(states.STATES)[int(ch) - 1])
            elif ch in ("w", "W"):
                engine.enter("walk")
            elif ch in ("d", "D"):
                engine.enter("daydream")
            elif ch in ("u", "U"):
                engine.enter("unstuck")
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


if __name__ == "__main__":
    # Without this the module documented in README and TESTING ("python3 -m
    # core.tui") imported itself and exited 0 without drawing anything.
    result = run()
    if not sys.stdin.isatty() and result:
        print(result)
