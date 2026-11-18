"""Walk dose delivery: delivered material, ownership, endings, and accounts."""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="delivery-test-")

from core import engine, sources, states  # noqa: E402


def setup_function(_):
    engine.clear()


def provider(*lines):
    queue = list(lines)

    def call(_n):
        return [queue.pop(0)] if queue else []

    return call


def drive(*lines, turns=8, session="delivery"):
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(*lines)
    try:
        engine.enter("walk", session=session)
        blocks = []
        for _ in range(turns):
            engine.note_turn(session)
            engine.tick(session)
            blocks.append(engine.inject(session) or "")
            if engine.peek() is None:
                break
        return blocks
    finally:
        sources.PROVIDERS["walk"] = original


def state_home() -> dict:
    with open(os.path.join(os.environ["ANTEMUSE_STATES_HOME"], "state.json")) as fh:
        return json.load(fh)


def markers(n=6):
    return [f"WALK-MARKER-{i}" for i in range(1, n + 1)]


def test_the_last_unit_reaches_the_turn_that_spends_it():
    lines = markers()
    drive(*lines)
    journal = [e["text"] for e in state_home()["journal"] if e.get("who") == "state"]
    assert journal[:6] == lines
    assert engine.peek() is None


def test_a_state_ends_with_exactly_one_account():
    drive(*markers())
    reports = [r for r in state_home()["residue"] if r.get("kind") == "report"]
    assert len(reports) == 1
    assert reports[0]["state"] == "walk"
    assert reports[0]["reason"] == "complete"


def test_a_dead_source_ends_as_failed_and_claims_no_dose():
    blocks = drive("feed unavailable · nothing to read")
    joined = "\n".join(blocks)
    assert "nothing arrived" in joined
    assert "1 of 6 hops" not in joined
    assert "[WHAT ARRIVED" not in joined
    report = [r for r in state_home()["residue"] if r.get("kind") == "report"][0]
    assert report["reason"] == "failed"
    assert "nothing arrived" in report["text"]


def test_a_source_that_runs_dry_mid_dose_is_not_called_nothing_arrived():
    drive("WALK-MARKER-1", "WALK-MARKER-2")
    report = [r for r in state_home()["residue"] if r.get("kind") == "report"][0]
    assert report["reason"] == "dry"
    assert "2 of 6 hops" in report["text"]
    assert "nothing arrived" not in report["text"]


def test_a_pane_poll_cannot_spend_a_state():
    lines = markers()
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(*lines)
    try:
        engine.enter("walk", session="pane")
        engine.note_turn("pane")
        engine.tick("pane")
        for _ in range(8):
            engine.deliver_if_due(source="pane")
        active = engine.peek()
        assert active is not None
        # Eight polls inside one turn buy nothing: the entry hop is the only unit that turn earned.
        # The pane used to take a second one here, and the desktop app showed `2/6 HOPS` before the
        # person had typed anything.
        assert active["served"] == 1
        engine.inject("pane")
        assert engine.peek() is not None
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_turn_from_another_session_does_not_spend_the_dose():
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider("a → b", "b → c")
    try:
        engine.enter("walk", session="A")
        engine.note_turn("A")
        engine.inject("A")
        assert engine._load()["active"]["served"] == 1
        engine.note_turn("B")
        engine.tick("B")
        assert engine.inject("B") is None
        active = engine._load()["active"]
        assert active["served"] == 1
        assert active["turns"] == 1
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_repeated_line_ends_dry_and_does_not_claim_nothing_arrived():
    line = "WALK-MARKER"
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(line, line, line)
    try:
        engine.enter("walk", session="repeat")
        engine.note_turn("repeat")
        engine.inject("repeat")
        engine.note_turn("repeat")
        engine.deliver_if_due()
        engine.note_turn("repeat")
        engine.deliver_if_due()
        assert engine.peek() is None
        report = [r for r in state_home()["residue"] if r.get("kind") == "report"][0]
        assert report["reason"] == "dry"
        assert "nothing arrived" not in report["text"]
        assert "nothing new arrived" in report["text"]
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_repeated_line_is_not_new_material():
    line = "WALK-MARKER"
    drive(line, line, line)
    report = [r for r in state_home()["residue"] if r.get("kind") == "report"][0]
    assert report["reason"] == "dry"
    assert "1 of 6 hops" in report["text"]
    assert "6 of 6 hops" not in report["text"]


def test_a_walk_still_withholds_its_material():
    blocks = drive(*markers())
    assert all("[WHAT ARRIVED" not in block for block in blocks)


def test_an_open_ended_explore_never_completes():
    engine.enter("explore", session="pane")
    for _ in range(4):
        engine.note_turn("pane")
        engine.tick("pane")
        engine.deliver_if_due()
    assert engine.peek()["key"] == "explore"


def test_a_provider_failure_line_is_not_material():
    assert engine._is_failure_line("feed unavailable · timed out")


def test_walk_dose_is_six_hops():
    assert states.STATES["walk"]["dose"] == {"unit": "hops", "n": 6}


def test_an_abandoned_walk_waits_for_its_owner_instead_of_being_spent_for_them():
    """Entered in A, one hop served, then A stops talking.

    This used to be a stuck state: a pane poll could serve the whole dose, `seen` never caught
    up (only A's block can advance it), and the state hung at "0 left" until a turn from another
    conversation forced it closed. Delivery is one unit per turn now, and a turn belongs to one
    conversation, so the dose cannot be spent behind the owner's back — the state simply waits,
    and every other conversation gets no annotation from it.
    """
    lines = markers()
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(*lines)
    try:
        engine.enter("walk", session="A")
        engine.note_turn("A")
        engine.inject("A")
        active = engine._load()["active"]
        assert active["served"] == 1, active

        # The pane looks as many times as it likes: a look is not a turn.
        for _ in range(10):
            engine.deliver_if_due(source="pane")
            engine.tick(None)
        assert engine._load()["active"]["served"] == 1, "a poll may show what a turn earned, no more"

        # Another conversation walks in and gets nothing of A's state.
        engine.note_turn("B")
        assert engine.inject("B") is None
        assert engine.peek() is not None, "an unfinished walk waits for the conversation that owns it"
        assert "WALKING" not in (engine._load().get("active") or {}).get("key", "")

        # A's next turn carries on where it left off.
        engine.note_turn("A")
        block = engine.inject("A") or ""
        assert "WALKING" in block
        assert engine._load()["active"]["served"] == 2
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_foreign_turn_does_not_close_a_state_that_still_has_units_to_serve():
    """The escape hatch is for an unshown dose, not for any state someone else walks in on."""
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(*markers())
    try:
        engine.enter("walk", session="A")
        engine.note_turn("A")
        engine.tick("A")
        engine.inject("A")
        assert engine._load()["active"]["served"] < engine._load()["active"]["dose"]

        engine.note_turn("B")
        engine.inject("B")
        assert engine.peek() is not None, "an unfinished state was closed by a stranger"
    finally:
        sources.PROVIDERS["walk"] = original


def test_a_walk_cannot_serve_past_its_dose():
    """Seven hops on a six-hop walk made the account print "6 of 6 hops" over seven lines."""
    lines = markers(12)
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(*lines)
    try:
        engine.enter("walk", session="dose")
        for _ in range(14):
            engine.note_turn("dose")
            engine.tick("dose")
            engine.inject("dose")
            engine.deliver_if_due(source="pane")
            if engine.peek() is None:
                break
    finally:
        sources.PROVIDERS["walk"] = original

    active = state_home().get("active") or {}
    if active:
        assert active["served"] <= active["dose"], active


def test_the_account_counts_the_trail_it_prints():
    """"6 of 6 hops" followed by seven hops is one statement disagreeing with itself."""
    engine.enter("walk", session="count")
    engine.note_turn("count")
    with open(os.path.join(os.environ["ANTEMUSE_STATES_HOME"], "state.json")) as fh:
        data = json.load(fh)
    data["active"]["served"] = 7          # what an overspending build left behind
    data["journal"].extend(
        {"who": "state", "state": "walk", "event": "walk", "at": 9e9 + i,
         "text": f"a{i} (n) → b{i} (n) · took its far edge"} for i in range(7))
    with open(os.path.join(os.environ["ANTEMUSE_STATES_HOME"], "state.json"), "w") as fh:
        json.dump(data, fh)

    account = engine._account(data, data["active"])

    assert "6 of 6 hops" in account["text"], account["text"]
    assert account["text"].count("[far]") == 6, account["text"]


def test_serving_stops_at_the_dose_even_when_a_provider_returns_a_batch():
    engine.enter("walk", session="batch")
    with open(os.path.join(os.environ["ANTEMUSE_STATES_HOME"], "state.json")) as fh:
        data = json.load(fh)
    data["active"]["served"] = data["active"]["dose"] - 1
    with open(os.path.join(os.environ["ANTEMUSE_STATES_HOME"], "state.json"), "w") as fh:
        json.dump(data, fh)

    served = engine._spend(data["active"], 4)

    assert served == data["active"]["dose"], (served, data["active"]["dose"])


def test_the_turn_that_spends_the_last_hop_carries_the_ending():
    """A walk must say it is over in the turn it ends in.

    The block used to be built while the state was still open and the close ran afterwards, so
    the last turn printed "6 of 6 hops" with the walk's own directive still attached — reading
    as a walk still in progress — and `WALKING ended · …` only appeared if the person typed
    again. Reported from a live chat: the walk never said it was done.
    """
    lines = markers()
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(*lines)
    try:
        engine.enter("walk", session="ending")
        blocks = []
        for _ in range(6):
            engine.note_turn("ending")
            blocks.append(engine.inject("ending") or "")
    finally:
        sources.PROVIDERS["walk"] = original

    last = blocks[-1]
    assert "6 of 6 hops" in last, last
    assert "this is the last one" in last, last
    assert "YOU JUST CAME BACK" in last, "the ending must arrive with the last hop, not a turn later"
    assert engine.peek() is None, "the state was still open after its last hop"

    # The account is not announced twice to the person: one residue report, marked told when
    # the host posted it. (The block may repeat it for a turn or two so a busy turn can still
    # react — that is the model's copy, not a second announcement.)
    reports = [r for r in engine._load()["residue"] if r.get("kind") == "report"]
    assert len(reports) == 1, reports


def test_the_reply_that_follows_a_finish_says_it_ended():
    """The ending rides on the answer, once.

    The host poster is not a display guarantee: in a live chat it accepted `WALKING ended · …`
    and marked the account told while nothing appeared. `transform_llm_output` is the channel
    that cannot be swallowed, so the reply that follows a finish carries the line — and only
    that one reply, not every reply in the residue window.
    """
    lines = markers()
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(*lines)
    try:
        engine.enter("walk", session="annot")
        for _ in range(6):
            engine.note_turn("annot")
            engine.inject("annot")
    finally:
        sources.PROVIDERS["walk"] = original

    first = engine.annotate("here is my answer") or ""
    assert "here is my answer" in first, "the answer must not be rewritten"
    assert "walking ended · walk · 6 of 6 hops" in first, first

    second = engine.annotate("another answer")
    assert second is None, "the ending is said once, not on every reply after it"


def test_a_delivery_that_arrives_after_the_state_ended_writes_nothing():
    """A walk that died kept spending its dose into the ledger with `active: None`.

    The provider ran while the state was alive; by the time it answered the state was gone, and
    the function still wrote a serving row for every term and every hop — fifty-three rows and
    twelve hops after one dead walk — then saved `data["active"] = {}`, because `active` had
    become the empty dict it invented from None. That `{}` is the shape the validator rejected,
    which quarantined the whole document.
    """
    import json
    from pathlib import Path

    from core import history

    before = len([r for r in history.recent(days=1, limit=400) if r.get("move") == "walk"])
    entered = engine.enter("walk", session="late")
    assert "WALKING" in entered
    key = engine.peek()["key"]

    def provider(_n):
        engine.stop("late", reason="failed")      # the state ends mid-call
        return ["late hop → landing"]

    original = sources.PROVIDERS[key]
    sources.PROVIDERS[key] = provider
    try:
        assert engine.deliver_if_due() == 0, "material nobody asked for is not served"
    finally:
        sources.PROVIDERS[key] = original

    after = len([r for r in history.recent(days=1, limit=400) if r.get("move") == "walk"])
    assert after == before, "a dead state must not write serving rows"
    stored = engine.watch_state()
    assert stored["active"] is None
    assert not list((Path(os.environ["ANTEMUSE_STATES_HOME"])).glob("state.json.invalid-*"))
    assert "active" in json.loads((Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json").read_text())


def test_a_walk_that_died_names_what_killed_it():
    """The person read "walk produced nothing" while the journal held the exception.

    The account is the only place a person looks, and it dropped the cause: a state that died of
    a named failure reported that nothing arrived, which is true and useless.
    """
    def dead(_n=None, **_kw):
        raise RuntimeError("WordNet data is unavailable · seek of closed file")

    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = dead
    try:
        engine.enter("walk", session="died")
        for _ in range(2):
            engine.note_turn("died")      # a turn earns one attempt; two failures need two turns
            engine.deliver_if_due(source="turn")
    finally:
        sources.PROVIDERS["walk"] = original

    state = engine.watch_state()
    assert state["active"] is None, "two empty deliveries end the state"
    text = [r.get("text") for r in state["residue"] if r.get("kind") == "report"][-1]
    assert "nothing arrived" in text
    assert "RuntimeError" in text and "seek of closed file" in text, text


def test_a_reply_that_already_ends_with_the_footer_gets_one_not_two():
    """The footer is this plugin's line, so it is added once.

    Observed in a real chat (0.11.28, move 121): the model's reply already ended with
    "— walking · 1 hop left · /return to come back" because the shape echoes through the
    conversation, and `annotate()` appended a second copy. The journal recorded the hop text twice
    before the plugin added a third.
    """
    engine.enter("walk", session="footer")
    engine.note_turn("footer")
    engine.deliver_if_due()
    footer = "— walking · 5 hops left · /return to come back"

    once = engine.annotate(f"An answer.\n\n{footer}")
    assert once.count(footer) == 1, once
    twice = engine.annotate(f"An answer.\n\n{footer}\n\n{footer}")
    assert twice.count(footer) == 1, twice
    assert twice.startswith("An answer."), twice


def test_a_dash_line_in_the_middle_of_a_reply_is_prose_not_a_footer():
    engine.enter("walk", session="footer2")
    engine.note_turn("footer2")
    engine.deliver_if_due()
    body = "Two things:\n\n— one: the wall stops the ship\n— two: the pane polls /state"
    out = engine.annotate(body) or ""
    assert "— one: the wall stops the ship" in out, out
    assert "— two: the pane polls /state" in out, out


def test_a_repeat_and_a_poll_in_one_turn_dont_end_the_walk(tmp_path):
    """One turn's repeat is one repeat, even when the pane also looked.

    The desktop app closed a walk `dry` at 2 of 6 in one turn: the turn delivered a repeat, the
    pane poll delivered the same repeat again, and two repeats with a served count ended the
    state claiming "nothing new arrived". A repeat must be counted against the turn that saw it,
    so a second door in that turn cannot count it twice.
    """
    engine, sources = _engine(tmp_path) if "_engine" in globals() else (None, None)
    if engine is None:
        import importlib
        engine = importlib.import_module("core.engine")
        sources = importlib.import_module("core.sources")

    line = "WALK-MARKER"
    original = sources.PROVIDERS["walk"]
    sources.PROVIDERS["walk"] = provider(line, line, line, line)
    try:
        engine.enter("walk", session="repeat-poll")
        engine.note_turn("repeat-poll")
        engine.inject("repeat-poll")          # first hop
        engine.note_turn("repeat-poll")
        engine.inject("repeat-poll")          # repeat
        assert engine.deliver_if_due(source="pane") == 0, "the poll bought nothing"
        active = engine.peek()
        assert active is not None, "one repeat in one turn is not drained material"
        engine.note_turn("repeat-poll")
        engine.deliver_if_due()               # the second turn's repeat is what ends it
        assert engine.peek() is None
    finally:
        sources.PROVIDERS["walk"] = original


def test_six_doors_arriving_together_buy_one_hop(tmp_path):
    """The turn must be claimed before the provider runs, not after it answers.

    The provider is called outside the lock. Two doors arriving together both read the old cursor,
    both passed the guard, and both served: the app showed two hops in the same second and a walk
    two hops spent before anyone spoke. Claiming the turn inside the lock makes the second door wait
    for a turn of its own.
    """
    import threading
    engine.enter("walk", session="together")
    got = []

    def knock():
        got.append(engine.deliver_if_due(source="pane"))

    threads = [threading.Thread(target=knock) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(got) == 1, got
    assert (engine.peek() or {}).get("served") == 1
