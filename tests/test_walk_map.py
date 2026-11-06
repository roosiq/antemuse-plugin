"""The walk map: parsed from the journal, sized to the terminal, safe to print."""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import walk_map  # noqa: E402


def _event(a, b, how, gloss="", at=None):
    return {"who": "state", "state": "walk", "event": "walk", "at": at or time.time(),
            "text": f"{a} (noun) → {b} (noun) · {how}" + (f" · “{gloss}”" if gloss else "")}


def _state(events):
    return {"active": {"key": "walk", "label": "WALKING"}, "journal": events}


def test_parse_tracks_depth_by_relation():
    nodes = walk_map.parse([
        _event("hand", "extremity", "went up to its hypernym"),
        _event("extremity", "external body part", "went up to its hypernym"),
        _event("external body part", "body part", "went down into a hyponym"),
    ])
    assert [n["depth"] for n in nodes] == [1, 2, 1]
    assert nodes[-1]["label"] == "body part"


def test_parse_ignores_other_states_and_bad_lines():
    events = [
        {"who": "state", "event": "dream", "text": "invented · a thing", "at": 0},
        {"who": "agent", "event": "walk", "text": "hand → foot", "at": 0},
        _event("hand", "extremity", "went up to its hypernym"),
    ]
    assert len(walk_map.parse(events)) == 1


def test_person_step_joins_the_same_path():
    events = [_event("hand", "extremity", "went up to its hypernym"),
              {"who": "person", "event": "walk_person", "text": "salt · a seasoning", "at": time.time()}]
    nodes = walk_map.parse(events)
    assert nodes[-1]["person"] is True
    assert nodes[-1]["label"] == "salt"
    rows = walk_map.strip(walk_map.render(_state(events), 100, 20))
    assert any("◆" in r for r in rows)


def test_frame_is_exactly_the_requested_size():
    rows = walk_map.render(_state([_event("hand", "extremity", "went up to its hypernym")]), 96, 18)
    assert len(rows) == 18
    assert all(len(walk_map.strip([r])[0]) <= 96 for r in rows)


def test_empty_walk_shows_a_single_marker_and_no_words():
    import re
    rows = walk_map.strip(walk_map.render(_state([]), 80, 12))
    text = "\n".join(rows)
    assert "◌" in text or "○" in text
    assert not re.search(r"[A-Za-z]{2,}", text)


def test_bare_map_has_no_instrumentation():
    import re
    events = [_event("hand", "extremity", "went up to its hypernym"),
              _event("extremity", "body part", "went down into a hyponym")]
    bare = "\n".join(walk_map.strip(walk_map.render(_state(events), 100, 20)))
    assert not re.search(r"[A-Za-z]{2,}", bare)
    debug = "\n".join(walk_map.strip(walk_map.render(_state(events), 100, 20, bare=False)))
    assert "STEP 02" in debug and "DEPTH" in debug
