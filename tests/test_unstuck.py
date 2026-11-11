"""A unstuck on a repository with nothing in it — and silence once it has a spec."""
from __future__ import annotations

import subprocess

from conftest import needs_git  # noqa: E402
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from core import recommend, settings, sources, states  # noqa: E402


pytestmark = needs_git()

class _Host:
    """The host surface settings reads; display is on, because these tests are about speech."""

    def __init__(self, values=None):
        self.values = values or {}

    def get_config(self, key, default=None):
        return self.values.get(key, default)


@pytest.fixture(autouse=True)
def _recommendations_visible():
    settings.bind(_Host({"show_recommendations": True}))
    yield



def _repo(path: Path, commits: int = 0, spec: bool = False) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    if spec:
        (path / "specs" / "changes" / "x").mkdir(parents=True, exist_ok=True)
        (path / "specs" / "changes" / "x" / "spec.md").write_text("# x\n")
        (path / "README.md").write_text("# started\n\nA project that already has a direction.\n")
    for i in range(commits):
        (path / f"f{i}.py").write_text("x = 1\n")
        subprocess.run(["git", "-C", str(path), "add", "."], check=True)
        subprocess.run(["git", "-C", str(path), "commit", "-qm", f"step {i}"], check=True)
    return path


def test_the_state_exists_with_a_read_only_budget():
    spec = states.STATES["unstuck"]
    assert spec["minutes"] == 5 and spec["turns"] == 3 and spec["cadence"] == 20
    assert spec["tools"] == ["read_file", "search_files"], "a unstuck that can edit is a scaffold"
    assert states.resolve("start") == "unstuck"


def test_material_names_what_is_missing_instead_of_inventing_it(monkeypatch, tmp_path):
    """Every direction is bound to evidence; the evidence IS the missing thing."""
    repo = _repo(tmp_path / "fresh")
    monkeypatch.chdir(repo)
    # the ledger and the graph add candidates, so a dose of six is a sample of the evidence
    # rather than all of it; ask for enough to cover every input this fixture can produce
    lines = " | ".join(sources.unstuck_text(12))
    assert "no commits" in lines
    assert "no README" in lines
    assert "no spec files yet" in lines
    assert "invented" not in lines.lower()


def test_material_reports_a_project_that_already_has_a_spec(monkeypatch, tmp_path):
    repo = _repo(tmp_path / "started", commits=4, spec=True)
    monkeypatch.chdir(repo)
    lines = " | ".join(sources.unstuck_text(6))
    assert "spec file(s) and 4 commit(s) already exist" in lines
    assert "pick the next unfinished acceptance check" in lines
    assert "no spec files yet" not in lines, "a project with a spec is not a greenfield"


def test_the_recommendation_fires_on_a_repository_with_nothing_in_it(monkeypatch, tmp_path):
    repo = _repo(tmp_path / "empty")
    monkeypatch.chdir(repo)
    setattr(recommend, "_NEW_CACHE", {"at": 0.0, "value": None})
    got = recommend.suggest({"work": {"turns": 2}})
    assert got and got["pattern"] == "new project"
    assert "/unstuck" in got["line"]


def test_it_stops_firing_once_the_project_has_a_spec(monkeypatch, tmp_path):
    repo = _repo(tmp_path / "started", commits=6, spec=True)
    monkeypatch.chdir(repo)
    setattr(recommend, "_NEW_CACHE", {"at": 0.0, "value": None})
    got = recommend.suggest({"work": {"turns": 2, "streak": 0}})
    assert got is None, got


def test_a_loop_on_a_new_project_still_recommends_the_unstuck(monkeypatch, tmp_path):
    repo = _repo(tmp_path / "empty2")
    monkeypatch.chdir(repo)
    setattr(recommend, "_NEW_CACHE", {"at": 0.0, "value": None})
    got = recommend.suggest({"work": {"turns": 5, "streak": 6}})
    assert got and got["pattern"] == "new project", got


def test_entering_a_state_posts_nothing_into_the_chat(monkeypatch):
    """Chat carries no visualization: the picture is the desktop pane, and a state beginning is
    not a reason to put art into a conversation."""
    posted = []
    import importlib
    plugin = importlib.import_module("__init__")
    monkeypatch.setattr(plugin, "_post", lambda text: posted.append(text) or True)

    line = plugin._enter("unstuck")("5", session_id="chat-1", platform="discord")

    assert "UNSTUCK" in line.upper() or "unstuck" in line.lower()
    assert posted == [], "a state beginning posts no picture"


def test_a_finished_state_is_handed_to_the_model_to_say(monkeypatch):
    """The plugin supplies the facts; the model says them in the house voice.

    A mechanical line posted by the plugin reads like a log entry. The person is owed a sentence,
    and the only thing in the system that can write one is the model — in the turn it was
    already going to take.
    """
    import importlib
    from core import engine

    plugin = importlib.import_module("__init__")
    posted = []
    monkeypatch.setattr(plugin, "_post", lambda text: posted.append(text) or True)

    plugin._enter("walk")("", session_id="chat-1", platform="discord")
    engine.note_turn()
    engine.stop("chat-1")

    block = plugin._pre_llm_call(prompt="hi", session_id="chat-1", platform="discord") or ""
    assert "[ANTEMUSE REPORT]" in block
    assert "step(s)" in block, "the facts travel with the request"
    assert "The agent in the third person" in block, "the voice travels too"
    assert posted == [], "the plugin does not write the sentence itself"

    # It is only counted as said once the model has actually said something.
    assert engine.unreported("chat-1")
    plugin._transform(response_text="WALKING ended · the agent walked 1m · 2 step(s) · a → b",
                      session_id="chat-1")
    assert engine.unreported("chat-1") is None

    # And the next turn does not ask again.
    again = plugin._pre_llm_call(prompt="hi again", session_id="chat-1", platform="discord") or ""
    assert "[ANTEMUSE REPORT]" not in again


def test_another_chat_is_not_asked_to_report(monkeypatch):
    """The state belonged to one conversation; a bystander turn does not narrate it."""
    import importlib
    from core import engine

    plugin = importlib.import_module("__init__")
    plugin._enter("walk")("", session_id="chat-1", platform="discord")
    engine.note_turn()
    engine.stop("chat-1")

    block = plugin._pre_llm_call(prompt="hi", session_id="chat-2", platform="discord") or ""
    assert "[ANTEMUSE REPORT]" not in block
