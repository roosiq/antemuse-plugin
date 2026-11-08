"""A trailhead on a repository with nothing in it — and silence once it has a spec."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import recommend, sources, states  # noqa: E402


def _repo(path: Path, commits: int = 0, spec: bool = False) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    if spec:
        (path / "specs" / "changes" / "x").mkdir(parents=True, exist_ok=True)
        (path / "specs" / "changes" / "x" / "spec.md").write_text("# x\n")
    for i in range(commits):
        (path / f"f{i}.py").write_text("x = 1\n")
        subprocess.run(["git", "-C", str(path), "add", "."], check=True)
        subprocess.run(["git", "-C", str(path), "commit", "-qm", f"step {i}"], check=True)
    return path


def test_the_state_exists_with_a_read_only_budget():
    spec = states.STATES["trailhead"]
    assert spec["minutes"] == 5 and spec["turns"] == 3 and spec["cadence"] == 20
    assert spec["tools"] == ["read_file", "search_files"], "a trailhead that can edit is a scaffold"
    assert states.resolve("start") == "trailhead"


def test_material_names_what_is_missing_instead_of_inventing_it(monkeypatch, tmp_path):
    repo = _repo(tmp_path / "fresh")
    monkeypatch.chdir(repo)
    lines = " | ".join(sources.trailhead_text())
    assert "no commits yet" in lines
    assert "no README" in lines
    assert "no spec files yet" in lines
    assert "invented" not in lines.lower()


def test_material_reports_a_project_that_already_has_a_spec(monkeypatch, tmp_path):
    repo = _repo(tmp_path / "started", commits=4, spec=True)
    monkeypatch.chdir(repo)
    lines = " | ".join(sources.trailhead_text())
    assert "already decided" in lines and "specs/changes/x/spec.md" in lines
    assert "a trailhead here is late" in lines


def test_the_recommendation_fires_on_a_repository_with_nothing_in_it(monkeypatch, tmp_path):
    repo = _repo(tmp_path / "empty")
    monkeypatch.chdir(repo)
    setattr(recommend, "_NEW_CACHE", {"at": 0.0, "value": None})
    got = recommend.suggest({"work": {"turns": 2}})
    assert got and got["pattern"] == "new project"
    assert "/trailhead" in got["line"]


def test_it_stops_firing_once_the_project_has_a_spec(monkeypatch, tmp_path):
    repo = _repo(tmp_path / "started", commits=6, spec=True)
    monkeypatch.chdir(repo)
    setattr(recommend, "_NEW_CACHE", {"at": 0.0, "value": None})
    got = recommend.suggest({"work": {"turns": 2, "streak": 0}})
    assert got is None, got


def test_a_loop_on_a_new_project_still_recommends_the_trailhead(monkeypatch, tmp_path):
    repo = _repo(tmp_path / "empty2")
    monkeypatch.chdir(repo)
    setattr(recommend, "_NEW_CACHE", {"at": 0.0, "value": None})
    got = recommend.suggest({"work": {"turns": 5, "streak": 6}})
    assert got and got["pattern"] == "new project", got
