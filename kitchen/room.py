"""The room: an automated phase machine that accumulates sparks.

One tick advances one phase. State phases resolve themselves (and tell you what
changed); move phases hand out a brief and wait for a spark; converge keeps the
best spark of the arc and starts the next one.

No model calls live here, so the machine can be driven by a cron tick, an agent
tool call, or a human slash command with identical behaviour.
"""
from __future__ import annotations

import json
import random
import re
import time
from typing import Any, Dict, List, Tuple

from . import deck, judge, phases, store
from .visual import Frame, Spark, render_png, render_text

ROOM_FILE = "room.json"


# ---------------------------------------------------------------- persistence

def load() -> Dict[str, Any] | None:
    path = store.data_dir() / ROOM_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def save(room: Dict[str, Any] | None) -> None:
    path = store.data_dir() / ROOM_FILE
    if room is None:
        path.unlink(missing_ok=True)
        return
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(room, indent=2))
    tmp.replace(path)


def create(seed: str | None = None, rotation: List[str] | None = None) -> Dict[str, Any]:
    room = {
        "room": "rm_" + "".join(random.choice("abcdefghijkmnpqrstuvwxyz23456789") for _ in range(6)),
        "arc": 1,
        "phase": "discover",
        "rotation": rotation or list(phases.ROTATION),
        "seed": (seed or deck.deal_seed("room", 1))[:400],
        "relief": 0,
        "penalty": 0,
        "expect_far": False,
        "sparks": [],
        "keepers": [],
        "state_log": [],
        "created": time.time(),
    }
    save(room)
    return room


# --------------------------------------------------------------------- tick

def step(room: Dict[str, Any]) -> str:
    """Advance until a phase that needs a human/agent, applying state phases."""
    notes: List[str] = []
    for _ in range(4):
        key = room["phase"]
        spec = phases.phase(key)

        if spec["kind"] == "state":
            notes.append(_apply_state(room, key, spec))
            room["phase"] = phases.next_phase(room["rotation"], key)
            continue

        if spec["kind"] == "converge":
            notes.append(_converge(room))
            continue

        save(room)
        return _brief(room, notes)

    save(room)
    return _brief(room, notes)


def _apply_state(room: Dict[str, Any], key: str, spec: Dict) -> str:
    effect = spec.get("effect")
    if effect == "relief":
        room["relief"] = min(2, room.get("relief", 0) + 1)
        room["state_log"].append({"phase": key, "at": time.time()})
        return f"{spec['label']} · {spec['minutes']} min, no input · residue kept (+5 on the next spark)"
    if effect == "recombine":
        pool = [s["title"] for s in room["sparks"][-6:]]
        if len(pool) >= 2:
            a, b = random.SystemRandom().sample(pool, 2)
            room["seed"] = f"{a} meets {b}"[:400]
            msg = f"DREAM · seed recombined: {room['seed']}"
        else:
            msg = "DREAM · not enough sparks to recombine yet; the seed held"
        room["state_log"].append({"phase": key, "at": time.time()})
        return msg
    if effect == "distance":
        room["seed"] = f"a stranger in 2036 inherits: {room['seed']}"[:400]
        room["expect_far"] = True
        room["state_log"].append({"phase": key, "at": time.time()})
        return "DISSOCIATE · seed handed to a stranger in 2036; far distance is now expected"
    if effect == "sabotage":
        room["penalty"] = room.get("penalty", 0) + 10
        room["state_log"].append({"phase": key, "at": time.time()})
        return "DOOMSCROLL · 20 minutes consumed · the room will charge 10 on the next spark"
    return f"{spec['label']} · nothing changed"


def _converge(room: Dict[str, Any]) -> str:
    arc_sparks = [s for s in room["sparks"] if s["arc"] == room["arc"]]
    if arc_sparks:
        best = max(arc_sparks, key=lambda s: s["score"])
        room["keepers"].append({
            "arc": room["arc"], "title": best["title"],
            "score": best["score"], "do_first": best["do_first"],
        })
        # the next arc inherits the work, not the idea: seeding from the winning
        # title just re-runs the winner and starves novelty
        room["seed"] = best["do_first"][:400]
        kept = f"kept “{best['title']}” ({best['score']})"
    else:
        kept = "nothing worth keeping"
    room["arc"] += 1
    room["phase"] = "discover"
    room["expect_far"] = False
    return f"CONVERGE · {kept} · arc {room['arc'] - 1} closed, arc {room['arc']} opens"


def _brief(room: Dict[str, Any], notes: List[str]) -> str:
    key = room["phase"]
    spec = phases.phase(key)
    lines = []
    if notes:
        lines += ["· " + n for n in notes] + [""]
    lines += [
        f"ROOM {room['room']} · arc {room['arc']} · phase {spec['label']}",
        "",
        f"  seed   {room['seed']}",
        f"  asks   {spec['asks']}",
        f"  write  title :: because ... :: do this first",
    ]
    if room.get("relief"):
        lines.append(f"  residue {room['relief']} × +5 from a walk or a daydream")
    if room.get("penalty"):
        lines.append(f"  debt   −{room['penalty']} from doomscrolling")
    return "\n".join(lines)


# ------------------------------------------------------------------- commit

_LABEL = re.compile(r"^\s*(title|spark|idea|why|because|try next|next|try|do this first)\s*[:：-]\s*", re.I)


def split_submission(text: str) -> Tuple[str, str, str] | None:
    raw = (text or "").strip()
    for sep in ("::", "|"):
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep)]
            break
    else:
        return None
    parts = [_LABEL.sub("", p).strip() for p in parts]
    if len(parts) != 3 or not all(parts):
        return None
    return parts[0], parts[1], parts[2]


def commit(room: Dict[str, Any], text: str) -> Tuple[str, Dict[str, Any] | None]:
    key = room["phase"]
    if not phases.is_move(key):
        return f"phase {key.upper()} does not take a spark. call step first.", None
    parts = split_submission(text)
    if parts is None:
        return ("three parts please: title :: because ... :: do this first", None)
    title, because, do_first = parts
    spec = phases.phase(key)

    ctx = {
        "seed": room["seed"],
        "move": spec["move"],
        "prior": [f"{s['title']} — {s['because']}" for s in room["sparks"][-12:]],
        "hint": False,
        "word_budget": 60,
    }
    result = judge.score({"title": title, "why": because, "try_next": do_first}, ctx)

    total = result["total"]
    if room.get("relief"):
        total = min(100, total + 5 * room["relief"])
        room["relief"] = 0
        result["notes"].append("walk residue +5")
    if room.get("penalty"):
        total = max(0, total - room["penalty"])
        result["notes"].append(f"doomscroll debt −{room['penalty']}")
        room["penalty"] = 0
    if room.get("expect_far") and result["distance"] == "far":
        total = min(100, total + 5)
        result["notes"].append("far, as the room asked")
    result["total"] = total
    result["verdict"] = judge.verdict(total)

    spark = {
        "n": len(room["sparks"]) + 1,
        "arc": room["arc"],
        "phase": key,
        "move": spec["move"],
        "score": total,
        "distance": result["distance"],
        "title": title,
        "because": because,
        "do_first": do_first,
        "seed": room["seed"],
        "at": time.time(),
    }
    room["sparks"].append(spark)
    room["seed"] = f"{title} — {do_first}"[:400]
    room["expect_far"] = False
    room["phase"] = phases.next_phase(room["rotation"], key)
    save(room)

    card = _card(spark, result)
    return card, spark


def _card(spark: Dict[str, Any], result: Dict[str, Any]) -> str:
    axes = result["axes"]
    return "\n".join([
        f"{spark['phase'].upper()} · {spark['title']} · {spark['score']}/100",
        f"  move {axes['move_discipline']:>2} · why {axes['mechanism']:>2} · next {axes['actionability']:>2} · new {axes['novelty']:>2}"
        f" · distance {spark['distance']}",
        ("  " + "; ".join(n for n in result["notes"])) if result["notes"] else "",
    ]).rstrip()


# ------------------------------------------------------------------ surfaces

def frame(room: Dict[str, Any], limit: int = 7) -> Frame:
    sparks = room["sparks"][-limit:]
    return Frame(
        room=room["room"],
        arc=room["arc"],
        phase=room["phase"],
        seed=room["seed"],
        sparks=[Spark(n=s["n"], phase=s["phase"], score=s["score"], distance=s["distance"], title=s["title"]) for s in sparks],
        keepers=list(room["keepers"]),
    )


def poster(room: Dict[str, Any]) -> str:
    path = store.data_dir() / f"room_{room['room']}_arc{room['arc']}.png"
    return render_png(frame(room), str(path))


def transcript(room: Dict[str, Any]) -> str:
    return render_text(frame(room))
