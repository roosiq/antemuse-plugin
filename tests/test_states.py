"""The surviving walk mechanics."""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="states-test-")

from core import engine, recall, sources, states  # noqa: E402


def setup_function(_):
    engine.clear()


def _provider(*lines):
    queue = list(lines)

    def call(_n):
        return [queue.pop(0)] if queue else []

    return call


def test_a_walk_leaves_every_tool_open():
    engine.enter("walk")
    directive = engine.inject() or ""
    assert "walking while you work" in directive
    assert "No tools in this state" not in directive
    assert engine.policy("terminal") is None
    assert engine.policy("web_search") is None


def test_a_state_does_not_take_tools_away_unless_asked():
    engine.enter("walk")
    assert engine.policy("terminal") is None
    assert engine.policy("write_file") is None
    assert "Tools are open in this state" in (engine.inject() or "")


def test_an_entry_may_narrow_the_set_without_editing_the_state():
    engine.enter("walk", block=True, allow=["read_file"])
    assert engine.policy("read_file") is None
    assert engine.policy("write_file")["action"] == "block"
    assert "Only these tools: read_file." in (engine.inject() or "")


def test_allow_without_block_is_refused_and_enters_nothing():
    from core import options
    import pytest

    with pytest.raises(ValueError, match="block: true"):
        options.parse({"allow": ["read_file"]})
    assert engine.peek() is None


def test_state_ends_when_the_dose_is_delivered_and_leaves_residue(monkeypatch):
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = _provider(*[f"hop {n} → landing {n}" for n in range(6)])
    try:
        engine.enter("walk", session="dose")
        for _ in range(6):
            engine.note_turn("dose")
            engine.inject("dose")
        assert engine.peek() is None
        reports = [r for r in engine.watch_state()["residue"] if r.get("kind") == "report"]
        assert reports and reports[-1]["reason"] == "complete"
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_clock_in_the_past_no_longer_ends_a_state():
    engine.enter("walk")
    path = pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    data = json.loads(path.read_text())
    data["active"]["ends_at"] = time.time() - 1
    path.write_text(json.dumps(data))
    assert engine.peek()["key"] == "walk"


def test_return_ends_the_state_and_keeps_residue():
    engine.enter("walk")
    assert "ended" in engine.stop()
    assert engine.peek() is None
    assert "walk" in engine.status()


def test_entering_a_new_walk_does_not_inherit_the_last_walks_material():
    engine.enter("walk", session="one")
    engine.record("state", "old material", event="walk")
    engine.stop("one")
    engine.enter("walk", session="two")
    engine.record("state", "new material", event="walk")
    data = engine._load()
    started = data["active"]["entered_at"]
    current = [e["text"] for e in data["journal"] if e.get("at", 0) >= started and e.get("who") == "state"]
    assert "new material" in current
    assert "old material" not in current


def test_a_turn_brings_material_the_dead_thread_missed(monkeypatch):
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = _provider("salt → brine", "brine → cure")
    try:
        engine.enter("walk", session="turn")
        engine.note_turn("turn")
        assert engine.deliver_if_due() == 1
        # A second call inside the same turn buys nothing; the next turn buys the next hop.
        assert engine.deliver_if_due() == 0
        engine.note_turn("turn")
        assert engine.deliver_if_due() == 1
        lines = [e["text"] for e in engine._load()["journal"] if e.get("who") == "state"]
        assert lines == ["salt → brine", "brine → cure"]
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_walk_supplies_nothing_to_the_working_turn():
    engine.enter("walk")
    engine.record("state", "hand (n) → palm (n) · took its far edge", event="walk")
    text = engine.inject() or ""
    assert "[WHAT ARRIVED" not in text
    assert "palm" not in text


def test_a_walk_ends_by_taking_the_frame_away():
    engine.enter("walk")
    engine.record("state", "hand (n) → palm (n) · took its far edge", event="walk")
    engine.inject()
    assert "different first step" in engine.stop()


def test_a_state_records_where_it_was_started():
    engine.enter("walk", session="sess-A", platform="discord")
    origin = engine.peek()["origin"]
    assert origin["session_id"] == "sess-A"
    assert origin["platform"] == "discord"
    assert "project" in origin


def test_another_session_cannot_collect_the_account():
    engine.enter("walk", session="sess-A", platform="discord")
    engine.record("state", "hand (n) → palm (n) · took its meronym", event="walk")
    out = engine.stop("sess-B")
    assert "running in the session that started it" in out
    assert engine.peek() is not None
    assert "ended" in engine.stop("sess-A")


def test_the_account_counts_material_not_the_agents_own_words():
    engine.enter("walk")
    engine.record("state", "salt (n) → brine (n) · took its hyponym", event="walk")
    engine.record("agent", "the salt made the water feel heavier", event="walk")
    out = engine.stop()
    assert "1 of 6 hops" in out
    assert "salt→brine [hyponym]" in out
    assert "heavier" not in out


def test_the_account_never_quotes_the_material_it_was_given():
    engine.enter("walk", session="CHAT-A", platform="discord")
    engine.record("state", "JOINED · my private material · possibility · something", event="walk")
    engine.stop("CHAT-A")
    said = engine.unreported("CHAT-A")
    assert said
    assert "private material" not in said["text"]


def test_unknown_state_is_refused():
    assert "no such state" in engine.enter("levitate")


def test_every_state_declares_a_contract_and_a_residue():
    assert set(states.STATES) == {"walk", "daydream", "doomscroll", "dream", "unstuck"}
    for key, spec in states.STATES.items():
        assert spec["contract"] and spec["residue"] and spec["directive"], key
        assert spec["label"] and spec["dose"], key


def test_a_dream_names_the_concepts_it_served(git_repo):
    """The landing line is what the person reads. A count of "2 recombinations" says something
    happened; the labels say what it was about, and they come from the ledger, not the prose."""
    for line in ("A recorded turn about a harbor crane and its rusted cable.",
                 "Another turn about a ticket queue and a paper lantern.",
                 "A third turn about a diesel generator and a coil of rope."):
        recall.remember(line)
    engine.enter("dream", session="S-DREAM-NAMES")
    for _ in range(2):
        engine.note_turn("S-DREAM-NAMES")
        engine.inject("S-DREAM-NAMES")
    said = engine.stop("S-DREAM-NAMES", reason="dose") or ""
    assert "concepts: " in said, said
    labels = said.split("concepts: ", 1)[1].strip().rstrip(".").strip()
    assert len(labels) > 3, said


def test_daydream_keeps_its_count_and_names_nothing():
    """Daydream's material is the person's own recorded turns. Naming the concepts would put
    their memory text back in front of them, so it reports how many joined, never which."""
    for line in ("A recorded turn about a harbor crane and its rusted cable.",
                 "Another turn about a ticket queue and a paper lantern.",
                 "A third turn about a diesel generator and a coil of rope."):
        recall.remember(line)
    engine.enter("daydream", session="S-DAY-QUIET")
    for _ in range(2):
        engine.note_turn("S-DAY-QUIET")
        engine.inject("S-DAY-QUIET")
    said = engine.stop("S-DAY-QUIET", reason="dose") or ""
    assert "concepts: " not in said, said
    assert "harbor crane" not in said and "paper lantern" not in said, said


def test_dream_enters_when_today_is_quiet_but_the_project_is_not(tmp_path):
    """A quiet day is not an empty project.

    dream used to read the last 24 hours only, so a chat in a repository whose last commit was
    ten days old was refused at the door with "fewer than three local git commit subjects" —
    which is a membership test for a dream, not a description of the work.
    """
    import subprocess

    from core import sources

    repo = tmp_path / "quiet-project"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "a.txt").write_text("one\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    for n in range(3):
        (repo / "a.txt").write_text(f"{n}\n")
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
        env = {
            "GIT_AUTHOR_NAME": "e2e", "GIT_AUTHOR_EMAIL": "e2e@example.invalid",
            "GIT_COMMITTER_NAME": "e2e", "GIT_COMMITTER_EMAIL": "e2e@example.invalid",
            "GIT_AUTHOR_DATE": f"2026-11-{5 + n:02d}T10:00:00",
            "GIT_COMMITTER_DATE": f"2026-11-{5 + n:02d}T10:00:00",
        }
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", f"quiet work {n}"],
                       check=True, env={**os.environ, **env})

    assert sources._git_subjects(repo) == [], "today is empty"
    assert len(sources._recent_subjects(repo)) == 3, "the project is not"


def test_walk_takes_its_six_hops_in_the_call_that_asked():
    """`/walk` is an act, not a meter the person fills.

    Six hops used to be owed across six turns, so finishing one walk meant typing five messages
    that said nothing. The command takes the whole dose there and then and answers with the path.
    """
    from core import engine
    out = engine.perform("walk", session="one-call")
    assert "6 of 6 hops" in out, out
    assert out.count("→") >= 5, out
    assert engine.peek() is None, "nothing is left running for the person to feed"
    data = engine._load()
    assert int((data.get("work") or {}).get("turns") or 0) == 0, "no turns were spent"
    hops = [e for e in data["journal"] if e.get("who") == "state" and e.get("event") == "walk"]
    assert len(hops) >= 6, hops
    assert all(e.get("session") == "one-call" for e in hops[-6:]), hops[-6:]
