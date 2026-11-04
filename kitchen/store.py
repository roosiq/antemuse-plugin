"""Persistence: one active round per profile (JSON) and a shared board (SQLite).

The active round is a single file rather than per-session state because the CLI
minigame is play-then-submit in two commands; a profile plays one service at a
time. The board is the social layer: humans and agents write the same rows.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List

PLUGIN_NAME = "antemuse-kitchen"


def data_dir() -> Path:
    override = os.environ.get("ANTEMUSE_KITCHEN_HOME") or os.environ.get("CONCEPT_KITCHEN_HOME")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    try:
        from plugins.plugin_storage import plugin_data_dir  # type: ignore
        return plugin_data_dir(PLUGIN_NAME)
    except Exception:  # standalone/test use
        path = Path.home() / ".antemuse-kitchen"
        path.mkdir(parents=True, exist_ok=True)
        return path


def _active_path() -> Path:
    return data_dir() / "active.json"


def load_active() -> Dict[str, Any] | None:
    path = _active_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def save_active(state: Dict[str, Any] | None) -> None:
    path = _active_path()
    if state is None:
        path.unlink(missing_ok=True)
        return
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(path)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(data_dir() / "board.db")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sparks (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               ts REAL NOT NULL,
               player TEXT NOT NULL,
               kind TEXT NOT NULL,
               model TEXT DEFAULT '',
               service TEXT NOT NULL,
               round INTEGER NOT NULL,
               move TEXT NOT NULL,
               seed TEXT NOT NULL,
               title TEXT NOT NULL,
               why TEXT NOT NULL,
               try_next TEXT NOT NULL,
               total INTEGER NOT NULL,
               distance TEXT NOT NULL,
               axes TEXT NOT NULL
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS services (
               service TEXT PRIMARY KEY,
               player TEXT NOT NULL,
               kind TEXT NOT NULL,
               started REAL NOT NULL,
               total INTEGER NOT NULL DEFAULT 0,
               best INTEGER NOT NULL DEFAULT 0,
               rounds INTEGER NOT NULL DEFAULT 0,
               completed INTEGER NOT NULL DEFAULT 0
           )"""
    )
    return conn


def record_spark(player: Dict[str, str], service: str, round_no: int, move: str,
                 seed: str, title: str, why: str, try_next: str, score: Dict[str, Any]) -> None:
    conn = _connect()
    with conn:
        conn.execute(
            "INSERT INTO sparks (ts, player, kind, model, service, round, move, seed, title, why, try_next, total, distance, axes)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), player["name"], player["kind"], player.get("model", ""), service,
             round_no, move, seed, title, why, try_next, score["total"],
             score.get("distance", ""), json.dumps(score.get("axes", {}))),
        )
        conn.execute(
            "INSERT INTO services (service, player, kind, started, total, best, rounds, completed)"
            " VALUES (?,?,?,?,?,?,?,0)"
            " ON CONFLICT(service) DO UPDATE SET total = total + excluded.total,"
            " best = MAX(best, excluded.best), rounds = rounds + 1",
            (service, player["name"], player["kind"], time.time(), score["total"],
             score["total"], 1),
        )
    conn.close()


def close_service(service: str) -> None:
    conn = _connect()
    with conn:
        conn.execute("UPDATE services SET completed = 1 WHERE service = ?", (service,))
    conn.close()


def leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    conn = _connect()
    rows = conn.execute(
        """SELECT player, kind, model, COUNT(*) AS sparks, SUM(total) AS total,
                  MAX(total) AS best, AVG(total) AS avg
           FROM sparks GROUP BY player, kind, model
           ORDER BY total DESC, best DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def table_titles(limit: int = 12) -> List[str]:
    conn = _connect()
    rows = conn.execute("SELECT title FROM sparks ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [r["title"] for r in rows if r["title"]]


def table_for_service(service: str) -> List[Dict[str, Any]]:
    conn = _connect()
    rows = conn.execute(
        "SELECT round, move, title, total, distance FROM sparks WHERE service = ? ORDER BY round",
        (service,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
