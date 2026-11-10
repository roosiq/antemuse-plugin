"""Regressions found by the QA pass on 2026-11-09.

Each one was user-visible: a blank card on a fresh install, a takeover that drew
nothing, a mistyped tool action that returned art instead of an answer, and a
documented command that exited without opening anything.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _surfaces():
    sys.path.insert(0, str(ROOT))
    from core import surfaces
    return surfaces


def test_a_fresh_install_still_gets_a_picture(tmp_path, monkeypatch):
    """No baked bank yet: the card must fall back to the frame shipped with the repo."""
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path / "empty-home"))
    (tmp_path / "empty-home").mkdir()
    surfaces = _surfaces()
    rows = surfaces.art(cols=44, rows=10, scene="daydream")
    assert rows, "no art at all"
    assert any(ch not in " ." for ch in "".join(rows)), "art is blank"


def test_the_takeover_has_an_entry_point():
    """`python3 -m core.tui` is documented in README and TESTING; it must run."""
    proc = subprocess.run([sys.executable, "-m", "core.tui"], cwd=ROOT,
                          capture_output=True, text=True, timeout=30,
                          env=dict(os.environ, ANTEMUSE_NO_SCAN="1"))
    assert proc.returncode == 0, proc.stderr[-400:]
    assert "Traceback" not in proc.stderr


def test_a_mistyped_tool_action_says_so(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("ANTEMUSE_NO_SCAN", "1")
    (tmp_path / "home").mkdir()
    spec = importlib.util.spec_from_file_location("antemuse_fallback_qa", ROOT / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    class Ctx:
        def __init__(self):
            self.tools = {}

        def register_hook(self, *a, **k):
            pass

        def register_command(self, *a, **k):
            pass

        def register_tool(self, **kw):
            self.tools[kw["name"]] = kw

        def register_auxiliary_task(self, *a, **k):
            pass

        def register_skill(self, *a, **k):
            pass

        def get_config(self, key, default=None):
            return default

    ctx = Ctx()
    module.register(ctx)
    out = ctx.tools["state"]["handler"]({"action": "frobnicate"})
    assert "no such action" in out.lower(), out[:120]
