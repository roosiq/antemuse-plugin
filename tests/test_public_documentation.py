"""Public documents describe the runtime registration and data boundaries."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_security_document_names_the_current_runtime_surface_and_storage():
    security = (ROOT / "SECURITY.md").read_text().lower()
    for fact in (
        "/walk",
        "/explore",
        "/return",
        "pre_llm_call",
        "pre_tool_call",
        "transform_llm_output",
        "post_tool_call",
        "state(action=...)",
        "no network client",
        "no subprocess",
        "read-only",
        "14 days",
        "300 user/assistant messages",
        "2-second budget",
        "30 minutes",
        "state.json",
        "recent_turns.json",
        "concepts.db",
        "walks/*.json",
        ".antemuse/walk_cursor.json",
        "config.yaml",
        "memory.md",
        "user.md",
    ):
        assert fact in security


def test_contributing_lists_only_the_three_public_commands():
    contributing = (ROOT / "CONTRIBUTING.md").read_text().lower()
    for command in ("/walk", "/explore", "/return"):
        assert command in contributing
    for retired in ("daydream", "doomscroll", "unstuck", "dream"):
        assert retired not in contributing


def test_security_document_drops_retired_commands():
    security = (ROOT / "SECURITY.md").read_text().lower()
    for retired in ("daydream", "doomscroll", "unstuck", "dream"):
        assert retired not in security
