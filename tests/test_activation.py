"""Activations: what is firing now, how it decays, and a picture with no words in it."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT))
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))

from core import activation, history  # noqa: E402

NOW = 1_760_000_000.0


def _serve(tmp_path, monkeypatch, label, at, session="s1", move="walk"):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    history.notice(label, move=move, session=session, at=at, ref=str(int(at)))


def test_a_concept_served_now_is_at_full_weight(tmp_path, monkeypatch):
    _serve(tmp_path, monkeypatch, "shipper", NOW)
    act = activation.activations("s1", move="walk", now=NOW)
    assert act["shipper"]["weight"] == 1.0


def test_weight_halves_over_the_half_life(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    history.notice("shipper", move="walk", session="s1", at=NOW - activation.HALF_LIFE_S)
    history.notice("ledger", move="walk", session="s1", at=NOW)          # the reference
    act = activation.activations("s1", move="walk", now=NOW)
    assert 0.45 <= act["shipper"]["weight"] <= 0.55, act


def test_nothing_cools_below_the_floor(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    history.notice("shipper", move="walk", session="s1", at=NOW - 20 * activation.HALF_LIFE_S)
    history.notice("ledger", move="walk", session="s1", at=NOW)
    act = activation.activations("s1", move="walk", now=NOW)
    assert "shipper" not in act


def test_a_serving_that_has_not_happened_yet_is_not_active(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    history.notice("future", move="walk", session="s1", at=NOW + 600)
    assert activation.activations("s1", move="walk", now=NOW) == {}


def test_repetition_does_not_outrank_recency(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    for i in range(20):                                   # said all day, not now
        history.notice("habit", move="walk", session="s1", at=NOW - 3600 - i, ref=f"h{i}")
    history.notice("fresh", move="walk", session="s1", at=NOW, ref="f1")
    act = activation.activations("s1", move="walk", now=NOW)
    assert act["fresh"]["weight"] == 1.0
    assert "habit" not in act


def test_a_move_narrows_the_map_to_that_state(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    history.notice("walker", move="walk", session="s1", at=NOW, ref="1")
    history.notice("dreamer", move="dream", session="s1", at=NOW, ref="2")
    assert set(activation.activations("s1", move="walk", now=NOW)) == {"walker"}
    assert set(activation.activations("s1", now=NOW)) == {"walker", "dreamer"}


def test_the_sequence_uses_real_moments_and_every_frame_has_activity(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    for i in range(6):
        history.notice("concept", move="walk", session="s1", at=NOW + i * 60, ref=str(i))
        history.notice("other", move="walk", session="s1", at=NOW + i * 60, ref=f"o{i}")
    frames = activation.sequence("s1", "walk", steps=6)
    assert len(frames) == 6
    assert all(f["activations"] for f in frames), [len(f["activations"]) for f in frames]
    assert [f["at"] for f in frames] == sorted(f["at"] for f in frames)


def test_an_unknown_session_is_an_empty_map(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    assert activation.activations("nope") == {}
    assert activation.sequence("nope") == []
    assert activation.summary([]) == {"frames": 0, "concepts": 0}


def test_the_picture_carries_no_words(tmp_path, monkeypatch):
    """The human card is a picture. A renderer that draws text has broken that rule."""
    source = (ROOT / "tools" / "activation_render.py").read_text()
    assert ".text(" not in source
    assert "ImageFont" not in source


def test_the_strip_and_the_gif_are_written(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    for i in range(4):
        for j in range(3):
            history.notice(f"term{i}{j}", move="walk", session="s1",
                           at=NOW + i * 90, ref=f"{i}-{j}")
    import json, random
    rng = random.Random(4)
    vectors = {f"term{i}{j}": [rng.uniform(-1, 1) for _ in range(8)] for i in range(4) for j in range(3)}
    emb = tmp_path / "emb.json"
    emb.write_text(json.dumps({"model": "test", "dim": 8, "vectors": vectors}))
    out = tmp_path / "act"
    result = subprocess.run([sys.executable, str(ROOT / "tools/activation_render.py"),
                             "--session", "s1", "--move", "walk", "--frames", "4",
                             "--size", "320x200", "--gif", "--embeddings", str(emb),
                             "--out", str(out)],
                            capture_output=True, text=True, timeout=180,
                            env={**os.environ, "ANTEMUSE_STATES_HOME": str(tmp_path)})
    assert result.returncode == 0, (result.stdout[-300:], result.stderr[-300:])
    assert (out / "s1-strip.png").stat().st_size > 2000
    assert (out / "s1.gif").exists()


def test_a_state_with_no_servings_says_so(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "tools/activation_render.py"),
                             "--move", "walk", "--out", str(tmp_path / "x")],
                            capture_output=True, text=True, timeout=120,
                            env={**os.environ, "ANTEMUSE_STATES_HOME": str(tmp_path)})
    assert result.returncode == 1
    assert "nothing recorded" in result.stdout or "no state servings" in result.stdout


# ---------------------------------------------------------------- as glyphs

def test_the_map_draws_only_ramp_characters_and_fills_the_grid(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    for i, label in enumerate(["gateway", "plugin", "ledger", "shipper"]):
        history.notice(label, move="walk", session="s1", at=NOW + i, ref=str(i))
    rows = activation.art(cols=40, rows=9, session="s1", move="walk", now=NOW + 10)
    assert len(rows) == 9
    assert all(len(r) == 40 for r in rows)
    assert set("".join(rows)) <= set(activation.RAMP), set("".join(rows))


def test_the_glyphs_carry_rank_not_one_letter_for_everything(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    for i in range(12):
        history.notice(f"term{i}", move="walk", session="s1", at=NOW + i, ref=str(i))
    rows = activation.art(cols=60, rows=12, session="s1", move="walk", now=NOW + 12)
    drawn = set("".join(rows)) - {" "}
    assert len(drawn) >= 3, drawn


def test_nothing_firing_is_an_empty_picture_not_a_blank_one(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    assert activation.art(cols=40, rows=8, session="s1") == []
    assert activation.art(cols=40, rows=8, session="") == []


def test_the_same_ledger_draws_the_same_picture(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    for i in range(6):
        history.notice(f"term{i}", move="walk", session="s1", at=NOW + i, ref=str(i))
    a = activation.art(cols=50, rows=10, session="s1", move="walk", now=NOW + 6)
    b = activation.art(cols=50, rows=10, session="s1", move="walk", now=NOW + 6)
    assert a == b


def test_the_surface_falls_back_when_nothing_is_firing(tmp_path, monkeypatch):
    """An empty field is not a picture of a state: the baked scene draws instead."""
    from core import storage, surfaces
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    monkeypatch.setattr(storage, "load", lambda: {"active": None, "key": ""}, raising=False)
    rows = surfaces.art(cols=40, rows=8, scene="activation")
    assert rows == [] or all(set(r) <= set(" .:-=+*#%@") for r in rows)
