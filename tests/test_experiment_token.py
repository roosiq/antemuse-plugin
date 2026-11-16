"""Development experiments require an explicitly supplied token."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("antemuse_experiment_token", ROOT / "experiments" / "token.py")
if SPEC is None or SPEC.loader is None:  # pragma: no cover - the file is repository source
    raise ImportError("cannot load experiments/token.py")
TOKEN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOKEN)


def test_remote_experiments_require_an_explicit_token(monkeypatch):
    monkeypatch.delenv("NOUS_ACCESS_TOKEN", raising=False)
    with pytest.raises(SystemExit, match="NOUS_ACCESS_TOKEN is required"):
        TOKEN.require_nous_token()


def test_remote_experiments_use_the_explicit_token(monkeypatch):
    monkeypatch.setenv("NOUS_ACCESS_TOKEN", "test-token")
    assert TOKEN.require_nous_token() == "test-token"
