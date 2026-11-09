"""The ledger as a graph: provenance, artifacts, and a picture that can be read."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT))
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))

from core import graph, history  # noqa: E402


def _ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    history.notice("shipper", move="walk", session="20261108_091834_aaaa")
    history.notice("ledger", move="walk", session="20261108_091834_aaaa")
    history.notice("shipper", move="dream", session="20261107_120000_bbbb")
    history.notice_artifact("antemuse-plugin", "core/history.py")
    return tmp_path


def test_a_concept_is_connected_to_the_session_it_was_met_in(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    data = graph.snapshot()
    kinds = {n["kind"] for n in data["nodes"]}
    assert {"concept", "session"} <= kinds, kinds
    relations = {e["relation"] for e in data["edges"]}
    assert "served_in" in relations
    ids = {n["id"] for n in data["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in data["edges"])


def test_a_file_is_an_artifact_and_belongs_to_a_project(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    data = graph.snapshot()
    files = [n for n in data["nodes"] if n["kind"] == "file"]
    assert files and files[0]["key"].startswith("antemuse-plugin/"), files
    relations = {e["relation"] for e in data["edges"]}
    assert "in_project" in relations


def test_two_concepts_served_in_one_move_are_linked(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    data = graph.snapshot()
    assert "co_served" in {e["relation"] for e in data["edges"]}


def test_a_session_is_a_hub_with_a_few_spokes_not_eighty(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    for i in range(30):
        history.notice(f"concept{i}", move="walk", session="20261108_091834_aaaa")
    data = graph.snapshot()
    spokes = [e for e in data["edges"] if e["relation"] == "served_in"]
    assert len(spokes) <= 8, len(spokes)


def test_a_session_id_is_shown_as_a_date(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    data = graph.snapshot()
    labels = [n["label"] for n in data["nodes"] if n["kind"] == "session"]
    assert "Nov 8 09:18" in labels, labels


def test_an_empty_or_broken_ledger_is_an_empty_graph_not_an_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path / "nothing-here"))
    data = graph.snapshot()
    assert data["nodes"] == [] and data["edges"] == []
    corrupt = tmp_path / "corrupt"
    corrupt.mkdir()
    (corrupt / "concepts.db").write_text("not a database")
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(corrupt))
    assert graph.snapshot()["nodes"] == []


def test_the_summary_counts_what_the_picture_shows(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    data = graph.snapshot()
    summary = graph.summary(data)
    assert summary["nodes:concept"] == len([n for n in data["nodes"] if n["kind"] == "concept"])
    assert sum(v for k, v in summary.items() if k.startswith("edges:")) == len(data["edges"])


def test_the_picture_is_actually_drawn(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    out = tmp_path / "graph"
    result = subprocess.run([sys.executable, str(ROOT / "tools/graph_export.py"),
                             "--limit", "40", "--out", str(out)],
                            capture_output=True, text=True, timeout=120,
                            env={**os.environ, "ANTEMUSE_STATES_HOME": str(tmp_path)})
    assert result.returncode == 0, result.stderr[-400:]
    png, svg, data = out / "concept-graph.png", out / "concept-graph.svg", out / "concept-graph.json"
    assert png.exists() and png.stat().st_size > 4000
    assert "<circle" in svg.read_text()
    payload = json.loads(data.read_text())
    assert payload["nodes"] and payload["summary"]["nodes:concept"] >= 1
