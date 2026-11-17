"""The pane's picture must be chosen by the same registry the engine uses.

The strand table (`SCENES`) is the pane's own copy of "which states exist". It has already
drifted once: `unstuck` was added to the registry in 0.11.21 and not to the table, so a person
entering `/unstuck` got the `idle` picture and no way to see they were in a state. That is the
same class of bug as the one-state cut — a literal list kept beside a registry that outgrew it —
so these tests read the real file and compare it to the real registry rather than trusting
either.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import states  # noqa: E402

PANE = Path(__file__).resolve().parent.parent / "desktop" / "plugin.js"
SOURCE = PANE.read_text()


def _scene_keys() -> set[str]:
    table = SOURCE[SOURCE.index("const SCENES = {"):]
    table = table[: table.index("\n}")]
    return set(re.findall(r"^  (\w+):\s+\{ strands:", table, re.M))


def _no_field() -> set[str]:
    found = re.search(r"const NO_FIELD = new Set\(\[([^\]]*)\]\)", SOURCE)
    return set(re.findall(r"'([a-z]+)'", found.group(1))) if found else set()


def test_every_agent_state_has_a_picture_or_a_reason_not_to():
    """A state either has a field or says why it has none. Silence is what hid unstuck."""
    missing = set(states.STATES) - _scene_keys() - _no_field()
    assert not missing, f"states with no picture and no reason (they draw idle): {sorted(missing)}"


def test_the_only_stateless_picture_is_the_one_that_must_not_draw_material():
    assert _no_field() == {"doomscroll"}, (
        "feed text is untrusted and never persisted, so doomscroll draws nothing; "
        "any other state in this set is a picture that went missing"
    )


def test_nothing_fired_is_its_own_picture():
    """`bare` must exist and must draw nothing, so 'nothing has arrived' is not stand-in art."""
    keys = _scene_keys()
    assert "bare" in keys
    assert re.search(r"^  bare:\s+\{ strands: 0,", SOURCE, re.M), "bare must have zero strands"
    assert re.search(r"^  bare: \[\],", SOURCE, re.M), "bare must have an empty composition"


def test_a_state_that_has_fired_nothing_is_drawn_bare_not_idle():
    """Zero material is a state of its own; it must not be drawn as the idle picture."""
    assert "export function sceneFor(" in SOURCE
    body = SOURCE[SOURCE.index("export function sceneFor("):]
    body = body[: body.index("\n}")]
    # The three answers the rule can give, and the one it must give for zero material.
    assert "served <= 0" in body, "the rule must test the served count"
    assert "'bare'" in body, "a running state with nothing served must draw bare"
    assert "busy ? 'work' : 'idle'" in body, "no state: work while a turn runs, idle otherwise"


def test_the_selection_is_not_a_second_literal():
    """The poll must ask the rule, not repeat the table lookup inline."""
    poll = SOURCE[SOURCE.index("const poll = () =>"):]
    poll = poll[: poll.index("probe.state")]
    assert "art.setScene(sceneFor(active, busy))" in poll
    assert "SCENES[" not in poll, "the poll grew its own copy of the table again"
