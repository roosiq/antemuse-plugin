"""One active state per profile, with whatever residue it left behind.

Profile-wide rather than per-session: the metaphor is about the agent, not about
a chat window, and a slash command has no session id to hang it on.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, List

from . import definitions, store

FILE = "state.json"
_LOCK = threading.Lock()


def _load() -> Dict[str, Any]:
    path = store.data_dir() / FILE
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
    path = store.data_dir() / FILE
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def _expire(data: Dict[str, Any], now: float | None = None) -> bool:
    active = data.get("active")
    if not active:
        return False
    now = now if now is not None else time.time()
    if active["turns_left"] <= 0 or now >= active["ends_at"]:
        data["residue"].append({"text": definitions.STATES[active["key"]]["residue"], "turns_left": 2})
        data["active"] = None
        return True
    return False


def enter(key: str, minutes: int | None = None) -> str:
    spec_key = definitions.resolve(key)
    if not spec_key:
        return f"no such state. try: {', '.join(definitions.STATES)}"
    spec = definitions.STATES[spec_key]
    with _LOCK:
        data = _load()
        previous = data.get("active")
        now = time.time()
        duration = float(minutes if minutes else spec["minutes"])
        data["active"] = {
            "key": spec_key,
            "entered_at": now,
            "ends_at": now + duration * 60,
            "turns_left": spec["turns"],
            "minutes": duration,
            "total_seconds": duration * 60,
        }
        _save(data)
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
        spec = definitions.STATES[active["key"]]
        data["residue"].append({"text": spec["residue"], "turns_left": 2})
        data["active"] = None
        _save(data)
    return f"{spec['label']} ended · residue: {spec['residue']}"


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
        active = data.get("active")
        residue = [r["text"] for r in data.get("residue", [])]
    if not active and not residue:
        return None
    lines: List[str] = []
    if active:
        spec = definitions.STATES[active["key"]]
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
    for r in residue:
        lines.append(f"[RESIDUE: {r}]")
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
    spec = definitions.STATES[active["key"]]
    allowed = spec["tools"]
    if allowed == []:
        return {"action": "block",
                "message": f"the agent is {spec['label'].lower()}; no tools in this state. /snap to return."}
    if isinstance(allowed, list) and tool_name not in allowed:
        return {"action": "block",
                "message": f"{spec['label'].lower()}: only {', '.join(allowed)} are available. /snap to return."}
    return None


def annotate(text: str) -> str | None:
    """transform_llm_output: make the state visible without rewriting the answer."""
    with _LOCK:
        data = _load()
        _expire(data)
        active = data.get("active")
    if not active:
        return None
    spec = definitions.STATES[active["key"]]
    left = max(0, int((active["ends_at"] - time.time()) / 60))
    return f"{text}\n\n— {spec['label'].lower()}, {left} min left · /snap to come back"


def status() -> str:
    with _LOCK:
        data = _load()
        _expire(data)
        active = data.get("active")
        residue = [r["text"] for r in data.get("residue", [])]
    if not active:
        lines = ["not in a state."]
    else:
        spec = definitions.STATES[active["key"]]
        left = max(0, int((active["ends_at"] - time.time()) / 60))
        lines = [
            f"{spec['label']} · {left} min left · {active['turns_left']} turn(s)",
            f"  {spec['contract']}",
            f"  {spec['directive']}",
        ]
    if residue:
        lines.append("residue: " + "; ".join(residue))
    return "\n".join(lines)


def record(who: str, text: str) -> None:
    """Keep what the agent and the person each produced in the same state."""
    who = "person" if who in ("person", "human", "you") else "agent"
    with _LOCK:
        data = _load()
        active = data.get("active")
        if not active:
            return
        data["journal"].append({
            "who": who,
            "state": active["key"],
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
        residue = [r["text"] for r in data.get("residue", [])]
    out: Dict[str, Any] = {
        "active": None,
        "journal": journal,
        "residue": residue,
        "now": time.time(),
    }
    if active:
        spec = definitions.STATES[active["key"]]
        out["active"] = {
            "key": active["key"],
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
