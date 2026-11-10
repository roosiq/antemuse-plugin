"""Registration must survive a platform without termios.

On Windows the plugin failed to register at all — 0 tools, 0 hooks — and the error said
"No module named 'core'". The real cause was `core/tui.py` importing `termios` at module load:
a full-screen terminal feature taking the whole plugin down on a machine that has no terminal to
take over. These tests keep that from coming back, and keep the diagnosis honest.
"""
from __future__ import annotations

import builtins
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class _Ctx:
    def __init__(self) -> None:
        self.tools: dict = {}
        self.hooks: list = []
        self.commands: list = []
        self.skills: list = []

    def register_hook(self, *a, **k):
        self.hooks.append((a, k))

    def register_command(self, *a, **k):
        self.commands.append((a, k))

    def register_tool(self, **kw):
        self.tools[kw["name"]] = kw

    def register_auxiliary_task(self, *a, **k):
        pass

    def register_skill(self, *a, **k):
        self.skills.append((a, k))

    def get_config(self, key, default=None):
        return default


def test_the_takeover_module_loads_without_termios(monkeypatch):
    real_import = builtins.__import__

    def no_posix(name, *args, **kwargs):
        if name in ("termios", "tty"):
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_posix)
    monkeypatch.delitem(sys.modules, "termios", raising=False)
    monkeypatch.delitem(sys.modules, "tty", raising=False)
    monkeypatch.delitem(sys.modules, "core.tui", raising=False)

    tui = importlib.import_module("core.tui")
    assert tui.POSIX_TTY is False
    # and the fallback is the text frame, not a crash
    out = tui.run()
    assert isinstance(out, str) and out


def test_the_plugin_registers_a_tool_and_its_hooks(monkeypatch):
    """The whole surface, loaded the way the host loads it."""
    monkeypatch.delitem(sys.modules, "antemuse", raising=False)
    module = importlib.import_module("__init__")
    ctx = _Ctx()
    module.register(ctx)
    assert "state" in ctx.tools
    assert len(ctx.hooks) >= 5


def test_a_real_error_inside_core_is_not_disguised_as_a_missing_module():
    """The old blanket `except ImportError` reported any failure inside `core` as
    "No module named 'core'" — the wrong diagnosis, and it sent a Windows install looking for a
    packaging problem that did not exist."""
    text = (ROOT / "__init__.py").read_text()
    assert "__package__" in text
    assert "except ImportError" not in text.split('"""', 2)[-1]
