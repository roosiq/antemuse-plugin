"""The plugin must use Hermes' own mechanisms, because a provider swap must not break it.

Each test here pins one interface the host really offers — checked against the host
source, not against our own helper's docstring.
"""
from __future__ import annotations

import importlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_no_module_of_ours_hardcodes_the_hermes_home():
    """`~/.hermes` is a default, not a constant: profiles and HERMES_HOME move it."""
    offenders = []
    for path in (ROOT / "core").glob("*.py"):
        text = path.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            if "~/.hermes" in line or '".hermes/' in line:
                if "plugin-data" in line or "memories" in line:
                    offenders.append(f"{path.name}:{i}")
    assert not offenders, f"hardcoded Hermes home: {offenders}"


def test_hermes_home_is_resolved_not_assumed(monkeypatch, tmp_path):
    from core import storage
    # with no host module available, HERMES_HOME is the answer
    monkeypatch.setitem(sys.modules, "hermes_constants", None)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "profile-home"))
    assert storage.hermes_home() == tmp_path / "profile-home"
    # and the data dir is derived from it, not from a guess
    monkeypatch.delenv("ANTEMUSE_STATES_HOME", raising=False)
    monkeypatch.setitem(sys.modules, "plugins.plugin_storage", None)
    assert storage.data_dir() == tmp_path / "profile-home" / "plugin-data" / "antemuse"


def test_memory_limitation_is_named_not_hidden(monkeypatch):
    from core import recall, sources
    monkeypatch.setattr(recall, "recent", lambda *a, **k: [])
    monkeypatch.setattr(sources, "memories", lambda: [])
    monkeypatch.setattr(sources, "memory_provider", lambda: "hindsight")
    line = sources.memory_pairs()[0]
    assert "hindsight" in line and "cannot read" in line, line

    monkeypatch.setattr(sources, "memory_provider", lambda: "builtin")
    assert "nothing said in this conversation" in sources.memory_pairs()[0]


def test_daydream_material_survives_an_external_memory_provider(monkeypatch, tmp_path):
    """The point of the fix: with hindsight configured, a daydream still has material."""
    from core import recall, sources
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    monkeypatch.setattr(sources, "memories", lambda: [])          # no built-in files
    monkeypatch.setattr(sources, "memory_provider", lambda: "hindsight")

    recall.remember("the parser keeps dropping the trailing brace", "person")
    recall.remember("so the diff is empty every time and the test passes anyway", "agent")
    lines = sources.memory_pairs()
    joined = " ".join(lines)
    assert lines, "no material"
    assert not any("cannot read" in line for line in lines), lines
    assert "trailing brace" in joined and "diff is empty" in joined, joined


def test_all_model_calls_go_through_the_host_facade():
    """No provider SDK, no HTTP, no key of our own: only `ctx.llm`."""
    imports = []
    for path in (ROOT / "core").glob("*.py"):
        text = path.read_text()
        for name in ("openai", "anthropic", "requests", "httpx", "aiohttp", "google.generativeai"):
            if re.search(rf"^\s*(import|from)\s+{re.escape(name)}\b", text, re.M):
                imports.append(f"{path.name}:{name}")
    assert not imports, f"provider SDK imported in core: {imports}"
    llm = (ROOT / "core/llm.py").read_text()
    assert "acomplete_structured" in llm
    # the facade's real signature, from agent/plugin_llm.py
    for kwarg in ("instructions=", "input=", "json_schema=", "max_tokens=", "timeout="):
        assert kwarg in llm, f"call does not match PluginLlm.acomplete_structured: {kwarg}"


def test_the_task_key_we_route_to_is_one_we_registered():
    """PluginLlm refuses an auxiliary task the plugin never declared."""
    src = (ROOT / "__init__.py").read_text()
    aux = re.search(r"AUXILIARY_TASKS\s*=\s*[\[(](.*?)[\])]", src, re.S)
    assert aux, "no AUXILIARY_TASKS table"
    declared = set(re.findall(r'\("([a-z_]+)"', aux.group(1)))
    used = set(re.findall(r'task_name="([a-z_]+)"', (ROOT / "core/runtime.py").read_text()))
    assert used and used <= declared, f"routed to undeclared task(s): {used - declared}"
