"""A delivery is reserved before its provider runs, and committed only if it still holds.

The act calls the provider once per unit with the lock released, and the pane polls
`GET /state` while it does. Both doors read the same `served`, both passed the dose guard,
and both committed: six provider calls journalled seven distinct hops while the account
said "6 of 6". The paced path already claimed its turn before running the provider; the
instant path claimed nothing.
"""
import json
import os
import pytest
import pathlib
import threading


def test_a_poll_cannot_deliver_into_an_act_that_is_mid_flight(tmp_path, monkeypatch):
    from core import engine, sources

    engine.clear()
    monkeypatch.setattr(sources, "ready", lambda *a, **k: None)

    started = threading.Event()
    release = threading.Event()
    calls = []
    guard = threading.Lock()

    def provider(n=1, **kwargs):
        with guard:
            index = len(calls)
            calls.append(index)
        if index == 0:
            # Hold the first delivery open so the other door arrives mid-flight.
            started.set()
            release.wait(3)
        return [f"word{index}a (n) → word{index}b (n) · took its far edge"]

    monkeypatch.setitem(sources.PROVIDERS, "walk", provider)

    result = {}
    worker = threading.Thread(
        target=lambda: result.setdefault("out", engine.perform("walk", session="alice")))
    worker.start()
    assert started.wait(3), "the act never reached its first delivery"
    try:
        # The pane's door, arriving while the act holds a delivery open.
        engine.deliver_if_due(source="pane")
    finally:
        release.set()
        worker.join(6)

    data = json.loads((pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json").read_text())
    # The account line is also `who: state` and also contains arrows, so counting every
    # arrow-bearing state line reports seven for a six-hop walk that delivered exactly six.
    # Count the hops, not the report of them.
    hops = [str(e.get("text")) for e in data.get("journal", [])
            if e.get("who") == "state"
            and "→" in str(e.get("text") or "").split(" · ")[0]
            and not str(e.get("text") or "").startswith("walk ·")]
    assert len(calls) == 6, f"the dose bought {len(calls)} provider calls"
    assert len(hops) == 6, f"six provider calls journalled {len(hops)} hops: {hops}"
    assert len(set(hops)) == 6, f"a hop was delivered twice: {hops}"
    assert not data.get("active"), "the act left a state running"

def test_a_pick_with_no_session_cannot_land_in_someone_elses_explore():
    """The cockpit's picks are the owner's own choices, so an unnamed caller is not the owner.

    The guard read `if owner and session and session != owner`, which let an empty session
    through: the shipped pane posted `{picks: batch}` with no session at all, so the normal
    client path was the bypass. A named foreign session was correctly refused.
    """
    from core import engine

    engine.clear()
    engine.enter("explore", None, session="alice")
    refused = engine.note_pick(["injected"], session="")
    assert refused.get("ok") is False, refused
    assert not (engine.peek() or {}).get("picks"), "an unnamed caller wrote into alice's account"

    foreign = engine.note_pick(["injected"], session="bob")
    assert foreign.get("ok") is False, foreign

    mine = engine.note_pick(["router"], session="alice")
    assert mine.get("ok") is True, mine
    assert (engine.peek() or {}).get("picks") == {"router": 1}


def test_a_subagents_task_prompt_is_not_the_persons_own_message():
    """A delegated run's "user message" is its goal, not something the person said.

    The pre-LLM hook records whatever the host hands it as the turn's user text. For a
    subagent that text is the task prompt, so this plugin filed agent-to-agent instructions
    in the person's day record — and at a 24-row cap they evicted real messages.
    """
    import importlib
    from core import recall

    mod = importlib.import_module("__init__")

    goal = "Perform a rigorous code-quality review of a 4-commit diff"
    mod._pre_llm_call(platform="subagent", session_id="delegated-run", user_message=goal)
    assert goal not in " ".join(recall.recent(recall.CAP, who="person", session="delegated-run"))

    said = "I keep rewriting the same parser and it still fails"
    mod._pre_llm_call(platform="discord", session_id="real-chat", user_message=said)
    assert said in " ".join(recall.recent(recall.CAP, who="person", session="real-chat"))


def test_daydream_starts_when_the_chat_named_its_turns_by_another_id():
    """The host names one chat two ways, and the gate must recognise both.

    A local desktop turn is recorded under its session KEY (`local-<hex>`), while a slash
    command arrives with the stored session ID plus that key. The gate counted only the ID,
    found no turns, and refused `/daydream` in a chat that had said plenty — the state was
    unreachable in the app.
    """
    import importlib
    from core import engine, recall

    mod = importlib.import_module("__init__")
    engine.clear()
    key = "local-" + "c" * 56
    stored = "20261119_120000_abcdef"
    for text in ("the parser keeps failing on nested quotes",
                 "the coffee shop closed after twenty years",
                 "I want the walk to feel like wandering"):
        recall.remember(text, "person", key)

    handler = mod._enter("daydream")
    out = handler("", session_id=stored, session_key=key, platform="cli")
    assert "can't start" not in out, out
    assert (engine.peek() or {}).get("key") == "daydream", out


def test_an_unattributed_turn_is_not_every_chats_material():
    """A row with no session belongs to no chat, so no chat may read it as its own.

    New writes are stamped, but migrated, restored or partially written rows are not, and
    `recent()` deliberately included them — so one chat's private text became another chat's
    daydream material.
    """
    import json
    import os
    import pathlib
    from core import recall

    ring = pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "recent_turns.json"
    ring.write_text(json.dumps([
        {"who": "person", "text": "LEGACY compensation details should not cross chats",
         "at": 1.0, "session": ""},
        {"who": "person", "text": "mine: the parser keeps failing on nested quotes",
         "at": 2.0, "session": "bob"},
    ]))
    got = recall.recent(recall.CAP, who="person", session="bob")
    assert not any("LEGACY" in t for t in got), got
    assert any("parser" in t for t in got), got
    # A caller with no chat context still reads the whole ring.
    assert any("LEGACY" in t for t in recall.recent(recall.CAP, who="person", session=None))


def test_a_move_that_cannot_be_written_says_so(monkeypatch):
    """History is the audit trail; a write that vanishes without a word is not an audit trail.

    `mark_move` caught its own exception and returned None, so the caller that meant to note
    the failure never learned there was one.
    """
    from core import history

    class Broken:
        def __enter__(self):
            raise RuntimeError("disk is on fire")

        def __exit__(self, *a):
            return False

        def execute(self, *a, **k):
            raise RuntimeError("disk is on fire")

        def close(self):
            pass

    monkeypatch.setattr(history, "_connect", lambda: Broken())
    with pytest.raises(Exception):
        history.mark_move("walk", 1.0, 2.0, "completed", 6)
