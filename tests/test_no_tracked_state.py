"""Repository hygiene: local plugin state is never tracked."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or not (ROOT / ".git").exists(),
    reason="not a git checkout (the release package ships without .git)",
)


def _tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"], check=True, text=True, capture_output=True
    )
    return result.stdout.splitlines()


def test_local_antemuse_state_is_not_tracked():
    assert not [path for path in _tracked_paths() if path.startswith(".antemuse/")]


def test_python_bytecode_is_not_tracked():
    assert not [
        path
        for path in _tracked_paths()
        if "/__pycache__/" in f"/{path}" or path.endswith(".pyc")
    ]
