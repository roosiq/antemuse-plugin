#!/usr/bin/env python3
"""Draw the functional flow of the Antemuse plugin as an SVG.

Every box here is a claim about the code, not about the docs. The docs drifted (APP_FLOW.md
still lists an "expiry (ceiling)" ending that `_expire()` no longer has), so this reads the
shape of `core/engine.py`, `core/states.py` and `__init__.py` and draws that.

    python3 docs/design/flow_gen.py        # writes antemuse-flow.svg next to this file
"""
from __future__ import annotations

import html
from pathlib import Path

# --- palette: taken from the pane (desktop/plugin.js), so the drawing looks like the product
BG = "#05070a"
LANE = "#0b1017"
LANE_LINE = "#1b2430"
CARD = "#101823"
CARD_LINE = "#233041"
INK = "#efe9d8"          # warm paper
MUTED = "#93a3b4"
ACCENT = "#f2cf8f"       # the gold the pane uses
CODE = "#cfd6dd"
WARN = "#e08a6a"
DIM = "#6b7c8d"

W = 1760
M = 32

LANES = [
    # name, x, width, subtitle
    ("A PERSON", 32, 340, "starts it, reads it"),
    ("THE ENGINE", 408, 780, "the state, the dose, the account"),
    ("THE AGENT TURN", 1224, 504, "where the block lands"),
]
SOURCES_X, SOURCES_W = 408, 1320


def esc(t: str) -> str:
    return html.escape(t, quote=False)


def wrap(text: str, width: int) -> list[str]:
    """Greedy wrap on words, for lines I did not pre-split."""
    out, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if len(trial) <= width:
            line = trial
        else:
            if line:
                out.append(line)
            line = word
    if line:
        out.append(line)
    return out


class Card:
    """A box: title, then body lines. A line is a string or ('code', text)."""

    def __init__(self, title: str, body: list, tone: str = "card", note: str = ""):
        self.title = title
        self.body = body
        self.tone = tone          # card | warn | quiet
        self.note = note
        self.x = self.y = self.w = self.h = 0

    def measure(self, w: int) -> None:
        self.w = w
        pad = 13
        inner = w - 2 * pad
        self.lines: list[tuple[str, str]] = []
        for item in self.body:
            if isinstance(item, tuple):
                kind, text = item
                if kind == "code":
                    self.lines.append(("code", text))
                else:
                    for part in wrap(text, int(inner / 6.9)):
                        self.lines.append(("text", part))
            else:
                for part in wrap(item, int(inner / 6.9)):
                    self.lines.append(("text", part))
        h = pad + 19 + 7
        for kind, _ in self.lines:
            h += 17 if kind == "code" else 18
        self.h = h + pad - 2

    def draw(self) -> str:
        fill = CARD if self.tone == "card" else ("#151009" if self.tone == "warn" else LANE)
        line = CARD_LINE if self.tone != "warn" else "#4a3126"
        out = [
            f'<rect x="{self.x}" y="{self.y}" width="{self.w}" height="{self.h}" rx="10" '
            f'fill="{fill}" stroke="{line}"/>'
        ]
        ty = self.y + 13 + 15
        title_fill = WARN if self.tone == "warn" else INK
        out.append(
            f'<text x="{self.x + 13}" y="{ty}" font-size="15.5" font-weight="600" '
            f'fill="{title_fill}">{esc(self.title)}</text>'
        )
        y = ty + 7 + 13
        for kind, text in self.lines:
            if kind == "code":
                out.append(
                    f'<text x="{self.x + 13}" y="{y}" font-size="12" fill="{CODE}" '
                    f'font-family="ui-monospace, Menlo, monospace">{esc(text)}</text>'
                )
                y += 17
            else:
                out.append(
                    f'<text x="{self.x + 13}" y="{y}" font-size="13" fill="{MUTED}">{esc(text)}</text>'
                )
                y += 18
        return "\n".join(out)

    # anchors
    @property
    def right(self) -> tuple[float, float]:
        return (self.x + self.w, self.y + self.h / 2)

    @property
    def left(self) -> tuple[float, float]:
        return (self.x, self.y + self.h / 2)

    @property
    def top(self) -> tuple[float, float]:
        return (self.x + self.w / 2, self.y)

    @property
    def bottom(self) -> tuple[float, float]:
        return (self.x + self.w / 2, self.y + self.h)


def stack(cards: list[Card], x: int, w: int, y: int, gap: int = 14) -> list[Card]:
    for c in cards:
        c.measure(w)
        c.x, c.y, c.w = x, y, w
        y += c.h + gap
    return cards


def arrow(x1, y1, x2, y2, label="", dashed=False, curve=0.0, label_dx=0, label_dy=-8) -> str:
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    # a quadratic control point pulled toward the middle gives a gentle bend
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2 + curve
    path = f"M {x1:.1f} {y1:.1f} Q {cx:.1f} {cy:.1f} {x2:.1f} {y2:.1f}"
    out = [f'<path d="{path}" fill="none" stroke="{ACCENT}" stroke-opacity="0.5" '
           f'stroke-width="1.6"{dash} marker-end="url(#arrow)"/>']
    if label:
        lx, ly = (x1 + x2) / 2 + label_dx, (y1 + y2) / 2 + label_dy
        out.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11.5" fill="{DIM}" text-anchor="middle" '
            f'letter-spacing="0.4">{esc(label)}</text>'
        )
    return "\n".join(out)


def path_arrow(points: list[tuple[float, float]], label="", label_at=None, dashed=True) -> str:
    """A routed polyline with rounded corners."""
    d = f"M {points[0][0]:.1f} {points[0][1]:.1f}"
    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        d += f" L {x1:.1f} {y1:.1f}"
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    out = [f'<path d="{d}" fill="none" stroke="{ACCENT}" stroke-opacity="0.38" stroke-width="1.5" '
           f'stroke-linejoin="round"{dash} marker-end="url(#arrow)"/>']
    if label and label_at:
        out.append(
            f'<text x="{label_at[0]:.1f}" y="{label_at[1]:.1f}" font-size="11.5" fill="{DIM}" '
            f'text-anchor="middle">{esc(label)}</text>'
        )
    return "\n".join(out)


def build() -> str:
    # ---------------------------------------------------------------- lane 1: the person
    p_start = Card("A person starts a state", [
        ("code", "/walk  /explore"),
        "explore is the person's own map to fly",
        "or the agent calls the state tool",
        "or a recommendation is followed, if the setting is on",
        "one state owns the profile at a time",
    ])
    p_work = Card("and keeps working", [
        "their message is journalled as a note",
        "the injected block never reaches their eyes",
        "they see the reply, the annotation, the account",
    ])
    p_reply = Card("gets the reply", [
        "the model's words, plus an annotation",
        ("code", "— walking · 5 hops left · /return"),
    ])
    p_account = Card("reads the account", [
        "the closing turn says it, in the house voice",
        "if the model skips it the plugin appends the line",
        "counts, not quotes — the privacy constraint",
    ])
    p_panes = Card("watches the panes", [
        "Antemuse pane: the map, 320–560px, right",
        "Cockpit pane: the same map, first person",
        "both poll /state; nothing navigates by itself",
    ])
    p_explore = Card("flies /explore", [
        "cockpit, lasso picks, PICK / LIT",
        "no dose, no clock, no provider",
        "ends only when they type /return",
    ])
    p_gap = Card("drops a state silently", [
        "entering a second state leaves the first with",
        "no account: “left walk; no residue kept”",
    ], tone="warn")

    stack([p_start, p_work, p_reply, p_account, p_panes, p_explore, p_gap],
          32, 340, 196, gap=14)

    # ---------------------------------------------------------------- lane 2: the engine
    e_enter = Card("enter() — the state begins", [
        "resolve the name · sources.ready() refuses without corpora",
        "write active: key, origin (session · platform · project),",
        "dose + unit, entered_at, work counters reset",
        ("code", "returns  WALKING · 6 hops · work continues · the frame is elsewhere"),
    ])
    e_inject = Card("inject() — once per turn", [
        "deliver_if_due(): serve the next unit for this state",
        "_expire(): no clock — time passing is not a reason for anything",
        "build the block, then complete_if_dosed()",
    ])
    e_dose = Card("the dose is the whole promise", [
        "served = units fetched     seen = units shown to a turn",
        "a unit is spent only when it has been shown, so a pane poll",
        "may serve ahead but can never complete a state",
        "dose ends it — not a duration, not a ceiling",
    ])
    e_stop = Card("stop() — the ending", [
        "build the account from the journal (this state only)",
        "append a residue report with 2 turns left",
        "the notifier posts it the moment the state closes",
        "normal records turns-to-dose, so the cost is measurable",
    ])
    e_fail = Card("failure paths, all named", [
        ("code", "cannot enter · wordnet unavailable"),
        ("code", "feed unavailable · <source>"),
        ("code", "/graph 401/403 → sign-in required"),
        ("code", "404 → backend not mounted"),
        ("code", "5xx → the backend did not answer"),
        "no answer at all → reconnecting → backend unavailable",
    ])
    e_quiet = Card("nothing on the state path calls a model", [
        "a state is arithmetic and memory: WordNet walks,",
        "a WordNet walk and the concept ledger",
        "so a state costs tokens only through its directive",
    ], tone="quiet")

    stack([e_enter, e_inject, e_dose, e_stop, e_fail, e_quiet],
          408, 780, 196, gap=14)

    # ---------------------------------------------------------------- lane 3: the agent turn
    a_enter = Card("the agent enters one too", [
        ("code", "state(action='enter', name='walk')"),
        "same handler, same dose, same account",
        "the escape hatch survives every state",
    ])
    a_pre = Card("pre_llm_call", [
        "note_turn · tick · journal the message",
        "inject() returns this turn's block",
    ])
    a_block = Card("the block", [
        ("code", "[STATE: WALKING · 5/6 hops left]"),
        "directive — the shape this turn takes",
        "tool rule — open unless the entry closed it",
        ("code", "[WHAT ARRIVED] — only if the state feeds"),
        ("code", "[YOU JUST CAME BACK] + the account"),
        ("code", "[RESIDUE] · the recommendation line"),
    ])
    a_work = Card("the model works", [
        "pre_tool_call: the policy allows or blocks",
        "post_tool_call: did the tool work",
    ])
    a_transform = Card("transform_llm_output", [
        "annotate the reply, while a state runs",
        "append the report if the model skipped it",
        "append the run's account, counts only",
    ])
    a_reply = Card("reply", [
        "the person sees the reply and the annotation",
        "the loop runs again next turn",
    ])

    stack([a_enter, a_pre, a_block, a_work, a_transform, a_reply],
          1224, 504, 196, gap=14)

    # ---------------------------------------------------------------- sources strip
    chips = [
        ("walk · WordNet", "six hops, one per turn, out to the rim"),
        ("cockpit · the map", "the same /graph payload, flown by hand"),
        ("explore · the person", "picks only; no provider at all"),
        ("verdicts · the ledger", "keep / trash, counted by tools/hit_rate.py"),
    ]
    store = ("state.json", "active · journal (cap 60) · residue · ledger · mood · work")

    tallest = max(e_quiet.y + e_quiet.h, p_gap.y + p_gap.h, a_reply.y + a_reply.h)
    strip_y = tallest + 56
    strip_h = 168

    # ---------------------------------------------------------------- lane backgrounds
    lane_bottom = strip_y - 22
    out = [
        f'<rect x="0" y="0" width="{W}" height="10" fill="{BG}"/>',
    ]
    for name, x, w, sub in LANES:
        out.append(
            f'<rect x="{x}" y="150" width="{w}" height="{lane_bottom - 150}" rx="14" '
            f'fill="{LANE}" stroke="{LANE_LINE}"/>'
        )
        out.append(
            f'<text x="{x + 18}" y="180" font-size="12.5" fill="{ACCENT}" letter-spacing="2.4" '
            f'font-weight="600">{esc(name)}</text>'
        )
        out.append(
            f'<text x="{x + 18}" y="196" font-size="11.5" fill="{DIM}">{esc(sub)}</text>'
        )

    # ---------------------------------------------------------------- title
    out += [
        f'<text x="32" y="62" font-size="30" font-weight="600" fill="{INK}">'
        f'Antemuse — the functional flow</text>',
        f'<text x="32" y="90" font-size="14" fill="{MUTED}">'
        f'one agent state, one dose, one account · drawn from core/engine.py, core/states.py and '
        f'__init__.py at 0.10.44</text>',
        f'<text x="32" y="112" font-size="12.5" fill="{DIM}">'
        f'solid arrows are the ordinary path · dashed arrows are the return path · '
        f'orange boxes are known gaps</text>',
    ]
    # legend glyphs
    out.append(f'<rect x="{W - 300}" y="40" width="12" height="12" rx="3" fill="{CARD}" stroke="{CARD_LINE}"/>')
    out.append(f'<text x="{W - 280}" y="51" font-size="12" fill="{MUTED}">a component</text>')
    out.append(f'<rect x="{W - 300}" y="64" width="12" height="12" rx="3" fill="#151009" stroke="#4a3126"/>')
    out.append(f'<text x="{W - 280}" y="75" font-size="12" fill="{MUTED}">a known gap</text>')

    # ---------------------------------------------------------------- cards
    for c in (p_start, p_work, p_reply, p_account, p_panes, p_explore, p_gap,
              e_enter, e_inject, e_dose, e_stop, e_fail, e_quiet,
              a_enter, a_pre, a_block, a_work, a_transform, a_reply):
        out.append(c.draw())

    # ---------------------------------------------------------------- arrows
    # person → engine: the command lands in enter()
    out.append(arrow(p_start.right[0], p_start.right[1], e_enter.left[0], e_enter.left[1],
                     "command or tool", label_dy=-9))
    # engine → agent: the block goes into the turn
    out.append(arrow(e_inject.right[0], e_inject.right[1], a_pre.left[0], a_pre.left[1],
                     "this turn's block", label_dy=-9))
    # agent → engine: the turn was taken, so the unit has been seen
    out.append(arrow(a_transform.left[0], a_transform.left[1], e_dose.right[0], e_dose.right[1],
                     "turn taken · seen", label_dy=-9))
    # engine → person: the account
    out.append(arrow(e_stop.left[0], e_stop.left[1], p_account.right[0], p_account.right[1],
                     "the account", label_dy=-9))
    # sources → engine: one unit per turn, up the middle
    out.append(arrow(SOURCES_X + SOURCES_W / 2, strip_y - 4, e_dose.bottom[0], e_dose.bottom[1] + 6,
                     "one unit per turn", label_dy=0, label_dx=0))
    # the reply, routed under the engine lane so it does not cross a card
    corridor = lane_bottom + 16
    out.append(path_arrow([
        (a_reply.left[0], a_reply.left[1]),
        (a_reply.left[0] - 22, a_reply.left[1]),
        (a_reply.left[0] - 22, corridor),
        (p_reply.right[0] + 26, corridor),
        (p_reply.right[0] + 26, p_reply.right[1]),
        (p_reply.right[0], p_reply.right[1]),
    ], "the reply", label_at=((a_reply.left[0] - 22 + p_reply.right[0] + 26) / 2, corridor - 7)))

    # ---------------------------------------------------------------- sources strip
    out.append(
        f'<rect x="{SOURCES_X}" y="{strip_y}" width="{SOURCES_W}" height="{strip_h}" rx="14" '
        f'fill="{LANE}" stroke="{LANE_LINE}"/>'
    )
    out.append(
        f'<text x="{SOURCES_X + 18}" y="{strip_y + 30}" font-size="12.5" fill="{ACCENT}" '
        f'letter-spacing="2.4" font-weight="600">SOURCES &amp; STORE</text>'
    )
    out.append(
        f'<text x="{SOURCES_X + 178}" y="{strip_y + 30}" font-size="11.5" fill="{DIM}">'
        f'where a unit comes from — and what survives</text>'
    )
    chip_w = (SOURCES_W - 18 * 2 - 5 * 12) / 6
    for i, (title, sub) in enumerate(chips):
        cx = SOURCES_X + 18 + i * (chip_w + 12)
        out.append(
            f'<rect x="{cx:.1f}" y="{strip_y + 50}" width="{chip_w:.1f}" height="54" rx="8" '
            f'fill="{CARD}" stroke="{CARD_LINE}"/>'
        )
        out.append(
            f'<text x="{cx + 11:.1f}" y="{strip_y + 72}" font-size="13" font-weight="600" '
            f'fill="{INK}">{esc(title)}</text>'
        )
        for j, part in enumerate(wrap(sub, 26)):
            out.append(
                f'<text x="{cx + 11:.1f}" y="{strip_y + 90 + j * 15}" font-size="11.5" '
                f'fill="{MUTED}">{esc(part)}</text>'
            )
    # the store chip, wider, under the agent lane
    sx = SOURCES_X + SOURCES_W - 268
    out.append(
        f'<rect x="{sx}" y="{strip_y + 116}" width="250" height="34" rx="8" fill="{CARD}" '
        f'stroke="{CARD_LINE}"/>'
    )
    out.append(
        f'<text x="{sx + 11}" y="{strip_y + 132}" font-size="13" font-weight="600" fill="{INK}">'
        f'.antemuse/{esc(store[0])}</text>'
    )
    out.append(
        f'<text x="{sx + 11}" y="{strip_y + 145}" font-size="11" fill="{MUTED}">{esc(store[1])}</text>'
    )

    # ---------------------------------------------------------------- endings strip
    ey = strip_y + strip_h + 26
    out.append(
        f'<text x="32" y="{ey}" font-size="12.5" fill="{ACCENT}" letter-spacing="2.4" '
        f'font-weight="600">HOW A STATE ENDS</text>'
    )
    endings = [
        ("complete", "the dose is served and seen, and at least one turn was worked",
         "“The act is done, so the state is over.”"),
        ("failed", "the source died, or a turn ran dry having served nothing",
         "“nothing arrived” — and the reason is named"),
        ("returned", "the person typed /return",
         "“The frame you were in is gone. State the goal…”"),
        ("superseded", "another state was entered instead",
         "no account — the known gap"),
    ]
    ew = (W - 64 - 3 * 12) / 4
    for i, (name, why, quote) in enumerate(endings):
        ex = 32 + i * (ew + 12)
        tone = "warn" if name == "superseded" else "card"
        fill = "#151009" if tone == "warn" else CARD
        line = "#4a3126" if tone == "warn" else CARD_LINE
        out.append(
            f'<rect x="{ex:.1f}" y="{ey + 14}" width="{ew:.1f}" height="86" rx="10" fill="{fill}" '
            f'stroke="{line}"/>'
        )
        out.append(
            f'<text x="{ex + 13:.1f}" y="{ey + 38}" font-size="14" font-weight="600" '
            f'fill="{WARN if tone == "warn" else INK}">{esc(name)}</text>'
        )
        for j, part in enumerate(wrap(why, 44)):
            out.append(
                f'<text x="{ex + 13:.1f}" y="{ey + 57 + j * 15}" font-size="11.5" fill="{MUTED}">'
                f'{esc(part)}</text>'
            )
        out.append(
            f'<text x="{ex + 13:.1f}" y="{ey + 92}" font-size="11.5" fill="{DIM}" '
            f'font-style="italic">{esc(quote)}</text>'
        )

    height = ey + 130
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" '
        f'viewBox="0 0 {W} {height}" font-family="Inter, \'DejaVu Sans\', system-ui, sans-serif">\n'
        f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{ACCENT}" fill-opacity="0.75"/></marker></defs>\n'
        f'<rect x="0" y="0" width="{W}" height="{height}" fill="{BG}"/>'
    )
    return head + "\n" + "\n".join(out) + "\n</svg>\n"


if __name__ == "__main__":
    svg = build()
    out = Path(__file__).with_name("antemuse-flow.svg")
    out.write_text(svg)
    print(f"wrote {out} ({len(svg):,} bytes)")
