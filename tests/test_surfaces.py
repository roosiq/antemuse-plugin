"""Every client gets the same state, encoded for what it can show."""
from __future__ import annotations

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="states-surfaces-")

from core import surfaces  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402


def setup_module(_):
    """The art renderer reads pre-rendered frames; seed the temp profile with one."""
    src = Path("/home/ryan/.hermes/plugin-data/antemuse/three_frames")
    dst = Path(os.environ["ANTEMUSE_STATES_HOME"]) / "three_frames"
    dst.mkdir(parents=True, exist_ok=True)
    cands = sorted(src.glob("*.png")) or [
        p for d in sorted(src.iterdir()) if d.is_dir() for p in sorted(d.glob("*.png"))[:1]
    ] if src.is_dir() else []
    for png in cands[:3]:
        shutil.copy(png, dst / png.name)


def state(active=True):
    now = time.time()
    return {
        "active": {"key": "walk", "label": "WALKING", "contract": "observations, not conclusions",
                   "directive": "x", "seconds_left": 415, "total_seconds": 480,
                   "turns_left": 3, "tools": []} if active else None,
        "journal": [
            {"who": "agent", "state": "walk", "text": "I notice I have no sidewalk and no weather, so a street would be invention.", "at": now},
            {"who": "person", "state": "walk", "text": "the fridge stopping mid-hum, then starting again", "at": now},
        ],
        "residue": [], "now": now,
    }


def test_chat_card_has_no_escape_codes():
    out = surfaces.card(state(), "discord")
    assert "\x1b" not in out


def test_chat_card_fits_its_width():
    for name in ("discord", "discord_desktop", "telegram", "slack", "text"):
        w = surfaces.profile(name)["width"]
        out = surfaces.card(state(), name)
        body = [l for l in out.splitlines() if l != "```"]
        assert max(len(l) for l in body) <= w + 2, name


def test_chat_cards_are_fenced_but_terminal_is_not():
    assert surfaces.card(state(), "discord").startswith("```")
    assert not surfaces.card(state(), "text").startswith("```")


def test_narrow_mode_is_mobile_safe():
    out = surfaces.card(state(), "discord", narrow=True)
    body = [l for l in out.splitlines() if l != "```"]
    assert max(len(l) for l in body) <= 38
    assert len(out) < 1800


def test_card_is_only_a_picture():
    import re
    out = surfaces.card(state(), "discord")
    assert not re.search(r"[A-Za-z]{2,}", out), "the person must not see prose"


def test_idle_card_is_still_only_a_picture():
    import re
    out = surfaces.card(state(False), "discord")
    assert not re.search(r"[A-Za-z]{2,}", out)


def test_ascii_art_is_plain_and_non_empty():
    rows = surfaces.art(44, 10)
    assert rows, "no rendered frames found"
    for r in rows:
        assert not any(ord(c) > 126 for c in r), "art must be 7-bit ASCII"
    assert any(ch != " " for r in rows for ch in r), "art rendered entirely blank"


def test_record_is_dense_and_plain():
    out = surfaces.record(state())
    assert "\x1b" not in out
    assert "state walk" in out
    assert "agent walk ::" in out


def test_snapshot_writes_a_png():
    path = surfaces.snapshot_path(state(), "discord")
    assert path.exists() and path.stat().st_size > 500
    with open(path, "rb") as fh:
        assert fh.read(8) == b"\x89PNG\r\n\x1a\n"
