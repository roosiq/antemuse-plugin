"""The walk provider is the only agent material provider."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core import sources, states  # noqa: E402


def test_every_state_has_its_own_provider():
    assert set(sources.PROVIDERS) == set(states.STATES)
    assert all(callable(fn) for fn in sources.PROVIDERS.values())


def test_ready_ignores_non_walk_names():
    assert sources.ready("explore") is None
    assert sources.ready("removed") is None


def test_ready_explains_missing_nltk(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda *_: None)
    why = sources.ready("walk")
    assert why and "nltk" in why and "uv pip install" in why


def test_walk_text_uses_the_active_walk(monkeypatch):
    from core import engine

    engine.enter("walk", walk="wander", session="source")
    calls = []

    class FakeWalk:
        def step(self, n):
            calls.append(n)
            return ["source (n) → destination (n) · took its hypernym"]

    monkeypatch.setattr("core.walks.get", lambda name: FakeWalk())
    assert sources.walk_text(1)[0].startswith("source")
    assert calls == [1]
