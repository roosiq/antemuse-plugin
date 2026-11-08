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


def test_no_retired_name_appears_anywhere():
    """The name is Antemuse. The older ones are not spelled anywhere, this file included."""
    # never written whole, so this check passes itself
    needles = ("kit" + "chen", "antemuse-" + "room", "antemuse-" + "states")
    skip = {"node_modules", ".git", "__pycache__", ".pytest_cache", "test-results"}
    # Recorded model output is not our prose: a scene set in a domestic room
    # mentions the retired word, and a retired name inside an answer is evidence,
    # not branding. Only the evidence directory is exempt — not every directory
    # that happens to be called "results".
    evidence = pathlib.Path(ROOT) / "evaluation" / "results"
    offenders = []
    for path in pathlib.Path(ROOT).rglob("*"):
        if not path.is_file() or skip & set(path.parts):
            continue
        if evidence in path.parents:
            continue
        if path.suffix in {".png", ".jpg", ".jpeg", ".zip", ".pyc", ".ico"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            continue
        for needle in needles:
            if needle in text:
                offenders.append(f"{path.relative_to(ROOT)}: {needle}")
                break
    assert not offenders, offenders


def test_nothing_in_core_names_a_channel_or_sends_anything():
    """Origin binding is free because the plugin only returns strings.

    A single `chat_id`, `thread_id`, or send call in core/ would let a state
    answer somewhere other than where it was started."""
    # reading a feed is fine; addressing a channel or posting to one is not
    bad = ("chat_id", "thread_id", "channel_id", "sendMessage", "send_message",
           "post_message", "requests.post", ".send(", "gateway.send")
    offenders = []
    for path in sorted((pathlib.Path(ROOT) / "core").glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in bad:
            if needle in text:
                offenders.append(f"{path.name}: {needle}")
    assert not offenders, offenders
