"""One state, every client.

The same frame is encoded for whatever the destination can actually show:

  terminal   truecolor ANSI, streaming, full width
  chat       ASCII snapshot, no escapes, narrow, one message
  text       plain record for a language model
  image      PNG attachment for clients that take files

Nothing here invents content; every renderer reads the same state dict.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image

from . import store

RAMP = " .:-=+*#%@"
ASCII_RAMP = " .:-=+*#"

PROFILES: Dict[str, Dict[str, Any]] = {
    "terminal": {"ansi": True, "color": True, "animate": True, "width": None, "image": False},
    "discord": {"ansi": False, "color": False, "animate": False, "width": 56, "image": True},
    "matrix": {"ansi": False, "color": False, "animate": False, "width": 56, "image": True},
    "telegram": {"ansi": False, "color": False, "animate": False, "width": 44, "image": True},
    "slack": {"ansi": False, "color": False, "animate": False, "width": 52, "image": True},
    "text": {"ansi": False, "color": False, "animate": False, "width": 72, "image": False},
}


def profile(name: str = "text", width: int | None = None) -> Dict[str, Any]:
    base = dict(PROFILES.get(name, PROFILES["text"]))
    if width:
        base["width"] = width
    return base


def strip(s: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def _frames_dir() -> Path:
    return store.data_dir() / "three_frames"


def art(cols: int = 44, rows: int = 12, index: int = 0, ramp: str = ASCII_RAMP) -> List[str]:
    """Luminance-ramp ASCII of a rendered three.js frame: no colour, no escapes."""
    pngs = sorted(_frames_dir().glob("*.png")) if _frames_dir().is_dir() else []
    if not pngs:
        return []
    im = Image.open(pngs[index % len(pngs)]).convert("L")
    w0, h0 = im.size
    im = im.crop((int(w0 * 0.20), int(h0 * 0.12), int(w0 * 0.80), int(h0 * 0.88)))
    im = im.resize((cols, rows), Image.LANCZOS)
    px = im.load()
    out = []
    for r in range(rows):
        line = "".join(ramp[min(len(ramp) - 1, int(px[c, r] / 255 * len(ramp)))] for c in range(cols))
        out.append(line.rstrip())
    return out


def _clock(seconds: int) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _bar(frac: float, cells: int, on: str = "█", off: str = "░") -> str:
    frac = min(1.0, max(0.0, frac))
    filled = int(round(cells * frac))
    return on * filled + off * (cells - filled)


def _wrap(s: str, n: int, limit: int = 3) -> List[str]:
    words, lines, cur = (s or "").split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) <= n:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:limit]


def card(state: Dict[str, Any], name: str = "discord") -> str:
    """A snapshot any chat client can render: monospaced block, no ANSI, fixed width."""
    p = profile(name)
    w = p["width"] or 56
    active = state.get("active")
    journal = state.get("journal", [])
    lines: List[str] = []

    if active:
        head = f"ANTEMUSE · {active['label']}"
        right = _clock(active["seconds_left"])
        lines.append(head + " " * max(1, w - len(head) - len(right)) + right)
    else:
        lines.append("ANTEMUSE · IDLE")
    lines.append("─" * w)

    if active:
        frac = active["seconds_left"] / max(1, active.get("total_seconds") or active["seconds_left"])
        lines.append(_bar(frac, w))
        art_rows = 10 if w < 50 else 12
        for row in art(cols=w, rows=art_rows):
            lines.append(row)
        lines.append("")
        tools = "closed" if active["tools"] == [] else (
            "open" if active["tools"] is None else ", ".join(active["tools"]))
        lines += _wrap(active["contract"], w, 2)
        lines.append(f"tools {tools} · {active['turns_left']} turn(s)")
    else:
        lines.append("no state running.")
        lines.append("1 walk · 2 daydream · 3 dissociate · 4 dream · 5 doomscroll")

    agent = [e for e in journal if e["who"] == "agent"]
    person = [e for e in journal if e["who"] == "person"]
    lines.append("─" * w)
    for label, entries in (("AGENT", agent), ("YOU", person)):
        if entries:
            body = _wrap(entries[-1]["text"], w - 8, 3)
            lines.append(f"{label:<6}{body[0]}")
            for extra in body[1:]:
                lines.append(" " * 6 + extra)
        else:
            lines.append(f"{label:<6}—")
    residue = state.get("residue") or []
    if residue:
        lines.append("─" * w)
        lines += _wrap("residue · " + " · ".join(residue), w, 2)
    return "\n".join(lines)


def record(state: Dict[str, Any]) -> str:
    """The language-model projection: dense, no decoration, no ANSI."""
    active = state.get("active")
    lines = []
    if active:
        lines.append(
            f"state {active['key']} | {active['label']} | {_clock(active['seconds_left'])} left "
            f"| {active['turns_left']} turn(s) | tools "
            + ("closed" if active["tools"] == [] else "open" if active["tools"] is None else ",".join(active["tools"]))
        )
        lines.append(f"contract: {active['contract']}")
    else:
        lines.append("state none")
    for e in state.get("journal", []):
        lines.append(f"{e['who']} {e['state']} :: {e['text']}")
    for r in state.get("residue", []):
        lines.append(f"residue :: {r}")
    return "\n".join(lines)


def snapshot_path(state: Dict[str, Any], name: str = "discord") -> Path:
    """A PNG of the same card, for clients that render text in a proportional font."""
    from PIL import ImageDraw, ImageFont

    text = card(state, name)
    font_path = "/usr/share/fonts/google-noto-vf/NotoSansMono[wdth,wght].ttf"
    if not Path(font_path).exists():
        font_path = "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf"
    font = ImageFont.truetype(font_path, 18)
    pad, lh = 28, 26
    lines = text.splitlines()
    wpx = pad * 2 + max(len(l) for l in lines) * 11
    hpx = pad * 2 + len(lines) * lh
    im = Image.new("RGB", (int(wpx), int(hpx)), (14, 12, 11))
    d = ImageDraw.Draw(im)
    for i, line in enumerate(lines):
        d.text((pad, pad + i * lh), line, font=font, fill=(242, 234, 225))
    path = store.data_dir() / "state_card.png"
    im.save(path)
    return path
