"""Which repository is "this project"?

The plugin runs inside the host process — the gateway, the desktop main — and that
process sits wherever it was launched from. A state that reads local git history must
therefore ask the *agent's* working directory, not the host's cwd, or a chat running
inside a repository sees the wrong history and both `dream` and `unstuck` refuse at
entry with "fewer than three local git commit subjects".

Found in a live CLI chat: `cd <the plugin checkout> && hermes chat --cli` then
`/dream` answered `can't start dream · empty · fewer than three local git commit
subjects are available for two recombinations`, because the host's cwd was not the
repository the chat was working in (`$HOME` there, a dotfiles repo with none in a day).

Every case pits two real repositories against each other, so the answer never depends
on where the test runner happens to sit.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import storage  # noqa: E402

HINTS = ("ANTEMUSE_PROJECT_ROOT", "TERMINAL_CWD")


@pytest.fixture(autouse=True)
def _no_ambient_hint(monkeypatch):
    """The suite runs inside a host that exports its own hint; every case sets what it means."""
    for name in HINTS:
        monkeypatch.delenv(name, raising=False)


def _repo(base: Path, name: str, subjects) -> Path:
    root = base / name
    root.mkdir()
    run = lambda *args: subprocess.run(["git", "-C", str(root), *args],
                                       capture_output=True, text=True, check=True)
    run("init", "-q")
    run("config", "user.email", "t@example.com")
    run("config", "user.name", "T")
    for subject in subjects:
        run("commit", "-q", "--allow-empty", "-m", subject)
    return root


def test_the_agents_working_directory_wins_over_the_host_cwd(tmp_path, monkeypatch):
    host = _repo(tmp_path, "host", ["host work"])
    agent = _repo(tmp_path, "agent", ["agent work", "more agent work"])
    monkeypatch.chdir(host)
    assert storage.project_root() == host, "with no hint the host cwd answers"
    monkeypatch.setenv("TERMINAL_CWD", str(agent))
    assert storage.project_root() == agent


def test_an_explicit_argument_beats_every_hint(tmp_path, monkeypatch):
    host = _repo(tmp_path, "host", ["host work"])
    agent = _repo(tmp_path, "agent", ["agent work"])
    monkeypatch.chdir(host)
    monkeypatch.setenv("TERMINAL_CWD", str(host))
    monkeypatch.setenv("ANTEMUSE_PROJECT_ROOT", str(host))
    assert storage.project_root(agent) == agent


def test_the_plugin_hint_is_preferred_to_the_agents_cwd(tmp_path, monkeypatch):
    host = _repo(tmp_path, "host", ["host work"])
    plugin = _repo(tmp_path, "plugin", ["plugin work"])
    monkeypatch.chdir(host)
    monkeypatch.setenv("ANTEMUSE_PROJECT_ROOT", str(plugin))
    monkeypatch.setenv("TERMINAL_CWD", str(host))
    assert storage.project_root() == plugin


def test_a_stale_hint_falls_back_instead_of_crashing(tmp_path, monkeypatch):
    host = _repo(tmp_path, "host", ["host work"])
    monkeypatch.chdir(host)
    monkeypatch.setenv("TERMINAL_CWD", str(tmp_path / "does-not-exist"))
    monkeypatch.setenv("ANTEMUSE_PROJECT_ROOT", "")
    assert storage.project_root() == host


def test_the_host_can_hand_us_the_calling_sessions_cwd(tmp_path, monkeypatch):
    host = _repo(tmp_path, "host", ["host work"])
    session = _repo(tmp_path, "session", ["session work", "more session work"])
    monkeypatch.chdir(host)
    monkeypatch.setenv("TERMINAL_CWD", str(host))
    storage.set_session_cwd_provider(lambda: str(session))
    try:
        assert storage.project_root() == session
    finally:
        storage.set_session_cwd_provider(None)
    assert storage.project_root() == host, "withdrawing the provider falls back to the env"


def test_a_provider_that_raises_is_not_fatal(tmp_path, monkeypatch):
    host = _repo(tmp_path, "host", ["host work"])
    monkeypatch.chdir(host)
    storage.set_session_cwd_provider(lambda: (_ for _ in ()).throw(RuntimeError("no session")))
    try:
        assert storage.project_root() == host
    finally:
        storage.set_session_cwd_provider(None)
