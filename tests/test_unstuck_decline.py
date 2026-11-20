"""Two defects from a real /unstuck run: it could not decline, and it would not end itself."""


def test_unstuck_declines_when_the_slot_holds_a_pasted_command():
    """The template is fixed; only the two nouns change. A shell command in the 'try Y' slot
    produced "install the tarball a different way, write a test for it" - busywork."""
    from core import engine, recall, sources
    import unittest.mock as m
    engine.clear()
    recall.remember("what does daydream do", session="decline")
    recall.remember("tar -xzf antemuse-0.12.7.tar.gz\ncd antemuse-0.12.7\npython scripts\\install.py",
                    session="decline")
    with m.patch.object(sources, "_recent_work",
                        lambda s=None: ["what does daydream do",
                                        "tar -xzf antemuse-0.12.7.tar.gz\npython scripts\\install.py"]):
        out = sources.unstuck_text(1, session="decline")
    line = out[0] if isinstance(out[0], str) else out[0][1]
    assert "a different way" not in line, f"advised varying a shell command: {line}"
    assert "smallest test" not in line, f"proposed a test for an install paste: {line}"


def test_unstuck_still_suggests_when_both_slots_are_real_attempts():
    from core import engine, recall, sources
    engine.clear()
    recall.remember("I tried caching the parser results but it still stalls", session="ok")
    recall.remember("I rewrote the tokenizer and the stall got worse", session="ok")
    import unittest.mock as m
    with m.patch.object(sources, "_recent_work",
                        lambda s=None: ["I tried caching the parser results but it still stalls",
                                        "I rewrote the tokenizer and the stall got worse"]):
        out = sources.unstuck_text(1, session="ok")
    line = out[0] if isinstance(out[0], str) else out[0][1]
    assert "next move" in line, line


def test_a_one_move_state_ends_without_waiting_for_another_message():
    """The dose was fully served on entry, but _expire required turns >= 1, so the state sat
    open until the person spoke again."""
    from core import engine, recall
    engine.clear()
    for t in ("I tried caching the parser results but it still stalls",
              "I rewrote the tokenizer and the stall got worse",
              "the budget review moved to thursday"):
        recall.remember(t, session="selfend")
    engine.enter("unstuck", session="selfend")
    for _ in range(3):
        engine.deliver_if_due(source="pane")
    # watch_state() has no "key" field, so asserting on it passed no matter what the state did.
    # The document on disk is the authority.
    import json, os, pathlib
    doc = json.loads((pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json").read_text())
    assert doc.get("active") is None, f"the dose is delivered; the state should have ended: {doc.get('active')}"


def test_a_multi_dose_state_still_waits_for_the_person():
    """The guard on the self-end fix: closing a complete dose must not let a state finish itself
    in the background. The pane may only show what the person earned by talking."""
    from core import engine, recall
    import json, os, pathlib
    engine.clear()
    for t in ("the parser keeps failing on nested quotes",
              "the coffee shop closed after twenty years",
              "I want the walk to feel like wandering"):
        recall.remember(t, session="pace-guard")
    engine.enter("dream", session="pace-guard")
    for _ in range(12):
        engine.deliver_if_due(source="pane")
    doc = json.loads((pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json").read_text())
    active = doc.get("active") or {}
    assert active.get("key") == "dream", "a 2-link dose must not close with no turns taken"
    assert int(active.get("served") or 0) == 1, f"the pane served ahead of the person: {active}"
