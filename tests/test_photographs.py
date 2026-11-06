"""Pictures in the terminal: cells, dissolves, and no words."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))

from core import photographs, tui  # noqa: E402


def _cells(colour, cols=12, rows=4):
    """A field of cells with the same colour on both halves of each cell."""
    return photographs.solid(colour, cols, rows)


def _is(cell, colour):
    return cell == (colour, colour)


def test_blend_is_a_dissolve_between_two_images():
    a, b = _cells((0, 0, 0)), _cells((255, 255, 255))
    assert photographs.blend(a, b, 0.0) == a
    assert photographs.blend(a, b, 1.0) == b
    mid = photographs.blend(a, b, 0.5)
    blacks = sum(1 for row in mid for c in row if _is(c, (0, 0, 0)))
    total = sum(len(r) for r in mid)
    assert 0.25 < blacks / total < 0.75, "half-way should be roughly half of each"


def test_blend_advances_monotonically():
    a, b = _cells((0, 0, 0)), _cells((255, 255, 255))
    counts = []
    for step in range(9):
        cells = photographs.blend(a, b, step / 8)
        counts.append(sum(1 for row in cells for c in row if _is(c, (255, 255, 255))))
    assert counts == sorted(counts)
    assert counts[0] == 0 and counts[-1] == 48


def test_rows_use_truecolor_half_blocks():
    rows = photographs.to_rows(_cells((10, 20, 30), cols=4, rows=2))
    assert len(rows) == 2
    assert "\x1b[38;2;10;20;30m" in rows[0]
    assert "\x1b[48;2;10;20;30m" in rows[0]
    assert "▀" in rows[0]


def test_rows_paint_top_and_bottom_differently():
    cell = ((10, 20, 30), (40, 50, 60))
    rows = photographs.to_rows([[cell]])
    assert "\x1b[38;2;10;20;30m\x1b[48;2;40;50;60m" in rows[0]


def test_overlay_draws_glyphs_instead_of_pixels():
    rows = photographs.to_rows(_cells((0, 0, 0), cols=6, rows=1), overlay=["  ●  ▮ "])
    assert "●" in rows[0] and "▮" in rows[0]


def _state(key):
    return {"active": {"key": key, "label": key.upper()}, "journal": [], "residue": []}


def test_frames_are_full_size_and_wordless():
    import re
    rows = tui.imagery_frame(_state("walk"), 60, 14, 0)
    assert len(rows) == 14
    plain = [re.sub(r"\x1b\[[0-9;]*m", "", r) for r in rows]
    assert not re.search(r"[A-Za-z]{2,}", "\n".join(plain))


def test_changing_state_starts_a_dissolve():
    tui._LAST.clear()
    tui._LAST.update({"key": None, "cells": None})
    tui.imagery_frame(_state("walk"), 48, 12, 0)
    tui.imagery_frame(_state("walk"), 48, 12, 1)
    tui.imagery_frame(_state("dream"), 48, 12, 2)
    assert tui._LAST.get("transition"), "a state change should start a dissolve"
    tui.imagery_frame(_state("dream"), 48, 12, 40)
    assert not tui._LAST.get("transition"), "the dissolve should end"
