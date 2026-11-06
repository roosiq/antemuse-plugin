"""One active state per profile, with whatever residue it left behind.

Profile-wide rather than per-session: the metaphor is about the agent, not about
a chat window, and a slash command has no session id to hang it on.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, List

from . import states, storage

FILE = "state.json"
_LOCK = threading.Lock()


def _load() -> Dict[str, Any]:
    path = storage.data_dir() / FILE
    if not path.exists():
        return {"active": None, "residue": [], "journal": []}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {"active": None, "residue": [], "journal": []}
    data.setdefault("active", None)
    data.setdefault("residue", [])
    data.setdefault("journal", [])
    return data


def _save(data: Dict[str, Any]) -> None:
    path = storage.data_dir() / FILE
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


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
    ]
    # the account is the material the state delivered, not the agent's own prose:
    # counting replies as "steps" made a five-step walk report ten.
    steps = [e for e in events if e.get("who") == "state"]
    # the clock stops when the state ends, not when someone notices it ended
    ended = min(time.time(), active.get("ends_at") or time.time())
    mins = max(1, int(round((ended - started) / 60)))
    trail: List[str] = []
    for e in steps:
        head = " ".join(e["text"].split()[:6]).rstrip(",.;:· ")
        if head and head not in trail:
            trail.append(head)
    body = " → ".join(trail[:5]) if trail else "nothing arrived"
    return {
        "state": key,
        "text": f"{key} {mins}m · {len(steps)} step(s) · {body[:180]}",
        "steps": len(steps),
    }


def _expire(data: Dict[str, Any], now: float | None = None) -> bool:
    active = data.get("active")
    if not active:
        return False
    now = now if now is not None else time.time()
    if active["turns_left"] <= 0 or now >= active["ends_at"]:
        report = _account(data, active)
        data["residue"].append({**report, "kind": "report", "turns_left": 2})
        data.setdefault("journal", []).append({
            "who": "state", "state": active["key"], "event": "report",
            "text": report["text"], "at": now,
        })
        data["journal"] = data["journal"][-60:]
        data["active"] = None
        try:
            from . import ticker
            ticker.stop()
        except Exception:
            pass
        return True
    return False


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


def enter(key: str, minutes: int | None = None, walk: str | None = None) -> str:
    spec_key = states.resolve(key)
    if not spec_key:
        return f"no such state. try: {', '.join(states.STATES)}"
    from . import sources
    why_not = sources.ready(spec_key)
    if why_not:
        return f"cannot enter {spec_key} · {why_not}"
    spec = states.STATES[spec_key]
    with _LOCK:
        data = _load()
        previous = data.get("active") or {}
        now = time.time()
        duration = float(minutes if minutes else spec["minutes"])
        data["active"] = {
            "key": spec_key,
            "walk": walk or (previous.get("walk") if previous and previous["key"] == spec_key else "wander"),
            "entered_at": now,
            "ends_at": now + duration * 60,
            "turns_left": spec["turns"],
            "minutes": duration,
            "total_seconds": duration * 60,
        }
        _save(data)
    from . import ticker
    ticker.start(spec_key)
    note = ""
    if previous and previous["key"] != spec_key:
        note = f" (left {previous['key']}; no residue kept)"
    return f"{spec['label']} · {duration:g} min · {spec['turns']} turn(s) · {spec['contract']}{note}"


def stop() -> str:
    with _LOCK:
        data = _load()
        active = data.get("active")
        if not active:
            return "not in a state."
        spec = states.STATES[active["key"]]
        report = _account(data, active)
        data["residue"].append({**report, "kind": "report", "turns_left": 2})
        data["journal"].append({
            "who": "state", "state": active["key"], "event": "report",
            "text": report["text"], "at": time.time(),
        })
        data["journal"] = data["journal"][-60:]
        data["active"] = None
        _save(data)
    from . import ticker
    ticker.stop()
    return (f"{spec['label']} ended · {report['text']}\n"
            f"Come back and tell the person what happened in there.")


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


def inject() -> str | None:
    """The block pre_llm_call adds to this turn's user message."""
    with _LOCK:
        data = _load()
        _expire(data)
        active = data.get("active") or {}
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
    if not active and not residue and not reports:
        return None
    lines: List[str] = []
    if active:
        spec = states.STATES[active["key"]]
        left = max(0, int((active["ends_at"] - time.time()) / 60))
        allowed = spec["tools"]
        tool_rule = (
            "No tools in this state." if allowed == []
            else ("Only these tools: " + ", ".join(allowed) + ".") if isinstance(allowed, list)
            else "Tools are allowed."
        )
        lines += [
            f"[STATE: {spec['label']} · {left} min left · {active['turns_left']} turn(s)]",
            spec["directive"],
            tool_rule,
        ]
    if active and stream:
        lines.append("")
        lines.append("[WHAT ARRIVED WHILE YOU WERE THERE — react to this, the person only sees pictures]")
        for e in stream:
            lines.append(f"  · {e.get('text', '')}")
    if reports:
        lines.append("")
        lines.append("[YOU JUST CAME BACK — say what happened in there, in your own words, before anything else]")
        for r in reports:
            lines.append(f"  · {r.get('text', '')}")
    for r in residue:
        lines.append(f"[RESIDUE: {r.get('text', '')}]")
    return "\n".join(lines)


CONTROL_TOOLS = {"state"}  # the escape hatch must survive every state


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
    allowed = spec["tools"]
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
            f"{spec['label']} · {left} min left · {active['turns_left']} turn(s)",
            f"  {spec['contract']}",
            f"  {spec['directive']}",
        ]
    if residue:
        lines.append("residue: " + "; ".join(
            r.get("text", "") if isinstance(r, dict) else str(r) for r in residue))
    return "\n".join(lines)


def remember_platform(platform: str) -> None:
    """The channel a turn arrived on, so renders can size themselves to it."""
    if not platform:
        return
    with _LOCK:
        data = _load()
        data["platform"] = platform
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
        })
        data["journal"] = data["journal"][-60:]
        _save(data)


def watch_state() -> Dict[str, Any]:
    """Everything the shared page needs, with no secrets."""
    with _LOCK:
        data = _load()
        _expire(data)
        active = data.get("active")
        journal = list(data.get("journal", []))
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
            "tools": spec["tools"],
        }
    return out


def clear() -> None:
    with _LOCK:
        _save({"active": None, "residue": []})
