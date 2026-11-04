"""Terminal rendering. ASCII only, 66 columns, no colour dependency."""
from __future__ import annotations

import textwrap
from typing import Any, Dict, List

W = 66


def _line(text: str = "", prefix: str = "  ") -> str:
    chunks = textwrap.wrap(text, width=W - len(prefix)) or [""]
    pad = " " * len(prefix)
    return "\n".join((prefix if i == 0 else pad) + chunk for i, chunk in enumerate(chunks))


def _bar(value: int, maximum: int = 25, width: int = 12) -> str:
    filled = int(round((value / maximum) * width)) if maximum else 0
    return "█" * filled + "·" * (width - filled)


def rule(char: str = "─") -> str:
    return char * W


def header(left: str, right: str = "") -> str:
    inner = W - 4
    gap = max(1, inner - len(left) - len(right))
    return f"╔═ {left}{' ' * gap}{right} ═╗"[: W]


def brief(state: Dict[str, Any], player: Dict[str, str]) -> str:
    move = state["move"].upper()
    job = {
        "FLIP": "reverse exactly one dimension",
        "SHIFT": "move exactly one frame",
        "CONNECT": "borrow one transferable mechanism",
        "UNPACK": "name one overlooked ingredient",
    }.get(move, "")
    src = state.get("source") or "deck"
    par = len(state.get("par") or [])
    lines = [
        header("ANTEMUSE KITCHEN", f"round {state['round']}/{state['rounds']}"),
        _line(f"player {player['name']} · {player['kind']} · service {state['service']}"),
        rule(),
        _line(f"SEED  {state['seed']}"),
        "",
        _line(f"MOVE  {move} — {job}"),
        _line(f"WANT  {state['expected_distance']} distance · context {state['context']}"),
        _line(f"PAR   {src}" + (f", {par} reference cards" if par else "")),
    ]
    if src == "deck" and state.get("par_error"):
        lines.append(_line(f"      engine unavailable: {state['par_error']}"))
    lines += [
        rule(),
        _line("answer  /cook submit <title> :: <because ...> :: <do this first>"),
        _line("        hint −8 · pass · board · rules"),
        rule("═"),
    ]
    return "\n".join(lines)


def score_card(result: Dict[str, Any], state: Dict[str, Any], title: str) -> str:
    axes = result["axes"]
    move = state["move"]
    move_gloss = {
        "flip": "named the dimension you reversed",
        "shift": "named the frame you moved",
        "connect": "named the source and the borrowed mechanism",
        "unpack": "named the overlooked ingredient",
    }.get(move, "named the move")
    rows = [
        ("move", axes["move_discipline"], move_gloss),
        ("why", axes["mechanism"], "said why it works"),
        ("next", axes["actionability"], "verb + bound"),
        ("new", axes["novelty"], f"distance {result.get('distance', '?')}"),
    ]
    lines = [
        header(f"ROUND {state['round']}/{state['rounds']}", f"{result['total']}/100"),
        _line(f"{state['move'].upper()} · {title}"),
        rule(),
    ]
    for label, value, gloss in rows:
        lines.append(f"  {label:5s} {value:2d}/25  {_bar(value)}  {gloss}")
    lines.append(rule())
    for penalty in result.get("penalties", []):
        lines.append(_line(f"−{abs(penalty['points'])}  {penalty['reason']}"))
    for note in result.get("notes", []):
        lines.append(_line(f"· {note}"))
    lines += [rule(), _line(_verdict_line(result)), rule("═")]
    return "\n".join(lines)


def _verdict_line(result: Dict[str, Any]) -> str:
    verdict = result["verdict"]
    tail = {
        "NEW SAUCE": "the table has nothing like it and the reason is explicit.",
        "SEASONED": "usable. One axis is holding it back; the notes say which.",
        "EDIBLE": "the idea is real but the move is mush. Name the one thing you changed.",
        "UNDERCOOKED": "it reads as advice, not a spark. Commit to a next action.",
        "RAW": "no move, no mechanism, no next step. Reroll or take the hint.",
    }.get(verdict, "")
    return f"{verdict} — {tail}"


def service_summary(state: Dict[str, Any], rows: List[Dict[str, Any]], player: Dict[str, str]) -> str:
    total = sum(r["total"] for r in rows)
    lines = [
        header("SERVICE COMPLETE", f"{total}/500"),
        _line(f"{player['name']} · service {state['service']}"),
        rule(),
    ]
    for row in rows:
        lines.append(f"  r{row['round']}  {row['move'].upper():8s} {row['total']:3d}  {row['title'][:38]}")
    lines += [rule(), _line(_closing(total)), rule("═")]
    return "\n".join(lines)


def _closing(total: int) -> str:
    if total >= 420:
        return "Five rounds that compound: every seed came from your own last spark."
    if total >= 320:
        return "Solid service. The chain held for most rounds — check where it broke."
    if total < 200 and state_rounds_short(total):
        return "Short service: the chain only pays when it is run. Five rounds or nothing."
    if total >= 200:
        return "Half the rounds moved, half restated. The judge counted both."
    return "The chain collapsed early. Play again and name one dimension per round."


def state_rounds_short(total: int) -> bool:
    return total < 500


def board(rows: List[Dict[str, Any]]) -> str:
    lines = [header("LEADERBOARD", f"{len(rows)} players · cumulative"), rule()]
    if not rows:
        lines.append(_line("no sparks yet"))
    for i, row in enumerate(rows, 1):
        kind = row["kind"]
        model = f" · {row['model']}" if row.get("model") else ""
        lines.append(f"  {i:2d}. {row['player'][:16]:16s} {kind:6s} {row['total']:5d}  avg {row['avg']:4.1f}  best {row['best']:3d}  n={row['sparks']}{model}")
    lines.append(rule("═"))
    return "\n".join(lines)


def hint_card(move: str, dims: List[str]) -> str:
    lines = [
        header("HINT", "−8"),
        _line(f"the move is {move.upper()}; name exactly one of these and say what the default was:"),
        "",
        _line("  " + " · ".join(dims)),
        rule("═"),
    ]
    return "\n".join(lines)
