"""The pane's payload is counts and glyphs — never the material a model reads.

The leak this guards against is not hypothetical: the state dict the model is
given carries ``directive``, and the engine's projection also carries a journal.
Handing either to a pane would put state machinery on a human surface, which is
exactly what the wordless-card rule exists to prevent. So the payload's keys are
asserted, not merely reviewed.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


def load(name: str):
    spec = importlib.util.spec_from_file_location(
        f"antemuse_test_{name}", DASHBOARD / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


projection = load("projection")
project = projection.project
tools_of = projection.tools_of

WALK = {
    "active": {
        "key": "walk", "walk": "wander", "label": "WALKING",
        "contract": "work continues · the frame is elsewhere",
        "directive": "SECRET MODEL INSTRUCTION",
        "ends_at": 1000.0, "seconds_left": 145, "total_seconds": 180, "turns_left": 4,
        "tools": None,
    },
    "journal": [{"kind": "walk", "text": "salt→ski parka [far]"}],
    "residue": [{"kind": "walk", "text": "residue line"}],
    "now": 855.0,
}


def test_idle_reports_nothing_running():
    payload = project({"active": None, "residue": [], "journal": []}, [], now=5.0)
    assert payload["active"] is None
    assert payload["generated_at"] == 5.0
    assert payload["frame"] == {"cols": 44, "rows": 12, "lines": []}
    assert payload["residue"] == {"count": 0, "kinds": []}


def test_active_state_reports_counts_and_contract():
    payload = project(WALK, ["line one"], now=855.0)
    active = payload["active"]
    assert active["key"] == "walk"
    assert active["label"] == "WALKING"
    assert active["seconds_left"] == 145
    assert active["total_seconds"] == 180
    assert active["turns_left"] == 4
    assert active["contract"] == "work continues · the frame is elsewhere"
    assert payload["frame"]["lines"] == ["line one"]
    assert payload["residue"] == {"count": 1, "kinds": ["walk"]}


def test_payload_never_carries_the_directive_or_the_journal():
    payload = project(WALK, [], now=855.0)
    dumped = json.dumps(payload)
    assert "SECRET MODEL INSTRUCTION" not in dumped
    assert "ski parka" not in dumped
    assert "directive" not in payload["active"]
    assert "journal" not in payload


def test_no_forbidden_key_appears_anywhere_including_nested():
    payload = project(WALK, ["a line"], now=1.0)
    found = set()

    def walk(value, path=""):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in projection.FORBIDDEN:
                    found.add(f"{path}/{key}")
                walk(item, f"{path}/{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")

    walk(payload)
    assert found == set()


def test_tools_are_free_by_default_and_policy_only_when_asked():
    """A state is an aside: the panel says tools are open unless the entry closed them."""
    assert tools_of(None) == {"mode": "free", "allowed": [], "blocked": []}
    assert tools_of([]) == {"mode": "free", "allowed": [], "blocked": []}
    assert tools_of(["web_search"], block=True) == {
        "mode": "some", "allowed": ["web_search"], "blocked": []
    }
    assert tools_of(None, block=True)["mode"] == "all"
    assert tools_of([], block=True)["mode"] == "none"
    narrowed = tools_of(["web_search", "read_file"], block=True, allow=["read_file"])
    assert narrowed == {"mode": "some", "allowed": ["read_file"], "blocked": []}


def test_residue_kinds_are_deduplicated_and_legacy_is_named():
    payload = project(
        {"active": None, "residue": [{"kind": "walk"}, {"kind": "walk"}, "an old string"], "journal": []}
    )
    assert payload["residue"] == {"count": 3, "kinds": ["legacy", "walk"]}


def test_a_missing_frame_is_an_empty_frame_not_an_error():
    payload = project({"active": WALK["active"], "residue": [], "journal": []}, None)
    assert payload["frame"]["lines"] == []


def test_the_route_is_declared_at_state():
    """The desktop half calls ctx.rest('/state'); the route must exist by that name."""
    api = pytest.importorskip("fastapi")  # noqa: F841 -- skip when the server env is absent
    module = load("plugin_api")
    paths = {route.path for route in module.router.routes}
    assert "/state" in paths


def test_a_surface_may_ask_for_a_larger_grid():
    """A 700x746 pane can hold ~87x53 cells; the chat card still asks for 44x12."""
    payload = project(WALK, ["x"], cols=87, rows=53)
    assert payload["frame"]["cols"] == 87
    assert payload["frame"]["rows"] == 53


def test_an_out_of_range_grid_is_clamped_not_refused():
    """A surface that misreports its size should still get a frame."""
    assert project(WALK, [], cols=5000, rows=5000)["frame"] | {} == {
        "cols": projection.MAX_COLS, "rows": projection.MAX_ROWS, "lines": []
    }
    small = project(WALK, [], cols=1, rows=1)["frame"]
    assert (small["cols"], small["rows"]) == (projection.MIN_COLS, projection.MIN_ROWS)


def test_a_nonsense_grid_falls_back_to_the_card_default():
    """'abc' is not a size; the chat card default is the safe answer."""
    frame = project(WALK, [], cols="abc", rows=None)["frame"]
    assert (frame["cols"], frame["rows"]) == (projection.FRAME_COLS, projection.FRAME_ROWS)


def test_frames_advance_on_a_clock_per_state():
    """The strip is baked; the pane animates by asking which frame is now."""
    api = load("plugin_api")
    walk = [api.frame_index("walk", now=100 + i) for i in range(13)]
    doom = [api.frame_index("doomscroll", now=100 + i) for i in range(13)]
    assert len(set(walk)) > 1 and len(set(doom)) > 1
    assert all(0 <= i < 8 for i in walk + doom)
    # a doomscroll moves faster than a walk: more distinct frames in the same second
    assert len(set(doom)) > len(set(walk))
    assert api.frame_index("walk", frames=0) == 0
    # deterministic: the same clock answers the same frame twice
    assert api.frame_index("dream", now=1234.5) == api.frame_index("dream", now=1234.5)

# --- the pane is never blank -------------------------------------------------

def _idle_api(monkeypatch, active=None):
    """The backend route, with a watch that has no active state."""
    api = load("plugin_api")
    from core import screensaver

    class _Panel:
        @staticmethod
        def engine_state():
            return {"active": active, "residue": [], "journal": []}

    # type() rather than a class body: a class body cannot close over the local
    # `screensaver`, it just raises NameError.
    _Core = type("_Core", (), {"panel": _Panel, "screensaver": screensaver})
    _Plugin = type("_Plugin", (), {"core": _Core})

    monkeypatch.setattr(api, "plugin", lambda: _Plugin())
    return api


def test_idle_pane_paints_an_ambient_scene(monkeypatch):
    """Outside a state the pane still draws: `no state` is a label, not a blank box."""
    api = _idle_api(monkeypatch)
    payload = api.state(cols=40, rows=12)
    lines = payload["frame"]["lines"]
    assert len(lines) == 12, "the pane asked for 12 rows"
    assert all(len(line) == 40 for line in lines), "every row is the width asked for"
    assert any(ch not in " ." for line in lines for ch in line), "ambient art, not an empty field"
    assert payload["active"] is None, "an ambient scene is not a state"


def test_busy_changes_only_the_scene(monkeypatch):
    """`?busy=1` picks `work`; it never fabricates an active state or moves a count."""
    api = _idle_api(monkeypatch)
    idle = api.state(cols=40, rows=12)
    work = api.state(cols=40, rows=12, busy=True)
    assert work["active"] is None
    assert work["residue"] == idle["residue"]
    assert work["frame"]["cols"] == idle["frame"]["cols"]
    assert work["frame"]["lines"] != idle["frame"]["lines"], "work is a different scene"


def test_ambient_frame_is_deterministic_and_sized(monkeypatch):
    """A given moment renders identically at whatever grid a surface asks for."""
    from core import screensaver
    a = screensaver.frame("idle", 116, 74, now=1000.0)
    b = screensaver.frame("idle", 116, 74, now=1000.0)
    assert a == b
    assert len(a) == 74 and all(len(row) == 116 for row in a)
    ink = sum(1 for row in a for ch in row if ch not in " .")
    assert 0.02 < ink / (74 * 116) < 0.08, "visible, not a smear (measured 3.7%)"


# --- the pane shows the activation map ---------------------------------------

def _walk_api(monkeypatch, tmp_path):
    """The backend route with a live walk, its ledger, and stills on disk."""
    api = load("plugin_api")
    from core import screensaver, storage
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    monkeypatch.setattr(storage, "data_dir", lambda: tmp_path)

    active = {"active": {"key": "walk", "origin": {"session_id": "s-live"}}, "residue": [], "journal": []}

    class _Panel:
        @staticmethod
        def engine_state():
            return active

    _Core = type("_Core", (), {"panel": _Panel, "screensaver": screensaver})
    _Plugin = type("_Plugin", (), {"core": _Core})
    monkeypatch.setattr(api, "plugin", lambda: _Plugin())
    return api


def test_a_live_state_serves_stills_and_the_route_serves_them(monkeypatch, tmp_path):
    api = _walk_api(monkeypatch, tmp_path)
    still = tmp_path / "activation" / "walk" / "f0-1.jpg"
    still.parent.mkdir(parents=True)
    still.write_bytes(b"\xff\xd8\xff\xd9")

    payload = api.state(cols=40, rows=12, session="s-live")
    assert payload["stills"] == ["/api/plugins/antemuse/art/walk/f0-1.jpg"]

    response = api.art("walk", "f0-1.jpg")
    assert getattr(response, "media_type", "") == "image/jpeg"
    assert getattr(response, "path", "") == str(still)


def test_the_art_route_refuses_anything_it_did_not_write(monkeypatch, tmp_path):
    """A refusal is a 404, not a 200 with a body about it."""
    from fastapi import HTTPException
    api = _walk_api(monkeypatch, tmp_path)
    for name, filename in (("walk", "../../state.json"), ("walk", "notes.txt"),
                           ("../..", "state.json"), ("walk", "missing.jpg")):
        try:
            api.art(name, filename)
        except HTTPException as exc:
            assert exc.status_code == 404, (name, filename)
        else:
            raise AssertionError(f"{name}/{filename} was not refused")


def test_no_state_means_no_stills(monkeypatch, tmp_path):
    api = _walk_api(monkeypatch, tmp_path)
    monkeypatch.setattr(api, "plugin", lambda: type("P", (), {"core": type("C", (), {
        "panel": type("Pan", (), {"engine_state": staticmethod(lambda: {"active": None})}),
        "screensaver": __import__("core.screensaver", fromlist=["x"])})()})())
    assert api.state(cols=40, rows=12)["stills"] == []


def test_stills_are_written_for_a_state_with_servings(monkeypatch, tmp_path):
    from core import activation_stills, history
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    now = 1_760_000_000.0
    for i, label in enumerate(["gateway", "plugin", "ledger", "shipper", "walk"]):
        history.notice(label, move="walk", session="s1", at=now - i, ref=str(i))
    emb = tmp_path / "emb.json"
    import json, random
    rng = random.Random(2)
    emb.write_text(json.dumps({"model": "t", "dim": 6, "vectors": {
        label: [rng.uniform(-1, 1) for _ in range(6)]
        for label in ["gateway", "plugin", "ledger", "shipper", "walk"]}}))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    (tmp_path / "antemuse").mkdir(exist_ok=True)
    (tmp_path / "antemuse" / "embeddings.json").write_text(emb.read_text())

    paths = activation_stills.stills(move="walk", session="s1", dest=tmp_path / "stills", now=now)
    assert len(paths) == activation_stills.STILL_COUNT
    assert all(p.exists() and p.stat().st_size > 1000 for p in paths)
    assert all(p.suffix == ".jpg" for p in paths)


def test_stills_stop_when_nothing_is_firing(monkeypatch, tmp_path):
    from core import activation_stills
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    assert activation_stills.stills(move="walk", session="nobody", dest=tmp_path / "x") == []


def test_the_pane_paints_stills_before_baked_art():
    """The wiring, checked at the source: the surface must prefer what the backend served, and
    fall back to the baked scene when there is nothing to show."""
    js = (Path(__file__).resolve().parents[1] / "desktop" / "plugin.js").read_text()
    assert "applyActivation(p && p.stills)" in js
    assert "if (!applyActivation(p && p.stills)) applyScene(key)" in js
    assert "stills = urls.slice()" in js
