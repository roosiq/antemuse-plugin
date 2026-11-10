"""The pane's payload is counts and glyphs — never the material a model reads.

The leak this guards against is not hypothetical: the state dict the model is
given carries ``directive``, and the engine's projection also carries a journal.
Handing either to a pane would put state machinery on a human surface, which is
exactly what the wordless-card rule exists to prevent. So the payload's keys are
asserted, not merely reviewed.
"""
from __future__ import annotations

import pathlib

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
    assert payload["files"] == [still.as_uri()]

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


def test_a_fresh_install_draws_the_ground_with_nothing_lit(monkeypatch, tmp_path):
    api = _walk_api(monkeypatch, tmp_path)
    monkeypatch.setattr(api, "plugin", lambda: type("P", (), {"core": type("C", (), {
        "panel": type("Pan", (), {"engine_state": staticmethod(lambda: {"active": None})}),
        "screensaver": __import__("core.screensaver", fromlist=["x"])})()})())
    # No state, and a ledger with no servings. The ground is still the truth — the concept space
    # exists, nothing is lit — and a blank pane is what made a first run look broken.
    payload = api.state(cols=40, rows=12, session="fresh")
    assert payload["stills"], payload.get("still_note")
    assert payload["still_note"] == ""


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


def test_stills_with_nothing_firing_light_nothing(monkeypatch, tmp_path):
    """A frame with no firings is drawn, and it must not invent a lit node to look busy."""
    from core import activation_stills
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    paths = activation_stills.stills(move="walk", session="nobody", dest=tmp_path / "x")
    assert paths, "an empty ledger still draws the ground"

    from PIL import Image

    lit = 0
    for path in paths:
        px = Image.open(path).convert("RGB").getdata()
        # the amber core is (255, 214, 126); nothing that bright may appear with nothing firing
        lit += sum(1 for r, g, b in px if r > 220 and g > 180)
    assert lit == 0, f"a frame lit {lit} pixels with nothing firing"


def test_the_pane_paints_stills_before_baked_art():
    """The wiring, checked at the source: the surface must prefer what the backend served, and
    fall back to the baked scene when there is nothing to show."""
    js = (Path(__file__).resolve().parents[1] / "desktop" / "plugin.js").read_text()
    # Every leg is offered and tried in turn. Picking one up front meant a 404 on the absolute
    # URL hid the file:// leg that would have painted the map.
    assert "const legs = []" in js
    assert "if (p && p.files_http && p.files_http.length) legs.push(p.files_http)" in js
    assert "if (p && p.files && p.files.length) legs.push(p.files)" in js
    assert "for (const leg of legs) {" in js
    assert "if (await fromB64(p && p.stills_b64)) return" in js
    assert "if (!tryLive(key)) clearLayers()" in js
    assert "stills = urls.slice()" in js


def test_the_pane_can_reach_stills_without_the_gateway():
    """The desktop pane is a file:// page: it cannot fetch the REST URL, so it reads the files the
    backend baked, and falls back to the baked scene when there are none."""
    js = (Path(__file__).resolve().parents[1] / "desktop" / "plugin.js").read_text()
    assert "plugin-data/antemuse/activation/" in js
    assert "probe.onerror" in js and "clearLayers()" in js
    assert "AMDBG" not in js, "no debug hooks left in the pane"


def test_stills_carry_an_absolute_url_for_a_remote_desktop(monkeypatch, tmp_path):
    """A remote desktop shows the pane on another computer, where a file:// path means nothing:
    the payload has to carry a URL the browser can actually fetch."""
    pytest.importorskip("httpx")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from core import activation_stills, history

    api = _walk_api(monkeypatch, tmp_path)
    now = 1_760_000_000.0
    for i, label in enumerate(["gateway", "plugin", "ledger", "shipper"]):
        history.notice(label, move="walk", session="s1", at=now - i, ref=str(i))
    api.plugin = lambda: type("P", (), {"core": type("C", (), {
        "panel": type("Pan", (), {"engine_state": staticmethod(lambda: {
            "active": {"key": "walk", "origin": {"session_id": "s1"}, "ends_at": now + 600},
            "session": "s1"})}),
        "screensaver": __import__("core.screensaver", fromlist=["x"])})()})()

    app = FastAPI()
    app.include_router(api.router)
    body = TestClient(app).get("/state?session=s1").json()
    assert body["files_http"], body.get("still_note")
    assert all(u.startswith("http://testserver/api/plugins/antemuse/art/walk/") for u in body["files_http"])


def test_the_stills_also_travel_as_bytes_for_a_remote_pane(monkeypatch, tmp_path):
    """A remote pane is a file:// page: it cannot fetch the route as an <img> and has no path on
    the host. The same stills come back over the RPC it already uses, as base64."""
    pytest.importorskip("httpx")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from core import storage

    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    api = _walk_api(monkeypatch, tmp_path)
    still = storage.data_dir() / "activation" / "walk" / "f0.jpg"
    still.parent.mkdir(parents=True, exist_ok=True)
    still.write_bytes(b"\xff\xd8\xff\xd9" + b"0" * 2000)

    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    body = client.get("/art_b64/walk/f0.jpg").json()
    assert body["type"] == "image/jpeg"
    assert len(body["data"]) > 2000
    # and the guard is the same as the byte route's
    assert client.get("/art_b64/walk/../../state.json").status_code == 404
    assert client.get("/art_b64/walk/state.json").status_code == 404


def test_the_activation_is_the_only_picture(monkeypatch, tmp_path):
    """No baked scenes: a state with nothing firing shows nothing, rather than stand-in art for a
    moment that did not happen. The activation of the concept graph is the whole visualization."""
    js = (Path(__file__).resolve().parents[1] / "desktop" / "plugin.js").read_text()
    assert "applyScene" not in js
    assert "./art/" not in js
    assert "BAKED" not in js
    assert "clearLayers()" in js


def test_the_map_is_drawn_when_no_state_is_running(monkeypatch, tmp_path):
    """The pane's whole surface is the map. Showing the app's own artwork between states made the
    plugin look broken ("I still see the wrong viz") when it was working."""
    from core import history

    api = _walk_api(monkeypatch, tmp_path)
    monkeypatch.setattr(api, "plugin", lambda: type("P", (), {"core": type("C", (), {
        "panel": type("Pan", (), {"engine_state": staticmethod(lambda: {"active": None})}),
        "screensaver": __import__("core.screensaver", fromlist=["x"])})()})())
    now = 1_760_000_000.0
    for i, label in enumerate(["gateway", "plugin", "ledger", "shipper"]):
        history.notice(label, move="walk", session="desk-1", at=now - i, ref=str(i))

    payload = api.state(cols=40, rows=12, session="desk-1")
    assert payload["stills"], payload.get("still_note")


def test_the_router_finds_core_when_the_host_imports_it_as_a_package(monkeypatch, tmp_path):
    """The host imports this router as `<plugin>.dashboard.plugin_api`, and a bare `from core
    import ...` raises ImportError there — swallowed, it told the pane "nothing firing" while the
    ledger had plenty, so the picture never appeared. This test loads the router the way the host
    does and demands stills."""
    import importlib
    import sys as _sys

    from core import history

    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    now = 1_760_000_000.0
    for i, label in enumerate(["gateway", "plugin", "ledger", "shipper", "walk"]):
        history.notice(label, move="walk", session="desk-1", at=now - i, ref=str(i))

    link = tmp_path / "as_a_package"
    link.mkdir()
    (link / "pkg").symlink_to(ROOT)
    _sys.path.insert(0, str(link))
    try:
        mod = importlib.import_module("pkg.dashboard.plugin_api")
        payload = mod.state(cols=40, rows=12, session="desk-1")
    finally:
        _sys.path.remove(str(link))
        for name in [n for n in _sys.modules if n == "pkg" or n.startswith("pkg.")]:
            _sys.modules.pop(name, None)

    assert payload["stills"], payload.get("still_note")
    assert payload["stills_b64"]


def test_a_still_that_was_never_post_processed_is_still_reachable(monkeypatch, tmp_path):
    """Without playwright the drawn frames stay in `<state>/base/`, and the routes used to look
    only at `<state>/` — so every URL `/state` advertised 404'd and the pane painted nothing. That
    is the "wrong viz" on a machine that has no bake step."""
    from pathlib import Path

    from core import storage

    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    root = Path(storage.data_dir()) / "activation" / "profile"
    (root / "base").mkdir(parents=True, exist_ok=True)
    (root / "base" / "f0-1760000000-post.jpg").write_bytes(b"\xff\xd8jpeg-bytes")

    api = _walk_api(monkeypatch, tmp_path)
    resolved = api._still_path("profile", "f0-1760000000-post.jpg")
    assert resolved is not None and resolved.parent.name == "base"

    body = api.art_b64("profile", "f0-1760000000-post.jpg")
    assert body["type"] == "image/jpeg" and body["data"]

    # and a name that is nowhere is still a refusal, not a 200 with a body about it
    try:
        api.art_b64("profile", "f9-1760000000-post.jpg")
    except Exception as exc:  # HTTPException
        assert getattr(exc, "status_code", None) == 404
    else:
        raise AssertionError("a missing still must refuse")


def test_every_path_state_advertises_is_one_the_routes_can_serve(monkeypatch, tmp_path):
    """/state and /art must agree. The pane's first leg is the absolute URL, so a URL that 404s
    costs the whole picture on any machine where that leg is first."""
    from core import history

    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    now = 1_760_000_000.0
    for i, label in enumerate(["gateway", "plugin", "ledger", "shipper", "walk"]):
        history.notice(label, move="walk", session="desk-1", at=now - i, ref=str(i))

    api = _walk_api(monkeypatch, tmp_path)
    payload = api.state(cols=40, rows=12, session="desk-1")
    assert payload["stills"], payload.get("still_note")
    for url in payload["stills"] + payload["stills_b64"]:
        parts = url.rsplit("/", 2)
        name, filename = parts[-2], parts[-1]
        assert api._still_path(name, filename) is not None, url

def test_the_router_finds_core_when_the_host_loads_it_as_a_bare_module(tmp_path):
    """The third load shape: no package parent and no plugin root on sys.path.

    The gateway recovered from `ModuleNotFoundError: No module named 'core'` by naming the failure
    in `still_note` — which is how it was finally caught — but it still served no picture. The
    router has to find `core` itself when neither relative nor flat import works.
    """
    import importlib.util
    import sys

    repo = pathlib.Path(__file__).resolve().parent.parent
    target = repo / "dashboard" / "plugin_api.py"
    saved = {k: v for k, v in sys.modules.items() if k == "core" or k.startswith("core.")}
    for key in saved:
        del sys.modules[key]
    saved_path = list(sys.path)
    for entry in [str(repo), str(repo / "dashboard")]:
        while entry in sys.path:
            sys.path.remove(entry)
    try:
        spec = importlib.util.spec_from_file_location("plugin_api_probe", target)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = module.state()
        assert payload["still_note"] == "", payload["still_note"]
        assert payload["stills"], "a bare-module load still has to find core"
    finally:
        sys.path[:] = saved_path
        sys.modules.update(saved)

def test_a_foreign_core_module_cannot_hide_the_plugins_own():
    """`core` is a generic name: something else may already own it.

    The gateway may have imported an unrelated `core` (another plugin, a stray directory on the
    path) before this router loads. Trusting `sys.modules['core']` or plain path order would then
    serve the wrong package — or fail — so the loader must take the plugin's own directory.
    """
    import importlib.util
    import sys
    import types

    repo = pathlib.Path(__file__).resolve().parent.parent
    target = repo / "dashboard" / "plugin_api.py"
    foreign = types.ModuleType("core")
    foreign.__file__ = "/tmp/elsewhere/core/__init__.py"
    saved = {k: v for k, v in sys.modules.items() if k == "core" or k.startswith("core.")}
    for key in saved:
        del sys.modules[key]
    sys.modules["core"] = foreign
    try:
        spec = importlib.util.spec_from_file_location("plugin_api_foreign", target)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = module.state()
        assert payload["still_note"] == "", payload["still_note"]
        assert payload["stills"]
    finally:
        sys.modules.pop("core", None)
        sys.modules.update(saved)

def test_the_graph_route_serves_real_positions_and_lights_only_what_fired():
    """/graph is the same map the stills draw, as numbers: no invented node, no invented light."""
    import importlib.util
    import sys

    repo = pathlib.Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("pa_graph", repo / "dashboard" / "plugin_api.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = module.graph(session="", limit=400)
    assert payload["plugin"], payload.keys()
    nodes = payload["nodes"]
    assert nodes, "the profile has servings, so the ground cannot be empty"
    assert len(nodes) <= 400
    for n in nodes[:50]:
        assert isinstance(n["l"], str) and n["l"]
        assert all(isinstance(n[k], float) for k in ("x", "y", "z"))
        assert 0.0 <= n["w"] <= 1.0
    # brightest last: a poll must not reshuffle the draw order of equal weights
    weights = [n["w"] for n in nodes]
    assert weights == sorted(weights)
    assert payload["lit"] == sum(1 for n in nodes if n["w"] > 0.05)



def test_the_pane_names_the_failure_it_actually_saw():
    """A failed poll is not automatically a missing route.

    An expired session, a slow server and an absent route all arrive as one rejected promise. The
    pane used to print "the plugin backend is not mounted" for every one of them, which sent us
    looking for a mount that was there. Each cause now answers with its own words, and only a 404
    is allowed to claim the route is missing.
    """
    import subprocess

    root = Path(__file__).resolve().parents[1]
    js = (root / "desktop" / "plugin.js").read_text()
    start = js.index("export function whyFailed(err) {")
    end = js.index("\n}", start) + 2
    fn = js[start:end].replace("export function", "function")
    copy_src = js[js.index("const copy = {"):js.index("}", js.index("const copy = {")) + 1]
    # The label is what the pane prints; viewModel must route the failure through whyFailed.
    vm_start = js.index("export function viewModel(payload, error) {")
    vm_end = js.index("\n}", vm_start) + 2
    vm_fn = js[vm_start:vm_end].replace("export function", "function")
    harness = copy_src + "\n" + fn + "\n" + vm_fn + """
const cases = [
  ['signin', new Error('401: {"reason":"no_cookie"}')],
  ['signin', new Error('Error: 403 Forbidden')],
  ['mount', new Error('Error: 404 Not Found')],
  ['silent', new Error('Timed out connecting to Hermes backend after 5000ms')],
  ['silent', new Error('503 Service Unavailable')],
  ['other', new Error('boom')]
]
const out = cases.map(([want, err]) => {
  const said = whyFailed(err)
  const ok = want === 'signin' ? said === 'sign-in required'
    : want === 'mount' ? said === 'the plugin backend is not mounted'
    : want === 'silent' ? said === 'the backend did not answer'
    : said === 'backend unavailable'
  return ok ? 'ok' : 'WRONG ' + said
})
console.log(out.join(','))
"""
    harness_path = root / "tests" / "_whyfailed_probe.mjs"
    harness_path.write_text(harness)
    try:
        done = subprocess.run(["node", str(harness_path)], capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        harness_path.unlink(missing_ok=True)
        import pytest
        pytest.skip("node is not installed here")
    harness_path.unlink(missing_ok=True)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == ",".join(["ok"] * 6), done.stdout
    # A failed poll must print its cause where a person reads it, not the generic category.
    assert "copy.unavailable : active" not in js, "the label still answers every failure with one category"
    assert "label: error ? whyFailed(error)" in js


def test_the_map_rides_the_route_that_was_always_mounted():
    """`/graph` is a new path, and a path exists only in the process that booted after it.

    That cost hours of the pane polling a route its backend had never mounted. The map is now also
    a parameter of `/state` — the one route every backend has carried since the first release — so
    the pane can get real positions from a host started long before this code landed.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import dashboard.plugin_api as api

    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/antemuse")
    client = TestClient(app)

    plain = client.get("/api/plugins/antemuse/state").json()
    assert "graph" not in plain

    seeded = client.get("/api/plugins/antemuse/state?graph=1").json()
    assert "graph" in seeded
    nodes = seeded["graph"]["nodes"]
    assert isinstance(nodes, list)
    for node in nodes[:5]:
        assert set(node) >= {"l", "x", "y", "z", "w"}
        assert 0.0 <= node["w"] <= 1.0
    # The two doors must hand back the same map, or one of them is lying.
    direct = client.get("/api/plugins/antemuse/graph?limit=1400").json()
    assert len(nodes) == len(direct["nodes"])
    assert seeded["graph"]["lit"] == direct["lit"]


def test_numbers_only_skips_the_picture_it_would_never_show():
    """A 3D surface polls for the map, not for a JPEG.

    Rendering one frame is ~1.9 s of image work. Paying that on every poll is what made a route
    that answers in 134 ms time out at 12 s once a turn was running, so `?stills=0` skips the whole
    image path and returns the numbers alone.
    """
    import time

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import dashboard.plugin_api as api

    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/antemuse")
    client = TestClient(app)

    started = time.time()
    lean = client.get("/api/plugins/antemuse/state?graph=1&stills=0").json()
    took = time.time() - started
    # The keys exist in the base payload as empty lists; the point is that no frame was rendered.
    assert not lean.get("stills") and not lean.get("stills_b64")
    assert lean["graph"]["nodes"], "the map must still be there"
    assert took < 3.0, f"numbers-only took {took:.1f}s"

    full = client.get("/api/plugins/antemuse/state").json()
    assert "stills" in full
