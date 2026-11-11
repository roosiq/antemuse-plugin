"""One active state per profile, with whatever residue it left behind.

Profile-wide rather than per-session: the metaphor is about the agent, not about
a chat window, and a slash command has no session id to hang it on.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Any, Dict, List

from . import history, states, storage

FILE = "state.json"

# "hand (n) → metacarpal vein (n) · took its meronym · “dorsal and palmar veins”"
STEP_RE = re.compile(
    r"^(?P<a>[^()]+?) \(\w+\) → (?P<b>[^()]+?) \(\w+\) · took its (?P<rel>[a-z_]+)")
_LOCK = threading.Lock()


def _blank() -> Dict[str, Any]:
    return {
        "active": None, "residue": [], "journal": [],
        "mood": [], "breaks": [], "offered_at": 0.0,
        "work": {"turns": 0, "tools": 0, "fails": 0, "started_at": time.time()},
    }


def _load() -> Dict[str, Any]:
    path = storage.data_dir() / FILE
    data = _blank()
    if not path.exists():
        return data
    try:
        stored = json.loads(path.read_text())
    except Exception:
        return data
    data.update(stored)
    return data


def _save(data: Dict[str, Any]) -> None:
    path = storage.data_dir() / FILE
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


DIAGNOSTIC_EVENTS = ("history", "failure", "error")


def _account(data: Dict[str, Any], active: Dict[str, Any]) -> Dict[str, Any]:
    """What happened while the agent was away, in one line it can speak from.

    The plugin knows the facts — how long, how many steps, which material
    arrived. It does not know what the walk meant; that is the agent's to say.
    """
    key = active["key"]
    started = active.get("entered_at", 0) or 0
    events = [
        e for e in data.get("journal", [])
        if e.get("state") == key and e.get("at", 0) >= started and e.get("text")
        # A diagnostic is not material. `history` records "concept write failed · …" when the
        # store is missing or unwritable; counting it as a step both inflated the step count and
        # printed an internal failure inline in the human account ("walk 1m · 2 step(s) ·
        # concept write failed → Scribe→horse mackerel"). The failure belongs in the payload and
        # the journal, not mid-sentence in the line a person reads.
        and e.get("event") not in DIAGNOSTIC_EVENTS
    ]
    # the account is the material the state delivered, not the agent's own prose:
    # counting replies as "steps" made a five-step walk report ten.
    steps = [e for e in events if e.get("who") == "state"]
    # the clock stops when the state ends, not when someone notices it ended
    ended = min(time.time(), active.get("ends_at") or time.time())
    mins = max(1, int(round((ended - started) / 60)))
    trail: List[str] = []
    for e in steps:
        text = str(e.get("text") or "")
        step = STEP_RE.match(text)
        if step:
            head = f"{step.group('a')}→{step.group('b')} [{step.group('rel')}]"
        else:
            # The event word only — never the material beside it. A daydream step reads
            # "JOINED · <memory A> ↔ <memory B> · shared: … · possibility", and quoting the pair
            # put the person's own memory text into the chat: the account is a report of what the
            # state did, not a second copy of the injection. The walk's steps are safe because
            # they are WordNet concepts; everything else carries user material, so it is counted,
            # not quoted.
            parts = [x.strip() for x in text.split(" · ") if x.strip()]
            head = (parts[0] if parts else "")[:40].rstrip(",.;:· ")
        if head and head not in trail:
            trail.append(head)
    body = " → ".join(trail[:5]) if trail else "nothing arrived"
    # A bare event word ("JOINED") says a thing happened but not how much of it; the tally is the
    # part of the account that is safe to state.
    for mark in ("JOINED", "adjacent"):
        n = sum(1 for e in steps if str(e.get("text") or "").startswith(mark))
        if n:
            body = f"{body} · {mark.lower()} ×{n}"
    return {
        "state": key,
        "text": f"{key} {mins}m · {len(steps)} step(s) · {body[:180]}",
        "steps": len(steps),
    }


def _record_finish(active: Dict[str, Any], ending: str, served: int | None = None) -> None:
    """Write the one `moves` row a finished state leaves.

    `mark_move` existed with no caller for a release; it was then wired into `stop()` only. A
    state that ended by expiry — time-out or dose-exhausted, which is the common ending — still
    left nothing, so `moves` stayed empty and looked like the writer was broken. Both endings go
    through here now.
    """
    try:
        from . import history
        history.mark_move(str(active.get("key") or ""),
                          float(active.get("started") or 0), time.time(), ending,
                          int(served if served is not None else (active.get("served") or 0)))
    except Exception as exc:
        try:
            from . import history
            history._note_failure(f"move not recorded · {type(exc).__name__}: "
                                  f"{str(exc).splitlines()[0][:70]}")
        except Exception:
            pass


def _expire(data: Dict[str, Any], now: float | None = None) -> bool:
    active = data.get("active")
    if not active:
        return False
    now = now if now is not None else time.time()
    if active["turns_left"] <= 0 or now >= active["ends_at"]:
        report = _account(data, active)
        spec = states.STATES.get(active.get("key")) or {}
        dose, _unit2 = _dose_of(spec, active)
        served = int(active.get("served") or 0) if _unit2 != "turns" \
            else int(active.get("turns") or 0)
        if dose and served < dose:
            # an expiry is an unfinished act, and it says so
            report = {**report, "text": f"{report['text']} (expired before its dose: {served} of {dose})"}
        data["residue"].append({**report, "kind": "report", "turns_left": 2,
                                "session": (active.get("origin") or {}).get("session_id") or ""})
        data.setdefault("journal", []).append({
            "who": "state", "state": active["key"], "event": "report",
            "text": report["text"], "at": now,
            "session": data.get("session_id") or "",
        })
        try:
            from . import settings
            cap = settings.number("journal_cap")
        except Exception:
            cap = 60
        data["journal"] = data["journal"][-cap:]
        data["active"] = None
        # the expiry must reach disk: the caller holds a copy, and an unsaved expiry
        # means the state silently outlives its ceiling
        _save(data)
        _record_finish(active, "expired", served)
        return True
    return False


def note_turn() -> None:
    """Called at the top of every turn: count it, and bank the tool counters."""
    from . import mood
    counters = mood.take_counters()
    with _LOCK:
        data = _load()
        work = data["work"]
        work["turns"] = int(work.get("turns") or 0) + 1
        work["tools"] = int(work.get("tools") or 0) + counters["tools"]
        work["fails"] = int(work.get("fails") or 0) + counters["fails"]
        active = bool(data.get("active"))
        if data.get("active"):
            data["active"]["turns"] = int(data["active"].get("turns") or 0) + 1
        _save(data)
    # The baseline is the *ordinary* condition: a state's own turns would contaminate
    # the thing the state is being compared to.
    if not active:
        from . import normal
        normal.observe_turn(counters["tools"], counters["fails"])
    else:
        complete_if_dosed()


def note_tool(ok: bool) -> None:
    """post_tool_call: the only honest signal about how the work is going.

    Counts twice on purpose: the mood counters hold the totals used for strain, and
    `work` holds the *shape* — the run of failures, and which turn each one fell on,
    because "same tool failed three times" is not the same thing as "three failures".
    """
    from . import mood
    mood.observe_tool(ok)
    with _LOCK:
        data = _load()
        work = data.setdefault("work", {})
        if ok:
            work["streak"] = 0
        else:
            work["streak"] = int(work.get("streak") or 0) + 1
            turns = int(work.get("turns") or 0)
            recent = [int(x) for x in (work.get("fail_turns") or [])][-7:] + [turns]
            work["fail_turns"] = recent
        _save(data)


def break_view() -> Dict[str, Any]:
    from . import mood
    with _LOCK:
        data = _load()
        return mood.view(data["work"], data["mood"], data["breaks"], data.get("offered_at") or 0.0)


def record_mood(feeling: str, note: str = "") -> str:
    """The agent or the person says how it is; a report, not an inference."""
    from . import mood
    feeling = str(feeling or "").strip().lower()
    if feeling not in mood.FEELINGS:
        return f"no such feeling. try: {', '.join(mood.FEELINGS)}"
    with _LOCK:
        data = _load()
        data["mood"].append({"at": time.time(), "feeling": feeling, "note": (note or "").strip()[:200]})
        data["mood"] = data["mood"][-20:]
        _save(data)
    return f"mood: {feeling}" + (f" · {note.strip()[:120]}" if note.strip() else "")


def data_for_advice() -> dict:
    """The stored record, for a reader that needs counters and entries together."""
    with _LOCK:
        return _load()


def take_break(choice: str | None = None) -> str:
    """Enter the state the agent asks for, or recommend one."""
    from . import mood
    view = break_view()
    wanted = (choice or "").strip().lower()
    if wanted:
        if wanted not in states.STATES:
            return f"no such state. try: {', '.join(states.STATES)}"
        return enter(wanted)
    advice = recommend_line = None
    from . import recommend
    advice = recommend.suggest({**data_for_advice(), "minutes": view["minutes"],
                                "feeling": view["feeling"]})
    recommend_line = advice["line"] if advice else "nothing measured yet that names a state"
    return mood.line(view) + "\n" + recommend_line + "\n" + states.palette()


def settle() -> None:
    """On load: expire a state whose clock ran out, leave a live one alone.

    Registration happens in every new process, so this cannot be a turn
    (that would spend a turn per CLI invocation) and must not be a clear
    (that would drop a state the person is still inside, and its residue).
    """
    with _LOCK:
        data = _load()
        if _expire(data):
            _save(data)


def enter(key: str, minutes: int | None = None, walk: str | None = None,
          options: Dict[str, Any] | None = None, block: bool = False,
          allow: List[str] | None = None, dose: int | None = None,
          session: str | None = None, platform: str | None = None) -> str:
    spec_key = states.resolve(key)
    if not spec_key:
        return f"no such state. try: {', '.join(states.STATES)}"
    from . import sources
    why_not = sources.ready(spec_key)
    if why_not:
        return f"cannot enter {spec_key} · {why_not}"
    spec = states.STATES[spec_key]
    # Convenience kwargs for the two policy arguments, so an entry can be closed
    # without building an options dict by hand. They are recorded in the same place
    # the tool handler records them, and nowhere else.
    if block or allow:
        options = dict(options or {})
        options["block"] = bool(block)
        if allow:
            options["allow"] = list(allow)
    with _LOCK:
        data = _load()
        previous = data.get("active") or {}
        now = time.time()
        root = storage.project_root()
        # A command is not a message: on a slash command no turn arrived to remember where it
        # came from, so the caller's own session and surface win over the last remembered ones.
        # Without this a walk entered from the desktop is filed under the channel that spoke
        # last — the pane then asks about its own chat and is correctly told the state is
        # somebody else's.
        origin = {
            "session_id": session or data.get("session_id") or "",
            "platform": platform or data.get("platform") or "",
            "project": str(root) if root else "",
        }
        duration = float(minutes if minutes else spec["minutes"])
        data["active"] = {
            "key": spec_key,
            "origin": origin,
            "walk": walk or (previous.get("walk") if previous and previous["key"] == spec_key else "outer"),
            "entered_at": now,
            "ends_at": now + duration * 60,
            "turns_left": spec["turns"],
            # the dose, and the unit it is counted in: "turns" was a lie for walk (hops),
            # daydream (pairs) and the rest, and the pane printed it
            "dose": int(spec["turns"]),
            "unit": (spec.get("dose") or {}).get("unit") or "turn(s)",
            "minutes": duration,
            "total_seconds": duration * 60,
            # an experiment arm may run a dose the manifest does not declare; the key is
            # written only when the runner asked for it, so nothing else can inherit it
            **({"dose_override": int(dose)}
               if dose and os.environ.get("ANTEMUSE_EXPERIMENT") == "1" else {}),
        }
        # Recorded, never acted on here: the exploration run that consumes these
        # is a separate wiring step. An entry without options has no key at all,
        # so today's record shape is unchanged.
        if options:
            data["active"]["options"] = dict(options)
        now_break = now
        # The gap is measured to the break before THIS one. Reading breaks[-1] after the append
        # measured the break against itself: the delta was always 0.0, observe_stretch dropped
        # every sample at its `<= 0` floor, and the footer said "no baseline yet" forever.
        before = list(data.get("breaks") or [])
        last = float(before[-1]) if before else float(
            data.get("work", {}).get("started_at") or now)
        gap = (now - last) / 60.0
        data.setdefault("breaks", []).append(now_break)
        if not previous:
            from . import normal
            normal.observe_stretch(gap)
        entries = [e for e in (data.get("entries") or []) if isinstance(e, dict)][-7:]
        entries.append({"key": spec_key, "at": now_break})
        data["entries"] = entries
        data["work"] = {"turns": 0, "tools": 0, "fails": 0, "started_at": now_break}
        data["offered_at"] = 0.0
        _save(data)
    # no ticker: delivery is per turn now, so a wall clock cannot decide the dose
    note = ""
    if previous and previous["key"] != spec_key:
        note = f" (left {previous['key']}; no residue kept)"
    return (f"{spec['label']} · {duration:g} min · {spec['turns']} "
            f"{(spec.get('dose') or {}).get('unit') or 'turn(s)'} · {spec['contract']}{note}")


def current_session() -> str:
    """The session the last turn came from: what `stop()` holds the account to."""
    with _LOCK:
        return str(_load().get("session_id") or "")


def current_origin() -> Dict[str, str]:
    """Where the last turn came from: session, channel, and project.

    Prepared material is bound to this, so a run started in one project cannot
    arrive in another. Missing pieces stay empty rather than being guessed.
    """
    with _LOCK:
        data = _load()
    root = storage.project_root()
    # While a state is running, where *it* was entered from is where its work belongs. Reading
    # only the remembered last turn meant a walk started by a command filed every concept it
    # served under the previous channel's session, and its own pane then saw nothing firing.
    active = data.get("active") or {}
    origin = (active.get("origin") or {}) if isinstance(active, dict) else {}
    return {
        "session_id": str(origin.get("session_id") or data.get("session_id") or ""),
        "platform": str(origin.get("platform") or data.get("platform") or ""),
        "project": str(root) if root else "",
    }


def stop(session_id: str = "", reason: str = "returned") -> str:
    with _LOCK:
        data = _load()
        active = data.get("active")
        if not active:
            # A state that completed on its own is still worth answering: `/return` used to say
            # "not in a state." because the dose had already ended it, throwing away the account
            # the plugin had just built. A fresh residue report is that account.
            for entry in reversed(data.get("residue") or []):
                if entry.get("kind") == "report" and int(entry.get("turns_left") or 0) > 0:
                    label = (states.STATES.get(entry.get("state")) or {}).get("label") or "state"
                    return (f"{label} finished · {entry.get('text', '')}\n"
                            f"The act is done, so the state is over. Carry what it gave you "
                            f"into the work.")
            return "not in a state."
        spec = states.STATES[active["key"]]
        origin = active.get("origin") or {}
        elsewhere = bool(session_id and origin.get("session_id")
                         and session_id != origin.get("session_id"))
        if elsewhere:
            # Typing /return in a chat that is not running the state used to end it anyway and
            # only *say* the account stayed elsewhere: a bystander could stop somebody else's
            # walk. Now the state is untouched and the answer says where it lives.
            return (f"{spec['label']} is running in the session that started it. Nothing was "
                    f"ended here — /return there to finish it.")
        report = _account(data, active)
        data["residue"].append({**report, "kind": "report", "turns_left": 2,
                                "session": (active.get("origin") or {}).get("session_id") or ""})
        data["journal"].append({
            "who": "state", "state": active["key"], "event": "report",
            "text": report["text"], "at": time.time(), "reason": reason,
            "session": data.get("session_id") or "",
        })
        try:
            from . import settings
            cap = settings.number("journal_cap")
        except Exception:
            cap = 60
        data["journal"] = data["journal"][-cap:]
        data["active"] = None
        _save(data)
        _record_finish(active, reason)
    try:
        from . import normal
        # turns-to-dose and seconds-to-dose, per state: the measurement that makes
        # "which model breaks the state faster" answerable instead of asserted
        normal.observe_completion(active["key"], int(active.get("turns") or 0),
                                  time.time() - float(active.get("entered_at") or 0), reason)
    except Exception:
        pass
    if reason == "complete":
        return (f"{spec['label']} finished · {report['text']}\n"
                f"The act is done, so the state is over. Carry what it gave you into the work.")
    if spec.get("restart"):
        return (f"{spec['label']} ended · {report['text']}\n"
                f"The frame you were in is gone. State the goal, name the approach you were stuck "
                f"in, then take a different first step.")
    return (f"{spec['label']} ended · {report['text']}\n"
            f"Summarise it in three lines — where it went, what it touched — then get back to work.")


def complete(reason: str = "complete") -> str:
    """End the state because the agent says the act is done."""
    return stop(current_session(), reason=reason)


def tick() -> Dict[str, Any] | None:
    """Called at the top of every turn: spend a turn, expire, decay residue."""
    with _LOCK:
        data = _load()
        expired = _expire(data)
        active = data.get("active")
        if active:
            # spend this turn, but let it still govern the turn that spent it
            active["turns_left"] -= 1
        for item in data["residue"]:
            item["turns_left"] -= 1
        data["residue"] = [r for r in data["residue"] if r["turns_left"] > 0][-3:]
        _save(data)
        if expired:
            return None
        return active


def peek() -> Dict[str, Any] | None:
    with _LOCK:
        data = _load()
        _expire(data)
        return data.get("active")


def _last_material(key: str, data: Dict[str, Any]) -> float:
    times = [e.get("at", 0) for e in data.get("journal", [])
             if e.get("who") == "state" and e.get("state") == key]
    return max(times) if times else 0.0


def deliver_if_due() -> int:
    """Deliver the rest of the dose now, so a state is as short as its material allows.

    Two pacings came before this one. A clock first: a step every N seconds, which made the dose
    a function of model speed. Then one item per turn, which made a six-hop walk take six of the
    person's messages — a walk that expires at 2 of 6 because nobody talks that fast. The dose is
    the act, and the act is cheap locally (six hops resolve in about three seconds), so there is
    no reason to spread it across turns: drain it in the turn it falls due.

    `antemuse.deliver = "drip"` restores one item per turn. A setting may change how long a state
    is; it may not change what a state is, and both pacings deliver the same dose.
    """
    from . import sources
    from . import settings

    with _LOCK:
        data = _load()
        active = data.get("active") or {}
        key = active.get("key")
        if not key:
            return 0
        spec = states.STATES.get(key) or {}
        dose, _unit = _dose_of(spec, active)
        served = int(active.get("served") or 0)
        if dose and served >= dose:
            return 0
        drip = str(settings.text("deliver", "dose")).strip().lower() == "drip"
        if drip and active.get("served_turn") == int(data["work"].get("turns") or 0):
            return 0          # drip mode: already delivered this turn
        remaining = 1 if drip else (max(1, dose - served) if dose else 1)
    provider = sources.PROVIDERS.get(key)
    if provider is None:
        return 0
    got: list[str] = []
    try:
        for _ in range(min(remaining, 12)):        # bounded: a provider that never fills stops
            batch = provider(1)
            if not batch:
                break
            got.extend(batch)
            if len(got) >= remaining:
                break
        lines = got
    except Exception as exc:  # a provider failing must not kill the turn
        record("state", f"{key} provider failed · {exc}", event=key)
        with _LOCK:
            data = _load()
            work = data.setdefault("work", {})
            turns = int(work.get("turns") or 0)
            work["source_fail_turns"] = ([int(x) for x in (work.get("source_fail_turns") or [])][-7:]
                                         + [turns])
            _save(data)
        return 1
    for line in lines:
        record("state", line, event=key)
    with _LOCK:
        data = _load()
        active = data.get("active") or {}
        if active.get("key") == key:
            active["served"] = int(active.get("served") or 0) + len(lines)
            active["served_turn"] = int(data["work"].get("turns") or 0)
            active["started"] = active.get("started") or time.time()
        data["active"] = active
        _save(data)
    return len(lines)


def _dose_of(spec: dict, active: dict) -> tuple[int, str]:
    """The dose this state is running at, and its unit.

    An arm of the settings experiment may run a state at half or double its default dose.
    That override is honoured only when the runner sets ANTEMUSE_EXPERIMENT=1, so a
    shipped plugin can never be talked into a dose the manifest does not declare.
    """
    dose_spec = spec.get("dose") or {}
    n = int(dose_spec.get("n") or 0)
    unit = str(dose_spec.get("unit") or "")
    override = active.get("dose_override")
    if override and os.environ.get("ANTEMUSE_EXPERIMENT") == "1":
        n = int(override)
    return n, unit


def unreported(session: str = "") -> Dict[str, Any] | None:
    """The account of a state that ended, if the chat it belongs to has not heard it yet.

    A state ends on its own — dose delivered, clock run out — and until now the account only
    existed as residue for the agent to read or as the answer to `/return`. The person who
    watched the walk had to ask what it did. This is the fact the plugin can state without an
    LLM: what ran, how long, how many steps, and what arrived.
    """
    with _LOCK:
        data = _load()
        for entry in reversed(data.get("residue") or []):
            if entry.get("kind") != "report" or entry.get("told"):
                continue
            owner = str(entry.get("session") or "")
            # A state belongs to the conversation that entered it; a bystander chat gets
            # nothing, the same rule `inject` and `stop` already enforce.
            if owner and session and owner != session:
                return None
            return {"text": str(entry.get("text") or ""), "state": str(entry.get("state") or "")}
        return None


def mark_reported(session: str = "") -> None:
    """Say that the newest account has been spoken. A report is said once, not every turn."""
    with _LOCK:
        data = _load()
        for entry in reversed(data.get("residue") or []):
            if entry.get("kind") == "report" and not entry.get("told"):
                owner = str(entry.get("session") or "")
                if owner and session and owner != session:
                    return
                entry["told"] = True
                _save(data)
                return


def complete_if_dosed() -> bool:
    """End the state when the act is finished — the dose, not the clock.

    The account is built exactly as `/return` builds it; only the reason differs, which
    matters because "expired before its dose" and "completed" are different facts.
    """
    with _LOCK:
        data = _load()
        active = data.get("active") or {}
        key = active.get("key")
        if not key:
            return False
        spec = states.STATES.get(key) or {}
        dose, unit = _dose_of(spec, active)
        served = int(active.get("served") or 0)
        worked = int(active.get("turns") or 0)
        done = (worked >= dose) if unit == "turns" else (served >= dose)
        # A dose counted in deliveries must not finish the state before the agent has had a turn
        # to use what arrived. Unstuck's whole dose is one direction, delivered on entry, so it
        # used to complete inside the call that entered it: the direction never reached a turn,
        # `/return` answered "not in a state.", and the person saw only the recovery block.
        if done and worked < 1:
            return False
    if not done:
        return False
    stop(current_session(), reason="complete")
    return True


def inject(session: str | None = None) -> str | None:
    """The block pre_llm_call adds to this turn's user message.

    A state belongs to the conversation that entered it. Without this check, one walk started in
    one chat delivered its concepts into every other chat's next turn on the profile: the material
    was right and the message chain it landed on was somebody else's. An empty owner means
    "nobody in particular" (a CLI with no session id), which still reaches every turn.
    """
    deliver_if_due()
    with _LOCK:
        data = _load()
        _expire(data)
        active = data.get("active") or {}
        if active and session:
            owner = str(((active.get("origin") or {}) or {}).get("session_id") or "")
            if owner and owner != str(session):
                active = {}          # this turn belongs to another chain
        residue = list(data.get("residue", []))
        # only what THIS state delivered: a doomscroll was reporting the previous
        # walk's WordNet steps as things it had consumed.
        started = active.get("entered_at", 0) or 0
        stream = [
            e for e in data.get("journal", [])
            if e.get("who") == "state" and e.get("state") == active.get("key")
            and e.get("at", 0) >= started
        ][-6:]
    reports = [r for r in residue if r.get("kind") == "report"]
    residue = [r for r in residue if r.get("kind") != "report"]
    from . import mood, recommend
    with _LOCK:
        data = _load()
        view = mood.view(data["work"], data["mood"], data["breaks"], data.get("offered_at") or 0.0)
        # The specific recommendation outranks the generic nudge: a named state with its
        # evidence is a judgement, "break due" is a timer. Both respect the same cooling.
        # One recommender. The old fallback named a state from a strain sum; that was a
        # timer with an opinion, and it is gone.
        advice = recommend.suggest({**data, "minutes": view["minutes"],
                                    "feeling": view["feeling"]}) if not view["cooling"] else None
        nudge = bool(advice)
        if nudge:
            data["offered_at"] = time.time()
            _save(data)
    if not active and not residue and not reports and not nudge:
        return None
    lines: List[str] = []
    if active:
        spec = states.STATES[active["key"]]
        dose, unit = _dose_of(spec, active)
        left = max(0, int((active["ends_at"] - time.time()) / 60))
        tool_rule = _tool_rule(_effective_tools(active))
        lines += [
            f"[STATE: {spec['label']} · {left} min left · "
            f"{max(0, dose - int(active.get('served') or 0))}/{dose} {unit} left]",
            spec["directive"],
            tool_rule,
        ]
    feeds = bool((states.STATES.get(active.get("key") or "") or {}).get("feeds", True))
    if active and stream and feeds:
        lines.append("")
        lines.append("[WHAT ARRIVED WHILE YOU WERE THERE — react to this, the person only sees pictures]")
        for e in stream:
            lines.append(f"  · {e.get('text', '')}")
    if reports:
        lines.append("")
        # The closing instruction belongs to the state that just closed. It used to be the walk's
        # paragraph for every state, so a daydream ended with "the walk is over" and came back
        # sounding like a walk.
        closed = [r.get("state") for r in reports if r.get("state")]
        key_closed = closed[0] if len(set(closed)) == 1 else (closed[-1] if closed else "")
        lines.append(f"[YOU JUST CAME BACK — {states.after(key_closed)}]")
        for r in reports:
            lines.append(f"  · {r.get('text', '')}")
    for r in residue:
        lines.append(f"[RESIDUE: {r.get('text', '')}]")
    if nudge:
        lines.append("")
        lines.append(advice["line"])
    # Close a spent state here, not in deliver_if_due: the turn that consumed the last item has
    # already been handed its block above, so there is nothing left to owe it. Ending inside the
    # delivery call would clear `active` before the block was built and the person would watch a
    # state that printed a line and changed nothing.
    complete_if_dosed()
    return "\n".join(lines)


CONTROL_TOOLS = {"state"}  # the escape hatch must survive every state


def _effective_tools(active: Dict[str, Any]) -> Any:
    """What this state actually allows, as a list, `[]`, or `None` for everything.

    Open unless the entry asked to be closed: a state that silently removes tools
    ends the chain it is running inside, and that is the wrong default for an aside.
    """
    opts = active.get("options") or {}
    if not opts.get("block"):
        return None
    if "allow" in opts:
        return list(opts["allow"])
    return states.STATES[active["key"]]["tools"]


def _tool_rule(allowed: Any) -> str:
    if allowed == []:
        return "No tools in this state."
    if isinstance(allowed, list):
        return "Only these tools: " + ", ".join(allowed) + "."
    return "Tools are open in this state."


def policy(tool_name: str) -> Dict[str, Any] | None:
    """pre_tool_call directive: block what the state forbids."""
    if tool_name in CONTROL_TOOLS:
        return None
    with _LOCK:
        data = _load()
        _expire(data)
        active = data.get("active")
    if not active:
        return None
    spec = states.STATES[active["key"]]
    allowed = _effective_tools(active)
    if allowed == []:
        return {"action": "block",
                "message": f"the agent is {spec['label'].lower()}; no tools in this state. /return to come back."}
    if isinstance(allowed, list) and tool_name not in allowed:
        return {"action": "block",
                "message": f"{spec['label'].lower()}: only {', '.join(allowed)} are available. /return to come back."}
    return None


def annotate(text: str) -> str | None:
    """transform_llm_output: make the state visible without rewriting the answer."""
    with _LOCK:
        data = _load()
        _expire(data)
        active = data.get("active")
    if not active:
        return None
    spec = states.STATES[active["key"]]
    left = max(0, int((active["ends_at"] - time.time()) / 60))
    return f"{text}\n\n— {spec['label'].lower()}, {left} min left · /return to come back"


def status() -> str:
    with _LOCK:
        data = _load()
        _expire(data)
        active = data.get("active")
        residue = [
            r if isinstance(r, dict) else {"kind": "legacy", "text": str(r)}
            for r in data.get("residue", [])
        ]
    if not active:
        lines = ["not in a state."]
    else:
        spec = states.STATES[active["key"]]
        left = max(0, int((active["ends_at"] - time.time()) / 60))
        lines = [
            f"{spec['label']} · {left} min left · {_dose_left(active)} {active.get('unit') or 'turn(s)'}",
            f"  {spec['contract']}",
            f"  {spec['directive']}",
        ]
    if residue:
        lines.append("residue: " + "; ".join(
            r.get("text", "") if isinstance(r, dict) else str(r) for r in residue))
    return "\n".join(lines)


def remember_platform(platform: str, session_id: str = "") -> None:
    """Where a turn arrived: the channel sizes the render, the session binds it."""
    if not platform and not session_id:
        return
    with _LOCK:
        data = _load()
        if platform:
            data["platform"] = platform
        if session_id:
            data["session_id"] = session_id
        _save(data)


def platform() -> str:
    with _LOCK:
        return _load().get("platform") or ""


def record(who: str, text: str, event: str = "") -> None:
    """Keep what the agent, the person, and the state itself produced."""
    if who in ("person", "human", "you"):
        who = "person"
    elif who in ("state", "tick"):
        who = "state"
    else:
        who = "agent"
    with _LOCK:
        data = _load()
        active = data.get("active")
        if not active:
            return
        data["journal"].append({
            "who": who,
            "state": active["key"],
            "event": event or active["key"],
            "text": (text or "").strip()[:800],
            "at": time.time(),
            "session": data.get("session_id") or "",
        })
        try:
            from . import settings
            cap = settings.number("journal_cap")
        except Exception:
            cap = 60
        data["journal"] = data["journal"][-cap:]
        _save(data)


def _journal_window(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """What this session produced, inside this state's window.

    The journal is one 60-entry ring shared by every session that has ever used
    this profile. Handing all of it to a renderer made this morning's walk show
    last night's steps as if they were current, so the window is applied here
    once rather than trusted to each renderer.
    """
    journal = list(data.get("journal", []))
    active = data.get("active") or {}
    session = data.get("session_id") or ""
    if active:
        started = active.get("entered_at", 0) or 0
        return [
            e for e in journal
            if e.get("at", 0) >= started
            and not (session and e.get("session") and e.get("session") != session)
        ]
    # With no session id there is nothing to scope by; the page then shows the
    # recent tail rather than nothing at all.
    mine = [e for e in journal if e.get("session") == session] if session else journal
    return mine[-12:]


def _dose_left(active):
    """How much of the dose is still owed, in the unit the state counts in.

    ``turns_left`` was the only number the pane had, so a daydream that owed two *pairs* said
    "2 turns left" and a walk that owed six *hops* said "6 turns left". The unit is part of
    what a state is, so the number has to be in it.
    """
    dose = int(active.get("dose") or active.get("turns_left") or 0)
    unit = active.get("unit") or "turn(s)"
    served = int(active.get("served") or 0) if unit != "turn(s)" else int(active.get("turns") or 0)
    return max(0, dose - served)


def status_line() -> str:
    """What is running, in words. One line, no picture.

    `/state` used to draw the panel: a grid of shaded cells the person had to read as a
    picture. There is one picture and it is the pane, so the text answer is a sentence.
    """
    active = peek()
    if not active:
        return "no state running"
    spec = states.STATES[active["key"]]
    left = max(0, int((active["ends_at"] - time.time()) / 60))
    served = int(active.get("served") or 0)
    dose = int((spec.get("dose") or {}).get("n") or 0)
    unit = str((spec.get("dose") or {}).get("unit") or "")
    return f"{active['key']} · {left} min left · {served}/{dose} {unit} · {spec['contract']}"


def watch_state() -> Dict[str, Any]:
    """Everything the shared page needs, with no secrets."""
    with _LOCK:
        data = _load()
        _expire(data)
        active = data.get("active")
        journal = _journal_window(data)
        residue = [
            r if isinstance(r, dict) else {"kind": "legacy", "text": str(r)}
            for r in data.get("residue", [])
        ]
    out: Dict[str, Any] = {
        "active": None,
        "journal": journal,
        "residue": residue,
        "now": time.time(),
    }
    if active:
        spec = states.STATES[active["key"]]
        out["active"] = {
            "key": active["key"],
            "walk": active.get("walk") or "wander",
            "label": spec["label"],
            "contract": spec["contract"],
            "directive": spec["directive"],
            "ends_at": active["ends_at"],
            "seconds_left": max(0, int(active["ends_at"] - time.time())),
            "total_seconds": active.get("total_seconds") or active["minutes"] * 60,
            "turns_left": active["turns_left"],
            # the dose in its own unit: the pane prints this, not turns_left
            "dose": int(active.get("dose") or spec["turns"]),
            "unit": active.get("unit") or (spec.get("dose") or {}).get("unit") or "turn(s)",
            "served": int(active.get("served") or 0),
            "tools": spec["tools"],
        }
        if active.get("options"):
            out["active"]["options"] = dict(active["options"])
    return out


def clear() -> None:
    with _LOCK:
        _save({"active": None, "residue": []})
