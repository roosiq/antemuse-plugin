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


def test_contributing_lists_the_registry_backed_public_commands():
    contributing = (ROOT / "CONTRIBUTING.md").read_text().lower()
    from core import states

    for command in (*[f"/{key}" for key in states.STATES], "/explore", "/return"):
        assert command in contributing


def test_security_document_discloses_every_active_state():
    security = (ROOT / "SECURITY.md").read_text().lower()
    from core import states

    for key in states.STATES:
        assert key in security
