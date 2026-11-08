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

from . import storage

RAMP = " .:-=+*#%@"
ASCII_RAMP = " .:-=+*#"

PROFILES: Dict[str, Dict[str, Any]] = {
    "terminal": {"ansi": True, "color": True, "animate": True, "width": None, "image": False, "fence": False, "max_chars": 0},
    # Discord: mobile renders ~40 monospace columns before wrapping, desktop ~56.
    # 2000-char cap per message, so the card carries its own budget.
    "discord": {"ansi": False, "color": False, "animate": False, "width": 40, "image": True, "fence": True, "max_chars": 1800},
    "discord_desktop": {"ansi": False, "color": False, "animate": False, "width": 56, "image": True, "fence": True, "max_chars": 1800},
    "matrix": {"ansi": False, "color": False, "animate": False, "width": 52, "image": True, "fence": True, "max_chars": 4000},
    "telegram": {"ansi": False, "color": False, "animate": False, "width": 40, "image": True, "fence": True, "max_chars": 3800},
    "slack": {"ansi": False, "color": False, "animate": False, "width": 46, "image": True, "fence": True, "max_chars": 3800},
    "text": {"ansi": False, "color": False, "animate": False, "width": 72, "image": False, "fence": False, "max_chars": 0},
}

# how many art rows fit in a chat card at each width, before the message gets tall
ART_ROWS = {40: 8, 46: 9, 52: 10, 56: 12, 72: 14}


def profile(name: str = "text", width: int | None = None, narrow: bool = False) -> Dict[str, Any]:
    """Resolve a destination to an encoding plan. `narrow` picks the mobile width."""
    key = name
    if narrow and name == "discord":
        key = "discord"
    base = dict(PROFILES.get(key, PROFILES["text"]))
    if width:
        base["width"] = max(24, min(96, width))
    if narrow and not width:
        base["width"] = 36
    base["art_rows"] = ART_ROWS.get(base["width"], 8)
    return base


def strip(s: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


#: A monospace glyph cell is about 0.6 advances wide for one line of height. Any
#: aspect-correct sampling has to divide by this, or the picture arrives stretched
#: by 1/0.6. The old code resized straight to (cols, rows) and did exactly that.
CELL_ASPECT = 0.6


def _frames_dir(pane: bool = False) -> Path:
    """Frames baked for a chat card (3.8:1) or for a pane (square)."""
    return storage.data_dir() / ("three_frames_pane" if pane else "three_frames")


def _stretch_bounds(values: List[int]) -> tuple[int, int]:
    """The ends of this frame's own range: 2nd and 99.5th percentile.

    A scene bank whose mean luminance is 13/255 has to be read against itself,
    not against 255, or the ramp's first visible character is never reached.
    """
    ordered = sorted(values)
    n = len(ordered)
    if not n:
        return 0, 0
    return ordered[int(n * 0.02)], ordered[min(n - 1, int(n * 0.995))]


def _cover(im: Image.Image, cols: int, rows: int) -> Image.Image:
    """Crop to the grid's aspect (in cell space) without distorting it, then scale.

    ``cols * CELL_ASPECT / rows`` is what the box looks like on screen; the image is
    cropped to that ratio first, so one cell of picture is one cell of glyphs.
    """
    target = (cols * CELL_ASPECT) / rows
    w, h = im.size
    if w / h > target:                      # too wide: trim the sides
        keep = max(1, int(round(h * target)))
        left = (w - keep) // 2
        return im.crop((left, 0, left + keep, h))
    keep = max(1, int(round(w / target)))   # too tall: trim top and bottom
    top = (h - keep) // 2
    return im.crop((0, top, w, top + keep))


def art(cols: int = 44, rows: int = 12, index: int = 0, ramp: str = ASCII_RAMP,
        scene: str = "", fit: str = "cover", pane: bool = False) -> List[str]:
    """Luminance-ramp ASCII of a rendered three.js frame: no colour, no escapes.

    ``fit="cover"`` fills the grid edge to edge (a pane, an immersive surface);
    ``fit="contain"`` letterboxes instead, which is what a chat card wants when the
    frame is wider than the message.
    """
    base = _frames_dir(pane=pane)
    sub = base / scene if scene else None
    pngs = sorted(sub.glob("*.png")) if sub is not None and sub.is_dir() else []
    if not pngs and base.is_dir():
        pngs = sorted(base.glob("*.png")) or [
            p for d in sorted(base.iterdir()) if d.is_dir() for p in sorted(d.glob("*.png"))[:1]
        ]
    if not pngs:
        return []
    im = Image.open(pngs[index % len(pngs)]).convert("L")
    if fit == "cover":
        im = _cover(im, cols, rows).resize((cols, rows), Image.LANCZOS)
    else:
        w0, h0 = im.size
        im = im.crop((int(w0 * 0.20), int(h0 * 0.12), int(w0 * 0.80), int(h0 * 0.88)))
        im = _cover(im, cols, rows).resize((cols, rows), Image.LANCZOS)
    values = list(im.tobytes())
    lo, hi = _stretch_bounds(values)
    out = []
    for r in range(rows):
        line = ""
        for c in range(cols):
            v = values[r * cols + c]
            t = 0.0 if hi <= lo else (v - lo) / (hi - lo)
            t = min(1.0, max(0.0, t))
            line += ramp[min(len(ramp) - 1, int(t * len(ramp)))]
        # A pane needs whole rows: ragged edges would show as a torn right margin.
        out.append(line if fit == "cover" else line.rstrip())
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


def card(state: Dict[str, Any], name: str = "discord", width: int | None = None,
         narrow: bool = False, fence: bool | None = None) -> str:
    """What a chat client shows: only the picture, sized to that client's view."""
    p = profile(name, width, narrow)
    w = p["width"] or 56
    active = state.get("active") or {}
    rows = art(cols=w, rows=p["art_rows"], scene=active.get("key", ""))
    if not rows:
        rows = [" " * w for _ in range(p["art_rows"])]
    text = "\n".join(r.rstrip() for r in rows)
    if p.get("max_chars") and len(text) > p["max_chars"]:
        text = text[: p["max_chars"]]
    if (fence if fence is not None else p.get("fence")):
        text = "```\n" + text + "\n```"
    return text


def _shrink(text: str, cap: int) -> str:
    """Drop rows from the middle of the art block until the message fits the cap."""
    lines = text.splitlines()
    art_idx = [i for i, l in enumerate(lines) if l and set(l) <= set(" .:-=+*#%@")]
    while len("\n".join(lines)) > cap and art_idx:
        drop = art_idx.pop(len(art_idx) // 2)
        lines.pop(drop)
        art_idx = [i if i < drop else i - 1 for i in art_idx]
    while len("\n".join(lines)) > cap and len(lines) > 6:
        lines.pop(-2)
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
        lines.append(f"{e.get('who','agent')} {e['state']} :: {e['text']}")
    for r in state.get("residue", []):
        text = r.get("text", "") if isinstance(r, dict) else str(r)
        lines.append(f"residue :: {text}")
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
    home = storage.data_dir()
    path = home / "state_card.png"
    im.save(path)
    return path
