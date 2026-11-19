"""Dream is about the day, and a day happens whether or not anyone committed anything."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import history, recall, sources


def _no_repo(monkeypatch, tmp_path):
    monkeypatch.setattr(sources, "projects", lambda: [])


def test_dream_starts_in_a_chat_with_no_repository(monkeypatch, tmp_path):
    _no_repo(monkeypatch, tmp_path)
    for text in ("the pricing page needs an annual discount line",
                 "the signup flow should explain the yearly discount",
                 "the pricing page and signup share a discount"):
        recall.remember(text, "person", "no-git")
    assert sources.ready("dream", session="no-git") is None
    lines = sources.day_connections(2, session="no-git")
    assert len(lines) == 2
    assert all("today:" in line for line in lines), lines
    assert "commit" not in " ".join(lines).lower()


def test_dream_uses_the_ledger_when_the_chat_has_no_turns(monkeypatch, tmp_path):
    _no_repo(monkeypatch, tmp_path)
    history.notice("joint venture", move="walk", session="ledger-only")
    history.notice("design boundary", move="unstuck", session="ledger-only")
    assert sources.ready("dream", session="ledger-only") is None
    lines = sources.day_connections(2, session="ledger-only")
    assert lines and "nothing from today yet" not in lines[0], lines
    assert "joint venture" in " ".join(lines)


def test_dream_refuses_plainly_when_the_day_really_is_empty(monkeypatch, tmp_path):
    _no_repo(monkeypatch, tmp_path)
    why = sources.ready("dream", session="empty-day")
    assert why and "commit" not in why.lower(), why
    assert "nothing from today yet" in why


def test_dream_does_not_read_another_chats_day(monkeypatch, tmp_path):
    _no_repo(monkeypatch, tmp_path)
    recall.remember("ALICE PRIVATE: the payroll cut is tied to Project Juniper", "person", "alice")
    recall.remember("ALICE PRIVATE: legal wants the terms held until Friday", "person", "alice")
    history.notice("payroll cut", move="walk", session="alice")
    assert sources.ready("dream", session="bob") is not None
    lines = sources.day_connections(2, session="bob")
    assert "ALICE" not in " ".join(str(x) for x in lines)


def test_commits_are_still_used_when_they_exist(monkeypatch, tmp_path):
    monkeypatch.setattr(sources, "projects", lambda: [tmp_path])
    monkeypatch.setattr(sources, "_recent_subjects", lambda root, want=3: [
        "add the ledger writer", "fix the pricing page", "wire the signup flow"])
    recall.remember("an unrelated turn", "person", "with-git")
    lines = sources.day_connections(1, session="with-git")
    assert lines and tmp_path.name in str(lines[0]), lines


def test_no_state_ever_requires_a_git_repo(monkeypatch, tmp_path):
    """Standing rule: a repo is optional enrichment for every state, never a condition of entry.

    `/dream` refused in any chat outside a checkout, and `/unstuck` did too. Neither state is
    about git; both are about the person's day. This guards the whole set, not just those two.
    """
    from core import engine, states
    monkeypatch.setattr(sources.storage, "project_root", lambda: None)
    monkeypatch.setattr(sources, "projects", lambda: [])
    for text in ("the pricing page needs an annual discount line",
                 "the signup flow should explain the yearly discount",
                 "the pricing page and signup share a discount"):
        recall.remember(text, "person", "repo-free")
    history.notice("joint venture", move="walk", session="repo-free")
    history.notice("design boundary", move="unstuck", session="repo-free")

    banned = ("git", "repo", "commit", "checkout")
    for key in states.STATES:
        why = sources.ready(key, session="repo-free")
        if why:
            assert not any(word in why.lower() for word in banned), (key, why)
    for key in ("daydream", "dream", "unstuck"):
        out = engine.enter(key, session="repo-free")
        assert "can't start" not in out, (key, out)
        engine.stop("repo-free")
