"""The environment gates decide whether a suite failure means anything.

A gate that asks `shutil.which()` passes on a stub the program cannot run, so the test it guards
still fails — and a red suite on Windows stops carrying information. These tests make the gate
answer the only question that matters: does the program execute?
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from conftest import _runs, needs_bash, needs_git  # noqa: E402


def test_a_program_that_runs_is_accepted():
    exe = Path(sys.executable).name
    assert _runs(exe) or _runs("python3"), "neither the running interpreter nor python3 executes"


def test_a_program_that_is_absent_is_refused():
    assert _runs("definitely-not-a-real-program-8b1f") is False


def test_a_program_that_resolves_but_cannot_execute_is_refused(monkeypatch, tmp_path):
    """The WindowsApps stub shape: `which` finds it, running it raises."""
    stub = tmp_path / "stub-bash"
    stub.write_text("#!/bin/sh\nexit 0\n")
    stub.chmod(0o644)                       # present, not executable -> PermissionError on POSIX
    import conftest

    monkeypatch.setattr("shutil.which", lambda name: str(stub))
    assert conftest._runs("bash") is False


def test_the_gates_are_marks_that_can_skip():
    for mark in (needs_bash(), needs_git()):
        assert hasattr(mark, "args"), "gate must be a pytest mark"
        assert isinstance(mark.args[0], bool)
