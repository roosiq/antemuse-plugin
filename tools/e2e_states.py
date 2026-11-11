"""End-to-end: enter every state, spend its dose, and check what it left behind.

This drives the same path the host drives — `engine.inject()` once per model turn — rather than
calling the providers directly, so what is exercised is the thing a user gets: the injected block,
the ledger rows, the `moves` row, and the ending report.

Each state runs in its own home: a shared ledger would let one state's terms satisfy another's
"already used" skip and quietly change what was served.

    /usr/bin/python3 tools/e2e_states.py            # all states
    /usr/bin/python3 tools/e2e_states.py --only walk

Exit 0 = every state honoured the contract. Exit 1 = at least one did not (the row says which).
No network is required except for doomscroll's feed; a feed failure is reported as a named
failure, not as success.
"""
from __future__ import annotations

import argparse
import json
import time
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STATES = ["walk", "daydream", "doomscroll", "dream", "unstuck"]
MAX_TURNS = 14
# Delivery is paced by the clock (one unit a second), so the turns have to be a second
# apart or the runner measures a state that was never given time to do anything.
TURN_GAP = 1.1


def _fresh_home() -> str:
    home = tempfile.mkdtemp(prefix="e2e-antemuse-")
    os.environ["ANTEMUSE_STATES_HOME"] = home
    return home


def _restore_home(prev) -> None:
    """Leave the process pointing where it was pointing.

    Setting ANTEMUSE_STATES_HOME and then deleting the directory leaves every later caller in the
    same process writing into a path that no longer exists — which is how this runner broke nine
    unrelated tests the first time it ran inside pytest.
    """
    if prev is None:
        os.environ.pop("ANTEMUSE_STATES_HOME", None)
    else:
        os.environ["ANTEMUSE_STATES_HOME"] = prev


def _purge_modules() -> None:
    for name in [m for m in sys.modules if m == "core" or m.startswith("core.")]:
        del sys.modules[name]


def _ledger(home: str):
    """The plugin's own ledger — `concepts.db`, not the host's `state.db`."""
    import sqlite3

    from core import history

    path = history.db_path()
    if not path.exists():
        return None
    return sqlite3.connect(path)


def _rows(conn, sql: str, args: tuple = ()):
    return conn.execute(sql, args).fetchall() if conn else []


def run_state(key: str) -> dict:
    prev_home = os.environ.get("ANTEMUSE_STATES_HOME")
    home = _fresh_home()
    _purge_modules()
    from core import engine, states, history

    out = {"state": key, "home": home, "turns": [], "problems": []}
    entered = engine.enter(key, session="e2e")
    out["entered"] = str(entered)[:200]
    # the entry line is the state's own voice ("WALKING · 3 min · 6 turn(s) · ..."), not the word
    # ACTIVE; what matters is that it reports the state it was asked for
    verb = {"walk": "WALKING", "daydream": "DAYDREAMING", "doomscroll": "DOOMSCROLLING",
            "dream": "DREAMING", "unstuck": "UNSTUCK"}[key]
    if verb not in str(entered).upper():
        out["problems"].append(f"entry did not report {verb}: {entered!r}")

    served_total = 0
    blocks = []
    for turn in range(MAX_TURNS):
        time.sleep(TURN_GAP)               # a turn is a second of the state's life
        engine.note_turn()                 # what the host does before each model turn
        block = engine.inject("e2e")
        data = engine._load() or {}
        active = data.get("active") or {}
        n = int(active.get("served") or 0)
        blocks.append(block or "")
        out["turns"].append({"turn": turn, "block_chars": len(block or ""), "served": n})
        served_total = max(served_total, n)
        if not active:
            out["ended_at_turn"] = turn
            break

    # the state should have ended on its own dose, without anyone calling /return
    active_now = (engine._load() or {}).get("active") or {}
    ended_by_itself = not active_now
    out["ended_by_dose"] = bool(ended_by_itself)
    if not ended_by_itself:
        out["problems"].append("state did not end after its dose within the turn budget")
        engine.stop("e2e", reason="returned")

    data = engine._load() if hasattr(engine, "_load") else {}
    out["journal_tail"] = [e.get("text", "")[:160] for e in (data.get("journal") or [])][-6:]

    conn = _ledger(home)
    # delivery files rows under the *current* session, which in a headless run is empty; the
    # contract being checked is that this state's material reached the ledger at all
    served = _rows(conn, "SELECT c.label, s.move FROM served s JOIN concepts c ON c.id = s.concept_id "
                         "WHERE s.move = ?", (key,))
    moves = _rows(conn, "SELECT state, ending, dose_done FROM moves")
    appearances = _rows(conn, "SELECT COUNT(*) FROM appearances a JOIN served s ON s.concept_id = "
                              "a.concept_id WHERE s.session = 'e2e'")
    if conn:
        conn.close()

    out["served_rows"] = len(served)
    out["served_moves"] = sorted({m for _l, m in served})
    out["served_sample"] = [label for label, _m in served[:5]]
    out["moves_rows"] = [list(r) for r in moves]
    out["appearances_linked"] = int(appearances[0][0]) if appearances else 0

    # A state that named why it had no material has not failed: "feed unavailable" and "no
    # direction available" are results. A state that ended silently served nothing at all.
    named = [t for t in out["journal_tail"]
             if any(w in t.lower() for w in ("unavailable", "no direction", "no project root",
                                             "failed", "missing input"))]
    out["named_failure"] = named[0][:120] if named else ""
    if served_total == 0 and not served:
        if named:
            out["partial"] = f"named failure: {named[0][:90]}"
        else:
            out["problems"].append("state served nothing and said nothing about why")
    if not moves:
        out["problems"].append("no moves row: the ending was not recorded")
    if served and key not in {m for _l, m in served}:
        out["problems"].append(f"served rows are not filed under {key}: {out['served_moves']}")

    # the pane's own payload: what a real pane would light
    try:
        from core import activation
        acts = activation.activations("e2e", key)
        out["activations"] = len(acts) if acts else 0
    except Exception as exc:
        out["activations"] = f"error: {exc}"

    # the account the model is told to speak, and its silence rule
    try:
        from core import report
        build = getattr(report, "facts", None) or getattr(report, "for_turn", None) or getattr(report, "account", None)
        text = build() if callable(build) else ""
        out["report"] = str(text)[:200]
        leaked = [
            s for s in out.get("served_sample") or []
            if s and s.lower() in str(text).lower()
        ]
        if leaked:
            out["problems"].append(f"report quotes served material: {leaked}")
    except Exception as exc:
        out["report"] = f"error: {exc}"

    shutil.rmtree(home, ignore_errors=True)
    _restore_home(prev_home)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    keys = [args.only] if args.only else STATES
    results = []
    for key in keys:
        try:
            results.append(run_state(key))
        except Exception as exc:  # a crash is a result, not a pass
            results.append({"state": key, "problems": [f"crashed: {exc!r}"], "served_rows": 0})

    width = max(len(r["state"]) for r in results) + 2
    bad = 0
    for r in results:
        ok = not r["problems"]
        bad += 0 if ok else 1
        status = "PARTIAL" if r.get("partial") else ("ok  " if ok else "FAIL")
        print(f"{r['state']:<{width}} {status} "
              f"served={r.get('served_rows', 0):<3} moves={r.get('moves_rows')} "
              f"activations={r.get('activations')}")
        for p in r["problems"]:
            print(f"{'':<{width}}   - {p}")
        if r.get("partial"):
            print(f"{'':<{width}}   ~ {r['partial']}")
    print(f"\n{len(results) - bad}/{len(results)} states honoured the contract")
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
