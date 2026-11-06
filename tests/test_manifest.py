"""The manifest and the package agree about who this is and what version it is."""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))


def _plugin():
    spec = importlib.util.spec_from_file_location("antemuse_plugin", os.path.join(ROOT, "__init__.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _manifest() -> dict:
    text = open(os.path.join(ROOT, "plugin.yaml"), encoding="utf-8").read()
    fields = {}
    for line in text.splitlines():
        if ":" in line and not line.startswith((" ", "#", "-")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip('"')
    return fields


def test_manifest_version_matches_package():
    assert _manifest()["version"] == _plugin().__version__


def test_manifest_name_is_the_brand():
    assert _manifest()["name"] == "antemuse"
    assert _manifest()["label"] == "Antemuse"


def test_the_registered_skill_is_the_brand():
    src = open(os.path.join(ROOT, "__init__.py"), encoding="utf-8").read()
    assert '"antemuse",\n            Path(__file__)' in src


def test_no_document_points_at_a_command_that_cannot_register():
    """/snap belongs to Hermes' built-in /snapshot alias; a plugin copy that points
    there sends people to a command that silently does not exist."""
    root = pathlib.Path(ROOT)
    targets = [root / "__init__.py", root / "README.md", root / "SKILL.md", root / "plugin.yaml"]
    targets += sorted((root / "core").glob("*.py"))
    offenders = []
    for path in targets:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for hit in ("/snap ", "`/snap`", "/snap\n", "/snap:"):
            if hit in text:
                offenders.append(f"{path.relative_to(ROOT)}: {hit.strip()}")
    assert not offenders, offenders
