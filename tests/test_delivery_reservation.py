"""A delivery is reserved before its provider runs, and committed only if it still holds.

The act calls the provider once per unit with the lock released, and the pane polls
`GET /state` while it does. Both doors read the same `served`, both passed the dose guard,
and both committed: six provider calls journalled seven distinct hops while the account
said "6 of 6". The paced path already claimed its turn before running the provider; the
instant path claimed nothing.
"""
import json
import os
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
