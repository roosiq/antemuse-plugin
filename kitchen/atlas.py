"""The walk as a side-scrolling place.

The journal is the ground truth: each event is one WordNet step, so the map is
just the path those events trace. Nodes are drawn where the walk landed, edges
are the relation that carried it (up for hypernym, down for hyponym, sideways
for antonym), and the camera follows the walker as it travels the newest edge.

Cells, not pixels: this has to run in a terminal at 15 fps, so every glyph is a
position in a character grid and every colour is one of six.
"""
from __future__ import annotations

import math
import re
import time
from typing import Dict, List, Tuple

STEP_CHARS = 12          # cells between nodes on the x axis
LEVEL_CHARS = 3          # cells per hypernym level on the y axis

INK = "\x1b[38;5;253m"
MUTED = "\x1b[38;5;244m"
FAINT = "\x1b[38;5;238m"
AMBER = "\x1b[38;5;215m"
TEAL = "\x1b[38;5;116m"
RED = "\x1b[38;5;174m"
RESET = "\x1b[0m"

STEP_RE = re.compile(
    r"^(?P<a>.+?) \((?P<apos>[a-z]+)\) → (?P<b>.+?) \((?P<bpos>[a-z]+)\)"
    r" · (?P<how>.+?)(?: · “(?P<gloss>.*?)”)?$")

UP = ("hypernym", "holonym")
DOWN = ("hyponym", "meronym")


def parse(journal: List[Dict]) -> List[Dict]:
    """Turn walk events into nodes; a person's own word joins the same path."""
    nodes: List[Dict] = []
    depth = 0
    for e in journal:
        if e.get("who") == "person" and e.get("event") == "walk_person":
            nodes.append({"label": (e.get("text") or "").split(" · ")[0] or "…",
                          "pos": "", "gloss": "", "how": "your step", "delta": 0,
                          "depth": depth, "at": e.get("at", 0), "from": "", "person": True})
            continue
        if e.get("who") != "state" or e.get("event") != "walk":
            continue
        m = STEP_RE.match(e.get("text", ""))
        if not m:
            continue
        how = m.group("how")
        if any(k in how for k in UP):
            delta = 1
        elif any(k in how for k in DOWN):
            delta = -1
        else:
            delta = 0
        depth += delta
        nodes.append({
            "label": m.group("b"), "pos": m.group("bpos"), "gloss": m.group("gloss") or "",
            "how": how, "delta": delta, "depth": depth, "at": e.get("at", 0),
            "from": m.group("a"),
        })
    return nodes


def _blank(w: int, h: int) -> Tuple[List[List[str]], List[List[str]]]:
    return ([[" "] * w for _ in range(h)], [[""] * w for _ in range(h)])


def _put(g, c, x: int, y: int, ch: str, color: str = "") -> None:
    if 0 <= y < len(g) and 0 <= x < len(g[0]):
        g[y][x] = ch
        c[y][x] = color


def _text(g, c, x: int, y: int, s: str, color: str = "") -> int:
    for i, ch in enumerate(s):
        _put(g, c, x + i, y, ch, color)
    return x + len(s)


def _line(g, c, x0: int, y0: int, x1: int, y1: int, color: str) -> None:
    """A line made of characters that join up at cell resolution."""
    dx, dy = x1 - x0, y1 - y0
    steps = max(abs(dx), abs(dy), 1)
    for i in range(steps + 1):
        x = round(x0 + dx * i / steps)
        y = round(y0 + dy * i / steps)
        if abs(dx) >= abs(dy) * 2:
            ch = "─"
        elif abs(dy) >= abs(dx) * 2:
            ch = "│"
        else:
            ch = "╱" if (dx > 0) == (dy < 0) else "╲"
        _put(g, c, x, y, ch, color)


def render(state: Dict, w: int, h: int, tick: int = 0, now: float | None = None,
           pan: int = 0) -> List[str]:
    """One frame of the walk. Pure function of the journal and the clock."""
    now = now or time.time()
    nodes = parse(state.get("journal", []))
    g, c = _blank(w, h)

    # ---- parallax: deterministic dust, so the frame looks alive without state
    for i in range(22):
        sx = (i * 41 + tick // 4) % (w + 20) - 10
        sy = (i * 17) % max(1, h // 2)
        _put(g, c, sx, sy, "·" if i % 3 else "˙", FAINT)

    if not nodes:
        msg = "the path begins · waiting for the first step"
        _text(g, c, max(0, (w - len(msg)) // 2), h // 2, msg, MUTED)
        return ["".join(r) for r in g]

    panel_w = 30 if w >= 78 else 0
    pw = w - panel_w - 2                      # width of the walking area
    # ---- camera keeps the newest node right of centre, with unexplored fog ahead
    last_x = (len(nodes) - 1) * STEP_CHARS
    cam = max(0, last_x - (pw - 22) + pan)
    # ---- the camera also follows height, so a climb never walks off the top
    apex = nodes[-1]["depth"]
    base_y = h - 6

    def screen(i: int, depth: int) -> Tuple[int, int]:
        return i * STEP_CHARS - cam, base_y - (depth - apex) * LEVEL_CHARS

    # ---- fog ahead of the walker: the part of the graph not walked yet
    fog_x = min(pw - 4, last_x - cam + 3)
    for x in range(max(0, fog_x), min(pw, fog_x + 4)):
        for y in range(3, h - 3):
            if (x * 7 + y * 3 + tick // 4) % 5 == 0:
                _put(g, c, x, y, "░", FAINT)

    # ---- ground
    for x in range(pw):
        shade = TEAL if (x + tick) % 9 < 3 else FAINT
        _put(g, c, x, h - 2, "▁", shade)

    # ---- edges
    for i in range(1, len(nodes)):
        x0, y0 = screen(i - 1, nodes[i - 1]["depth"])
        x1, y1 = screen(i, nodes[i]["depth"])
        age = len(nodes) - i
        if nodes[i]["delta"] > 0:
            color = TEAL
        elif nodes[i]["delta"] < 0:
            color = AMBER
        else:
            color = MUTED
        if age > 6:
            color = FAINT
        _line(g, c, x0, y0, x1, y1, color)

    # ---- nodes and labels
    for i, n in enumerate(nodes):
        x, y = screen(i, n["depth"])
        if x < -12 or x > pw + 2:
            continue
        newest = i == len(nodes) - 1
        if n.get("person"):
            glyph, color = "◆", RED
        else:
            glyph = "◉" if newest else ("●" if len(nodes) - i < 4 else "○")
            color = AMBER if newest else (INK if len(nodes) - i < 4 else MUTED)
        _put(g, c, x, y, glyph, color)
        label = n["label"]
        seen = sum(1 for m in nodes[:i] if m["label"] == n["label"])
        if seen:
            label += f"·{seen + 1}"
        if len(label) > 15:
            label = label[:14] + "…"
        lx = x + 2 if x + 2 + len(label) < w else x - len(label) - 2
        if 0 <= lx < w:
            _text(g, c, lx, y, " " + label + " ", color)   # a chip: clears what the edge drew

    # ---- walker: travels the newest edge, then waits at the end
    x1, y1 = screen(len(nodes) - 1, nodes[-1]["depth"])
    if len(nodes) >= 2:
        elapsed = now - nodes[-1]["at"]
        travel = max(0.0, min(1.0, 1.0 - elapsed / 12.0)) if elapsed >= 0 else 0.0
        x0, y0 = screen(len(nodes) - 2, nodes[-2]["depth"])
        wx = round(x0 + (x1 - x0) * travel) if travel > 0 else x1 + 2
        wy = round(y0 + (y1 - y0) * travel) if travel > 0 else y1
        wy += 1 if int(tick / 2) % 2 else 0
    else:
        wx, wy = x1 + 2, y1
    _put(g, c, wx, wy - 1, "▮", INK)      # the walker's body
    _put(g, c, wx, wy, "▰", TEAL)         # its shadow on the edge

    # ---- rails
    for y in range(3, h - 2):
        _put(g, c, 0, y, "│", FAINT)
    for level in range(-4, 5):
        ly = base_y - level * LEVEL_CHARS
        if 3 <= ly < h - 2 and abs(level) <= 4:
            mark = f"{level:+d}" if level else " 0"
            _text(g, c, 2, ly, mark, TEAL if level == 0 else FAINT)

    if panel_w:
        px = pw + 2
        _put(g, c, px - 1, 2, "│", FAINT)
        _text(g, c, px, 2, "SENSE", FAINT)
        gloss = (nodes[-1]["gloss"] or "").strip()
        words, line_buf, rows_used = gloss.split(), "", 0
        for word in words:
            if len(line_buf) + len(word) + 1 > panel_w - 2:
                _text(g, c, px, 4 + rows_used, line_buf, MUTED)
                rows_used += 1
                line_buf = word
            else:
                line_buf = (line_buf + " " + word).strip()
            if rows_used >= 4:
                break
        if line_buf and rows_used < 4:
            _text(g, c, px, 4 + rows_used, line_buf, MUTED)
        _text(g, c, px, 10, "PATH", FAINT)
        for i, n in enumerate(nodes[-4:]):
            arrow = "↑" if n["delta"] > 0 else ("↓" if n["delta"] < 0 else "→")
            _text(g, c, px, 11 + i, f"{arrow} {n['label'][:panel_w - 4]}",
                  AMBER if i == len(nodes[-4:]) - 1 else MUTED)
        _text(g, c, px, 16, f"steps {len(nodes)}", FAINT)

    # ---- HUD
    depth = nodes[-1]["depth"]
    arrow = "↑" if nodes[-1]["delta"] > 0 else ("↓" if nodes[-1]["delta"] < 0 else "→")
    hud = f" STEP {len(nodes):02d}   DEPTH {depth:+d}   {arrow} {nodes[-1]['how'][:26]}"
    _text(g, c, 1, 0, hud, INK)
    legend = "↑ up · hypernym   ↓ down · hyponym   → across · antonym   ◆ your step   h/l pan   j join"
    _text(g, c, 1, 1, legend[: w - 2], FAINT)
    rows = []
    for y in range(h):
        row = "".join(g[y]).rstrip()
        colors = c[y][: len(row) + 1]
        out, cur = [], ""
        for x, ch in enumerate(row):
            if colors[x] != cur:
                cur = colors[x]
                out.append(cur)
            out.append(ch)
        rows.append("".join(out) + RESET)
    return rows


def strip(rows: List[str]) -> List[str]:
    return [re.sub(r"\x1b\[[0-9;]*m", "", r) for r in rows]
