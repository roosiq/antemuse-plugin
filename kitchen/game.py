"""Concept Kitchen — the round loop, shared by the /cook command and the cook tool.

Both entry points call the same functions with the same submission schema, so a
human and an agent are playing the identical game with identical scoring. The
only difference is the label on the board row.
"""
from __future__ import annotations

import os
import random
import re
from typing import Any, Dict, List, Tuple

from . import deck, engine, judge, render, store

DEFAULT_CONFIG: Dict[str, Any] = {
    "use_engine": True,
    "engine_url": engine.DEFAULT_URL,
    "word_budget": 60,
}

_CONFIG: Dict[str, Any] = dict(DEFAULT_CONFIG)


def configure(cfg: Dict[str, Any] | None) -> None:
    merged = dict(DEFAULT_CONFIG)
    if isinstance(cfg, dict):
        merged.update({k: v for k, v in cfg.items() if v is not None})
    _CONFIG.clear()
    _CONFIG.update(merged)


def player(name: str | None, kind: str = "human", model: str = "") -> Dict[str, str]:
    clean = (name or "").strip()
    if not clean:
        clean = os.environ.get("USER") or "player"
    return {"name": clean[:32], "kind": "agent" if kind == "agent" else "human", "model": (model or "")[:40]}


def _new_state(p: Dict[str, str], seed: str | None = None) -> Dict[str, Any]:
    service = deck.new_service_id(random.SystemRandom())
    spec = deck.round_spec(service, 1)
    if seed:
        spec["seed"] = seed[:300]
    state: Dict[str, Any] = {
        **spec,
        "player": p["name"],
        "kind": p["kind"],
        "prior": [],
        "scores": [],
        "hint_used": False,
        "source": "deck",
        "par": [],
        "par_error": "",
        "started": True,
    }
    _deal_par(state)
    store.save_active(state)
    return state


def _deal_par(state: Dict[str, Any]) -> None:
    if not _CONFIG.get("use_engine", True):
        state.update({"source": "deck", "par": [], "par_error": "engine disabled in config"})
        return
    result = engine.deal(
        move=state["move"],
        seed=state["seed"],
        distance=state["expected_distance"],
        context=state["context"],
        url=str(_CONFIG.get("engine_url") or engine.DEFAULT_URL),
    )
    state.update({"source": result["source"], "par": result["cards"], "par_error": result.get("error", "")})


def _active_for(p: Dict[str, str]) -> Dict[str, Any] | None:
    state = store.load_active()
    if not state:
        return None
    return state


def start(p: Dict[str, str], seed: str | None = None) -> str:
    state = _active_for(p)
    if state and state.get("player") != p["name"] and not state.get("finished"):
        return (render.header("KITCHEN BUSY", "one service at a time")
                + "\n" + render._line(f"{state['player']} has an open service on this profile.") + "\n"
                + render._line("finish it with /cook submit, or end it with /cook pass.") + "\n"
                + render.rule("═"))
    if state and state.get("player") == p["name"]:
        return render.brief(state, p)
    return render.brief(_new_state(p, seed), p)


def submit(p: Dict[str, str], text: str) -> str:
    state = _active_for(p)
    if not state:
        return _need_start()
    if state.get("player") != p["name"]:
        return render._line(f"{state['player']} owns the open service; /cook pass ends it.") 
    parts = _split(text)
    if parts is None:
        return (render.header("SUBMISSION NEEDS THREE PARTS")
                + "\n" + render._line("/cook submit <title> :: <because ...> :: <do this first>")
                + "\n" + render._line("Separate with :: or |. All three are required — that is the game.")
                + "\n" + render.rule("═"))
    title, why, try_next = parts
    ctx = {
        "seed": state["seed"],
        "move": state["move"],
        "prior": list(state.get("prior") or []) + store.table_titles(12),
        "distance": state["expected_distance"],
        "hint": bool(state.get("hint_used")),
        "word_budget": int(_CONFIG.get("word_budget") or 60),
    }
    result = judge.score({"title": title, "why": why, "try_next": try_next}, ctx)
    total = result["total"]
    if state["expected_distance"] == "far" and result["distance"] == "far":
        total = min(100, total + 5)
        result["total"] = total
        result["notes"].append("+5 the round asked for far and you went far")
        result["verdict"] = judge.verdict(total)

    store.record_spark(p, state["service"], state["round"], state["move"], state["seed"],
                       title, why, try_next, result)
    state.setdefault("scores", []).append({"round": state["round"], "total": total,
                                           "title": title, "move": state["move"],
                                           "distance": result["distance"]})
    state.setdefault("prior", []).append(f"{title} — {why}")

    card = render.score_card(result, state, title)
    if state["round"] >= state["rounds"]:
        store.close_service(state["service"])
        store.save_active(None)
        rows = store.table_for_service(state["service"])
        return card + "\n" + render.service_summary(state, rows, p)

    nxt = deck.round_spec(state["service"], state["round"] + 1,
                         previous_seed=f"{title} — {try_next}"[:240])
    state.update(nxt)
    state["hint_used"] = False
    _deal_par(state)
    store.save_active(state)
    return card + "\n" + render.brief(state, p)


def hint(p: Dict[str, str]) -> str:
    state = _active_for(p)
    if not state:
        return _need_start()
    state["hint_used"] = True
    store.save_active(state)
    spec = judge.MOVE_SPECS.get(state["move"], {})
    dims = list(spec.get("dims", {}).keys())
    if not dims:
        dims = ["source domain", "transferred mechanism"] if state["move"] == "connect" else ["overlooked ingredient", "its cost"]
    return render.hint_card(state["move"], dims)


def pass_service(p: Dict[str, str]) -> str:
    state = _active_for(p)
    if not state:
        return render._line("no open service to pass.")
    store.close_service(state["service"])
    store.save_active(None)
    rows = store.table_for_service(state["service"])
    return render.service_summary(state, rows, p) if rows else render._line("passed with an empty service. the table keeps the loss.")


def board(p: Dict[str, str]) -> str:
    return render.board(store.leaderboard())


def rules(p: Dict[str, str]) -> str:
    return judge.RULES


def status(p: Dict[str, str]) -> str:
    state = _active_for(p)
    if not state:
        return render._line("no open service. /cook play starts one.")
    return render.brief(state, p)


def _need_start() -> str:
    return (render.header("NO OPEN SERVICE")
            + "\n" + render._line("/cook play deals a seed. Five rounds, one move per round.")
            + "\n" + render.rule("═"))


_LABEL = re.compile(
    r"^\s*(title|spark|idea|why|why it connects|because|try next|next|try)\s*[:：-]\s*",
    re.IGNORECASE,
)


def _split(text: str) -> Tuple[str, str, str] | None:
    raw = (text or "").strip()
    for sep in ("::", "|"):
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep)]
            break
    else:
        return None
    parts = [_LABEL.sub("", part).strip() for part in parts]
    if len(parts) != 3 or not all(parts):
        return None
    return parts[0], parts[1], parts[2]
