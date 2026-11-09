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
    history.notice("shipper", move="walk", session="20261108_091834_aaaa", ref="101")
    history.notice("ledger", move="walk", session="20261108_091834_aaaa", ref="101")
    history.notice("shipper", move="dream", session="20261107_120000_bbbb", ref="202")
    history.notice_artifact("antemuse-plugin", "core/history.py", commit="abc1234")
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


def test_two_concepts_in_the_same_message_are_linked(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    data = graph.snapshot()
    linked = [e for e in data["edges"] if e["relation"] == "co_served"]
    assert linked, {e["relation"] for e in data["edges"]}
    assert linked[0]["weight"] == 1 and linked[0]["evidence"]["messages"] == 1


def test_sharing_only_a_session_is_not_a_link(tmp_path, monkeypatch):
    """A session is often a hundred messages; two concepts sharing one is the template."""
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    history.notice("shipper", move="walk", session="20261108_091834_aaaa", ref="1")
    history.notice("ledger", move="walk", session="20261108_091834_aaaa", ref="2")
    data = graph.snapshot()
    assert "co_served" not in {e["relation"] for e in data["edges"]}


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


# ------------------------------------------------------- semantic projection

def _embeddings():
    """A tiny stand-in for the model's output: three obvious directions plus noise."""
    import random
    rng = random.Random(11)
    base = {
        "gateway": [1.0, 0.0, 0.0], "plugin": [0.95, 0.1, 0.0], "manifest": [0.9, 0.2, 0.05],
        "evaluation": [0.0, 1.0, 0.0], "verdict": [0.1, 0.95, 0.0], "reviewer": [0.05, 0.9, 0.1],
        "porosity": [0.0, 0.0, 1.0], "thermal": [0.1, 0.0, 0.95], "material": [0.05, 0.05, 0.9],
    }
    vectors = {}
    for label, vec in base.items():
        noisy = [v + rng.uniform(-0.02, 0.02) for v in vec]
        norm = sum(v * v for v in noisy) ** 0.5
        vectors[label] = [v / norm for v in noisy]
    return {"model": "test", "dim": 3, "vectors": vectors}


def test_the_projection_is_deterministic():
    emb = _embeddings()
    labels = sorted(emb["vectors"])
    import tools.graph_export as ge  # noqa: E402
    a = ge.pca2(emb["vectors"], labels)
    b = ge.pca2(emb["vectors"], labels)
    assert all(abs(a[k][0] - b[k][0]) < 1e-9 and abs(a[k][1] - b[k][1]) < 1e-9 for k in labels)


def test_refinement_preserves_meaning_better_than_pca_alone():
    emb = _embeddings()
    labels = sorted(emb["vectors"])
    import tools.graph_export as ge  # noqa: E402
    raw = ge.pca2(emb["vectors"], labels)
    refined = ge.refine(raw, emb["vectors"], iters=30)
    before = ge.projection_quality(raw, emb["vectors"], sample=200)["pearson"]
    after = ge.projection_quality(refined, emb["vectors"], sample=200)["pearson"]
    assert after >= before, (before, after)


def test_neighbours_in_meaning_land_close_together():
    emb = _embeddings()
    labels = sorted(emb["vectors"])
    import tools.graph_export as ge  # noqa: E402
    pos = ge.refine(ge.pca2(emb["vectors"], labels), emb["vectors"], iters=60)
    def d(a, b):
        return ((pos[a][0] - pos[b][0]) ** 2 + (pos[a][1] - pos[b][1]) ** 2) ** 0.5
    assert d("gateway", "plugin") < d("gateway", "porosity")
    assert d("evaluation", "verdict") < d("evaluation", "thermal")


def test_semantic_view_draws_concepts_only(tmp_path, monkeypatch):
    """A session has no semantic position; it must not be placed somewhere false."""
    _ledger(tmp_path, monkeypatch)
    import tools.graph_export as ge  # noqa: E402
    data = graph.snapshot()
    emb_path = tmp_path / "emb.json"
    emb_path.write_text(json.dumps({"model": "test", "dim": 3,
                                    "vectors": {"shipper": [1.0, 0, 0], "ledger": [0.9, 0.1, 0]}}))
    embeddings = json.loads(emb_path.read_text())
    nodes, packed = ge.semantic_layout(data, embeddings)
    assert nodes and all(n["kind"] == "concept" for n in nodes)
    assert all(e["relation"] == "near_in_meaning" for e in packed["edges"])


def test_the_semantic_export_writes_all_three_artefacts(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    emb = tmp_path / "emb.json"
    emb.write_text(json.dumps({"model": "test", "dim": 3,
                               "vectors": {"shipper": [1.0, 0, 0], "ledger": [0.9, 0.1, 0]}}))
    out = tmp_path / "graph"
    result = subprocess.run([sys.executable, str(ROOT / "tools/graph_export.py"),
                             "--limit", "40", "--semantic", "--embeddings", str(emb),
                             "--out", str(out)],
                            capture_output=True, text=True, timeout=120,
                            env={**os.environ, "ANTEMUSE_STATES_HOME": str(tmp_path)})
    assert result.returncode == 0, result.stderr[-400:]
    assert (out / "concept-semantic.png").exists()
    assert "<circle" in (out / "concept-semantic.svg").read_text()
    assert json.loads((out / "concept-semantic.json").read_text())["layout"] == "semantic"


def test_without_embeddings_the_semantic_view_says_so(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    out = tmp_path / "graph"
    result = subprocess.run([sys.executable, str(ROOT / "tools/graph_export.py"),
                             "--semantic", "--embeddings", str(tmp_path / "absent.json"),
                             "--out", str(out)],
                            capture_output=True, text=True, timeout=120,
                            env={**os.environ, "ANTEMUSE_STATES_HOME": str(tmp_path)})
    assert result.returncode == 1
    assert "graph_embed" in result.stdout
