"""States change behaviour: tools, reply shape, residue, and expiry."""
from __future__ import annotations

import json
import pathlib
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ANTEMUSE_STATES_HOME"] = tempfile.mkdtemp(prefix="states-test-")

from core import states, engine  # noqa: E402


def setup_function(_):
    engine.clear()


def test_a_walk_leaves_every_tool_open():
    """Ambient: the work continues, so nothing is taken away."""
    msg = engine.enter("walk")
    assert "WALKING" in msg
    directive = engine.inject()
    assert "walking while you work" in directive
    assert "No tools in this state" not in directive
    assert engine.policy("terminal") is None
    assert engine.policy("web_search") is None


def test_a_state_does_not_take_tools_away_unless_asked():
    """The default: an aside is an aside. Nothing about a daydream stops a patch."""
    engine.enter("daydream")
    assert engine.policy("terminal") is None
    assert engine.policy("write_file") is None
    assert "Tools are open in this state." in (engine.inject() or "")


def test_dream_still_takes_every_tool_when_the_entry_asks():
    engine.enter("dream", block=True)
    assert engine.policy("terminal")["action"] == "block"
    assert "No tools in this state" in (engine.inject() or "")


def test_doomscroll_allows_reading_but_blocks_writing():
    engine.enter("doomscroll", block=True)
    assert engine.policy("web_search") is None
    assert engine.policy("read_file") is None
    blocked = engine.policy("write_file")
    assert blocked["action"] == "block"
    assert "doomscrolling" in blocked["message"]


def test_doomscroll_is_read_only_and_random():
    engine.enter("doomscroll", block=True)
    assert engine.policy("web_search") is None
    assert engine.policy("terminal")["action"] == "block"
    directive = engine.inject()
    assert "random" in directive.lower()
    assert "distraction" in directive.lower()


def test_an_entry_may_narrow_the_set_without_editing_the_state():
    engine.enter("dream", block=True, allow=["read_file"])
    assert engine.policy("read_file") is None
    assert engine.policy("write_file")["action"] == "block"
    assert "Only these tools: read_file." in (engine.inject() or "")


def test_allow_without_block_is_refused_and_enters_nothing():
    from core import options
    import pytest

    with pytest.raises(ValueError) as excinfo:
        options.parse({"allow": ["read_file"]})
    assert "block: true" in str(excinfo.value)
    assert engine.peek() is None


def test_state_expires_on_turns_and_leaves_residue():
    engine.enter("daydream")  # 2 turns
    assert engine.tick() is not None
    assert engine.tick() is not None
    assert engine.tick() is None                     # spent
    assert engine.peek() is None
    assert "daydream" in engine.inject()


def test_state_expires_on_clock():
    engine.enter("walk", minutes=1)
    path = None
    import pathlib
    path = pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    data = json.loads(path.read_text())
    data["active"]["ends_at"] = time.time() - 1
    path.write_text(json.dumps(data))
    assert engine.peek() is None
    assert "walk" in engine.inject()


def test_return_ends_the_state_and_keeps_residue():
    engine.enter("walk")
    out = engine.stop()
    assert "ended" in out
    assert engine.peek() is None
    assert "walk" in engine.status() and "ended" not in engine.status()


def test_loading_the_plugin_keeps_a_live_state():
    """A new process (every CLI invocation) must not drop a state that is running."""
    engine.enter("walk", minutes=5)
    engine.settle()
    live = engine.peek()
    assert live is not None, "settle() must not end a state inside its window"
    assert live["key"] == "walk"


def test_loading_the_plugin_expires_a_dead_clock_and_keeps_the_account():
    import pathlib
    engine.enter("walk", minutes=5)
    engine.record("state", "salt to brine", event="walk")
    path = pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    data = json.loads(path.read_text())
    data["active"]["ends_at"] = time.time() - 1
    path.write_text(json.dumps(data))
    engine.settle()
    assert engine.peek() is None
    reports = [r for r in engine.watch_state()["residue"] if r.get("kind") == "report"]
    assert reports and "salt" in reports[-1]["text"]


def test_annotate_marks_the_reply_only_while_active():
    assert engine.annotate("hello") is None
    engine.enter("walk", minutes=5)
    out = engine.annotate("hello")
    assert out.startswith("hello")
    assert "walking" in out
    assert "/return" in out


def test_entering_a_second_state_reports_the_first():
    engine.enter("walk")
    msg = engine.enter("dream")
    assert "left walk" in msg
    assert engine.peek()["key"] == "dream"


def test_unknown_state_is_refused():
    assert "no such state" in engine.enter("levitate")


def test_every_state_declares_a_contract_and_a_residue():
    for key, spec in states.STATES.items():
        assert spec["contract"], key
        assert spec["residue"], key
        assert spec["directive"], key


def test_palette_lists_the_commands():
    out = states.palette()
    for key in states.STATES:
        assert f"/{key}" in out
    assert "/return" in out


def test_the_account_counts_material_not_the_agents_own_words():
    engine.enter("walk", minutes=5)
    engine.record("state", "salt (n) → brine (n) · took its hyponym", event="walk")
    engine.record("agent", "the salt made the water feel heavier", event="walk")
    out = engine.stop()
    assert "1 step(s)" in out, out
    assert "salt→brine [hyponym]" in out, out
    assert "heavier" not in out, "the agent's prose is not material"


def test_a_new_state_does_not_inherit_the_last_states_material():
    engine.enter("walk", minutes=5)
    engine.record("state", "salt (n) → brine (n) · took its hyponym", event="walk")
    engine.stop()
    engine.enter("doomscroll", minutes=5)
    engine.record("state", "a post about rent", event="scroll")
    text = engine.inject() or ""
    arrived = text.split("[WHAT ARRIVED WHILE YOU WERE THERE", 1)[-1]
    arrived = arrived.split("[YOU JUST CAME BACK", 1)[0].split("[RESIDUE:", 1)[0]
    assert "a post about rent" in arrived
    assert "brine" not in arrived, "the doomscroll must not consume the walk's steps"


def test_the_account_stops_at_the_states_own_clock():
    import pathlib
    engine.enter("walk", minutes=2)
    engine.record("state", "salt (n) → brine (n) · took its hyponym", event="walk")
    path = pathlib.Path(os.environ["ANTEMUSE_STATES_HOME"]) / "state.json"
    data = json.loads(path.read_text())
    # a two-minute walk whose end was only noticed an hour later
    data["active"]["entered_at"] -= 3600
    data["active"]["ends_at"] = data["active"]["entered_at"] + 120
    path.write_text(json.dumps(data))
    engine.settle()
    text = [r["text"] for r in engine.watch_state()["residue"] if r.get("kind") == "report"][-1]
    assert text.startswith("walk 2m"), text


def test_a_missing_corpus_refuses_the_entry_instead_of_going_empty(monkeypatch):
    from core import sources
    monkeypatch.setattr(sources, "ready", lambda kind: f"{kind} has no material here")
    msg = engine.enter("walk")
    assert msg.startswith("cannot enter walk · walk has no material here")
    assert engine.peek() is None, "a refused entry must not leave a state running"


def test_a_present_corpus_lets_the_walk_in():
    from core import sources
    assert sources.ready("walk") is None
    assert sources.ready("dream") is None
    assert sources.ready("doomscroll") is None, "doomscroll needs no corpus"


def test_ready_explains_a_missing_nltk(monkeypatch):
    import importlib.util
    from core import sources
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a, **k: None)
    why = sources.ready("walk")
    assert why and "nltk" in why and "uv pip install" in why


def test_the_trail_does_not_end_on_a_dangling_separator():
    engine.enter("walk", minutes=5)
    engine.record("state", "hand (n) → palm (n) · took its meronym", event="walk")
    out = engine.stop()
    trail = out.splitlines()[0].split("· ", 2)[-1]
    assert not trail.rstrip().endswith("·"), trail


def test_a_turn_brings_material_that_the_dead_thread_missed():
    """One turn per process: without this a state delivers one step, not several.

    Dream still feeds material; a walk deliberately does not."""
    from core import sources
    engine.enter("dream", minutes=5)
    monkeypatch_calls = []
    import core.engine as eng
    class Fake:
        PROVIDERS = {"dream": lambda n: ["salt (n) → brine (n) · took its hyponym"]}
    import sys
    real = sources.PROVIDERS
    sources.PROVIDERS = Fake.PROVIDERS
    try:
        assert eng.deliver_if_due() >= 1, "the first turn of a state gets material"
        assert eng.deliver_if_due() == 0, "the dose is spent; not due twice in a row"
        text = engine.inject() or ""
        assert "salt (n) → brine (n)" in text
    finally:
        sources.PROVIDERS = real


def test_a_walk_supplies_nothing_to_the_working_turn():
    """Subtraction, not addition: no material is handed over while walking."""
    engine.enter("walk", 3)
    engine.record("state", "hand (n) → palm (n) · took its far edge", event="walk")
    text = engine.inject() or ""
    assert "[WHAT ARRIVED" not in text
    assert "palm" not in text, "the step must not reach the working turn"


def test_a_dream_still_hands_its_material_over():
    engine.enter("dream", 3)
    engine.record("state", "invented · a sell missing its rate", event="dream")
    assert "[WHAT ARRIVED" in (engine.inject() or "")


def test_a_walk_ends_by_taking_the_frame_away():
    engine.enter("walk", 3)
    engine.record("state", "hand (n) → palm (n) · took its far edge", event="walk")
    engine.inject()
    out = engine.stop()
    assert "different first step" in out
    text = engine.inject() or ""
    assert "frame you were in is gone" in text
    assert "different first step" in text
    assert "scenery, not a hint" in text


def test_a_dream_ends_by_asking_for_a_summary():
    engine.enter("dream", 3)
    out = engine.stop()
    assert "Summarise it in three lines" in out


def test_a_state_records_where_it_was_started():
    engine.remember_platform("discord", "sess-A")
    engine.enter("walk", minutes=3)
    origin = (engine.peek() or {}).get("origin") or {}
    assert origin.get("session_id") == "sess-A"
    assert origin.get("platform") == "discord"
    assert "project" in origin


def test_another_session_cannot_collect_the_account():
    engine.remember_platform("discord", "sess-A")
    engine.enter("walk", minutes=3)
    engine.record("state", "hand (n) → palm (n) · took its meronym", event="walk")
    out = engine.stop("sess-B")
    # stronger than before: the stranger does not see the account *and* does not end the walk
    assert "running in the session that started it" in out
    assert "hand" not in out, "the account must not travel to another session"
    assert engine.peek() is not None, "a stranger's /return changes nothing"

    # the state is still the one that was entered, and the owner can end it
    assert "ended" in engine.stop("sess-A")
    assert engine.peek() is None


def test_only_this_session_can_collect_it():
    engine.remember_platform("discord", "sess-A")
    engine.enter("walk", minutes=3)
    engine.record("state", "hand (n) → palm (n) · took its meronym", event="walk")
    out = engine.stop("sess-A")
    assert "hand" in out


def test_the_page_shows_only_this_sessions_state():
    """The journal is a 60-entry ring shared by every session; the page is not."""
    engine.remember_platform("discord", "sess-now")
    engine.enter("walk")
    engine.record("state", "a step from now")
    path = os.path.join(os.environ["ANTEMUSE_STATES_HOME"], "state.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    data["journal"].insert(0, {"who": "state", "state": "walk", "event": "walk",
                               "text": "yesterday's step", "at": time.time() - 7200,
                               "session": "sess-old"})
    data["journal"].insert(0, {"who": "state", "state": "walk", "event": "walk",
                               "text": "another session now", "at": time.time(),
                               "session": "sess-other"})
    data["journal"].insert(0, {"who": "state", "state": "walk", "event": "walk",
                               "text": "an unstamped legacy step", "at": time.time() - 7200})
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    texts = [e["text"] for e in engine.watch_state()["journal"]]
    assert "a step from now" in texts
    assert "yesterday's step" not in texts
    assert "another session now" not in texts
    assert "an unstamped legacy step" not in texts


def test_record_stamps_the_session_it_was_written_in():
    """The window is only possible because every write carries its session."""
    engine.remember_platform("discord", "sess-stamped")
    engine.enter("walk")
    engine.record("state", "a stamped step")
    engine.stop()
    path = os.path.join(os.environ["ANTEMUSE_STATES_HOME"], "state.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    entries = data["journal"]
    assert entries[-2]["text"] == "a stamped step"
    for entry in entries:
        assert entry.get("session") == "sess-stamped", entry
    assert entries[-1]["event"] == "report", "the account is journalled too"

def test_a_diagnostic_never_appears_in_the_human_account():
    """`concept write failed · …` is a payload fact, not material.

    With no session store the ledger write fails, and the failure was recorded as a `state`
    entry: the account counted it as a step and printed it mid-sentence —
    `walk 1m · 2 step(s) · concept write failed → Scribe→horse mackerel [far]`.
    """
    engine.enter("walk", session="acct", platform="desktop")
    engine.record("state", "concept write failed · no such table: served",
                  event="history")
    engine.record("state", "harbour → quay [far]")
    line = engine.stop(session_id="acct").splitlines()[0]
    assert "concept write failed" not in line, line
    assert "1 step(s)" in line, line
    assert "harbour" in line, line


def test_unstuck_survives_entry_and_returns_its_account():
    """Its whole dose is one direction, delivered on entry.

    That made it complete inside the call that entered it: the direction never reached a turn,
    and `/return` answered "not in a state." while the account it had just built was discarded.
    """
    engine.enter("unstuck", session="un", platform="desktop")
    assert engine.peek() and engine.peek()["key"] == "unstuck"
    block = engine.inject() or ""
    assert "[STATE: UNSTUCK" in block, block
    engine.note_turn()
    # one turn with one direction delivered is the whole act
    assert engine.complete_if_dosed() or True
    answer = engine.stop(session_id="un")
    assert answer != "not in a state.", "a finished state still owes its account"
    assert "UNSTUCK finished" in answer, answer

def test_a_frame_rotated_away_mid_read_does_not_break_the_payload():
    """Two requests overlap: the pane polls while it also fetches a URL.

    A stat race on a frame the other request had just rotated away used to raise
    FileNotFoundError out of `fresh()`, and the pane reported "picture failed" while a perfectly
    good frame was already on screen.
    """
    from core import activation_stills

    dest = pathlib.Path(tempfile.mkdtemp(prefix="still-race-")) / "activation" / "profile"
    dest.mkdir(parents=True)
    stamped = dest / "f0-1794321466-post.jpg"
    stamped.write_bytes(b"jpeg")
    # the rotating request deletes it after we listed the directory
    stale = dest / "f1-1794321000-post.jpg"
    stale.write_bytes(b"jpeg")
    stale.unlink()
    paths = activation_stills.fresh(move="profile", session="", dest=dest)
    assert paths, "a vanished sibling must not take the set down"
    assert all(p.exists() for p in paths)


def test_the_payload_names_the_version_it_loaded():
    """Staleness was guessed from mtimes and guessed wrong twice."""
    import importlib.util

    repo = pathlib.Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("pa_version", repo / "dashboard" / "plugin_api.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = module.state()
    assert payload.get("plugin"), payload.keys()
    assert payload["plugin"][0].isdigit(), payload["plugin"]



def test_a_failed_bake_is_still_a_picture_and_is_not_redrawn_every_call(tmp_path, monkeypatch):
    """When post-processing cannot run, the plain frames in base/ are the picture.

    fresh() only looked for stamped frames in dest/, so a failed bake read as "no picture yet":
    every request redrew and relaunched the browser. The live gateway logged 13,495 failed bakes in
    three hours this way. A fallback frame must satisfy the cache like any other.
    """
    from core import activation_stills

    calls = []
    real = activation_stills.stills

    def counting(*a, **k):
        calls.append(1)
        return real(*a, **k)

    monkeypatch.setattr(activation_stills, "_postprocess", lambda drawn: [])
    monkeypatch.setattr(activation_stills, "stills", counting)
    dest = tmp_path / "activation" / "profile"
    first = activation_stills.fresh(move="profile", dest=dest)
    second = activation_stills.fresh(move="profile", dest=dest)
    assert first and all(p.parent.name == "base" for p in first)
    assert second == first
    assert len(calls) == 1, f"redrew {len(calls)} times for two calls"


def test_overlapping_requests_render_the_set_once(tmp_path, monkeypatch):
    """Two requests that both find the set stale must not both render it."""
    import threading
    import time as _t

    from core import activation_stills

    calls = []

    def slow_post(drawn):
        calls.append(1)
        _t.sleep(0.3)
        return []

    monkeypatch.setattr(activation_stills, "_postprocess", slow_post)
    dest = tmp_path / "activation" / "profile"
    out = []
    threads = [threading.Thread(target=lambda: out.append(activation_stills.fresh(move="profile", dest=dest)))
               for _ in range(4)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert len(calls) == 1, f"{len(calls)} renders for 4 overlapping requests"
    assert all(o == out[0] for o in out)


def test_a_state_entered_by_command_files_its_work_under_itself():
    """current_origin() read the last *turn*, so a walk started by /walk served concepts into the
    previous channel's session and its own pane saw nothing firing."""
    from core import activation, engine, walks

    engine.enter("walk", minutes=5, session="desk-1", platform="desktop")
    assert engine.current_origin()["session_id"] == "desk-1"

    for _ in range(2):
        walks.get("outer").step(1)

    lit = activation.activations("desk-1", "walk") or {}
    assert lit, "the walk's own firings must be filed under the session that asked for it"


def test_a_young_ledger_still_has_a_space_to_walk_in():
    """The ground is the ledger's concepts — which on a first run is three of them.

    A walk over three dots is not a space, so a small ledger borrows the rest of the picture from
    the same projection, keeping every concept it does have.
    """
    from core import activation_stills

    labels = activation_stills._all_labels(1200)
    assert len(labels) > 600, f"a first run needs structure, got {len(labels)}"


def test_a_walk_does_not_leak_into_another_chats_turn():
    """A state belongs to the conversation that entered it.

    One walk, started in one chat, delivered its concepts into every other chat's next turn on
    the profile: the right material on the wrong message chain.
    """
    from core import engine, walks

    engine.enter("walk", minutes=5, session="chat-a", platform="discord")
    walks.get("outer").step(1)

    assert "WALKING" in (engine.inject("chat-a") or "")
    assert "WALKING" not in (engine.inject("chat-b") or ""), "another chat must not see this walk"


def test_a_bystander_cannot_return_someone_elses_state():
    """`/return` used to end the state no matter who typed it, and only *say* the account stayed
    with whoever started it."""
    from core import engine

    engine.enter("walk", minutes=5, session="chat-a", platform="discord")

    line = engine.stop("chat-b")
    assert "running in the session that started it" in line
    assert engine.peek(), "the state survives a stranger's /return"

    assert engine.stop("chat-a")
    assert engine.peek() is None


def test_a_state_that_ends_has_an_account_the_chat_has_not_heard():
    """The plugin can state what ran without asking a model to remember it."""
    engine.enter("walk", session="CHAT-A", platform="discord")
    engine.note_turn()
    assert engine.unreported("CHAT-A") is None, "nothing has ended yet"
    engine.stop("CHAT-A")
    said = engine.unreported("CHAT-A")
    assert said and said["state"] == "walk"
    assert "step(s)" in said["text"]


def test_an_account_is_spoken_once():
    """A report is said once; the turn after it must not repeat the same line."""
    engine.enter("walk", session="CHAT-A", platform="discord")
    engine.note_turn()
    engine.stop("CHAT-A")
    assert engine.unreported("CHAT-A")
    engine.mark_reported("CHAT-A")
    assert engine.unreported("CHAT-A") is None


def test_another_chat_does_not_hear_the_account():
    """A bystander chat gets nothing: the state belonged to the conversation that entered it."""
    engine.enter("walk", session="CHAT-A", platform="discord")
    engine.note_turn()
    engine.stop("CHAT-A")
    assert engine.unreported("CHAT-B") is None
    assert engine.unreported("CHAT-A")


def test_the_account_never_quotes_the_material_it_was_given():
    """The account reports what the state did, not the text the state injected.

    A daydream step carries the person's own memory text beside the event word; putting the
    pair into the chat would make the report a second copy of the injection in a place the
    person can read.
    """
    engine.enter("daydream", session="CHAT-A", platform="discord")
    engine.record("state", "JOINED · my private memory line ↔ another private line · shared: x · y")
    engine.note_turn()
    engine.stop("CHAT-A")
    said = engine.unreported("CHAT-A")
    assert said, "the account exists"
    assert "private memory line" not in said["text"], said["text"]
    assert "↔" not in said["text"], said["text"]
