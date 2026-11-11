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

from conftest import needs_symlinks  # noqa: E402

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

    class _Engine:
        @staticmethod
        def watch_state():
            return {"active": active, "residue": [], "journal": []}

    _Core = type("_Core", (), {"engine": _Engine})
    _Plugin = type("_Plugin", (), {"core": _Core})
    monkeypatch.setattr(api, "plugin", lambda: _Plugin())
    return api


def _walk_api(monkeypatch, tmp_path):
    """The backend route with a live walk and its ledger. No pictures: there is one renderer."""
    api = load("plugin_api")
    from core import storage
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    monkeypatch.setattr(storage, "data_dir", lambda: tmp_path)

    active = {"active": {"key": "walk", "origin": {"session_id": "s-live"}}, "residue": [], "journal": []}

    class _Engine:
        @staticmethod
        def watch_state():
            return active

    _Core = type("_Core", (), {"engine": _Engine})
    _Plugin = type("_Plugin", (), {"core": _Core})
    monkeypatch.setattr(api, "plugin", lambda: _Plugin())
    return api


def test_a_fresh_install_draws_the_ground_with_nothing_lit(monkeypatch, tmp_path):
    api = _walk_api(monkeypatch, tmp_path)
    monkeypatch.setattr(api, "plugin", lambda: type("P", (), {"core": type("C", (), {
        "engine": type("Eng", (), {"watch_state": staticmethod(lambda: {"active": None})})})()})())
    # No state, and a ledger with no servings. The ground is still the truth — the concept space
    # exists, nothing is lit — and a blank pane is what made a first run look broken.
    payload = api.state(cols=40, rows=12, session="fresh", with_graph=1)
    assert payload["picture"] == "pane"
    assert payload["graph"]["lit"] == 0, "nothing fired, so nothing is lit"


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
        "engine": type("Eng", (), {"watch_state": staticmethod(lambda: {"active": None})}),
        })()})())
    now = 1_760_000_000.0
    for i, label in enumerate(["gateway", "plugin", "ledger", "shipper"]):
        history.notice(label, move="walk", session="desk-1", at=now - i, ref=str(i))

    payload = api.state(cols=40, rows=12, session="desk-1", with_graph=1)
    assert payload["picture"] == "pane"
    assert payload["graph"]["nodes"], "the ground is drawn with nothing lit"


@needs_symlinks()
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

    assert payload["picture"] == "pane"


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
        assert payload["picture"] == "pane", ("a bare-module load still has to find core", payload)
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
        assert payload["picture"] == "pane", payload
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


def test_a_state_with_no_owner_lights_the_pane():
    """A walk entered from the app has no session; its firings must still reach the pane.

    graph() fell back to the pane's own session id when the active state had no owner, so a
    running walk served nine concepts and the pane lit two. Empty owner means everyone.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import dashboard.plugin_api as api
    from core import engine, history

    engine.enter("walk", minutes=5, session="")
    history.notice("doorstop", move="walk", session="")

    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/antemuse")
    client = TestClient(app)

    body = client.get("/api/plugins/antemuse/state?graph=1&stills=0&session=some-pane-session").json()
    lit = [n for n in body["graph"]["nodes"] if n["w"] > 0.05]
    assert lit, "a walk that served a concept must light it"
    assert any(n["l"] == "doorstop" for n in lit)
    engine.exit() if hasattr(engine, "exit") else None


def test_a_walk_reports_its_path_in_order():
    """The firings are a set; the path is a sequence. The route has to say which order it walked.

    Without this the pane can only light points, and a walk reads as a scatter of lit concepts
    rather than a route out from the task and back.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import dashboard.plugin_api as api
    from core import engine, walks

    engine.enter("walk", minutes=5, session="")
    walk = walks.get("outer")
    for _ in range(3):
        walk.step(1)

    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/antemuse")
    body = TestClient(app).get("/api/plugins/antemuse/state?graph=1&stills=0").json()

    path = body["graph"]["path"]
    assert len(path) >= 2, "a walk that stepped has a path"
    # order, not membership: a hop the projection cannot place has no node to draw through, and
    # that is a coverage limit, not a wrong path
    assert path[-1] != path[-2]


def test_the_map_carries_the_relations_it_has():
    """Edges must be relations the ledger recorded, not geometry the pane invented.

    The pane drew k-nearest neighbours in the projection, so an edge could carry activation only
    when two points happened to be near each other. Client code needs the relations itself.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import dashboard.plugin_api as api
    from core import engine, history

    engine.enter("walk", minutes=5, session="")
    # two concepts sighted in the same message: that is the co-occurrence an edge is evidence of
    history.notice("doorstop", ref="m-1")
    history.notice("bookend", ref="m-1")
    # another test in the suite may have memoised a payload built before this ledger existed
    api._GRAPH_MEMO.clear() if hasattr(api, "_GRAPH_MEMO") else None
    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/antemuse")
    body = TestClient(app).get("/api/plugins/antemuse/state?graph=1&stills=0").json()

    links = body["graph"]["links"]
    assert links, "a ledger that has served concepts has co-occurrences"
    assert {"a", "b", "w"} <= set(links[0])
    top = links[0]["w"]
    assert top >= links[-1]["w"], "strongest relation first"
    assert top >= 1


def test_entering_a_state_is_not_hidden_by_the_memo():
    """The graph memo cached "profile" and kept serving it for three seconds after /walk.

    A state entered right after a poll looked like no state at all — the pane's own label said
    profile while the walk was running.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import dashboard.plugin_api as api
    from core import engine

    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/antemuse")
    client = TestClient(app)
    api._GRAPH_MEMO.clear() if hasattr(api, "_GRAPH_MEMO") else None

    engine.exit() if hasattr(engine, "exit") else None
    before = client.get("/api/plugins/antemuse/state?graph=1&stills=0").json()["graph"]["key"]
    engine.enter("walk", minutes=5, session="")
    after = client.get("/api/plugins/antemuse/state?graph=1&stills=0").json()["graph"]["key"]

    assert before == "profile"
    assert after == "walk", "a state entered a moment after a poll must show up at once"


def test_a_new_serving_is_not_hidden_by_the_memo():
    """The memo cached three seconds of the map and did not know the ledger had moved.

    A walk that stepped between two polls kept showing the picture from before the step.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import dashboard.plugin_api as api
    from core import engine, history, walks

    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/antemuse")
    client = TestClient(app)
    api._GRAPH_MEMO.clear() if hasattr(api, "_GRAPH_MEMO") else None

    engine.enter("walk", minutes=5, session="")
    first = client.get("/api/plugins/antemuse/state?graph=1&stills=0").json()["graph"]["lit"]

    walks.get("outer").step(1)
    history.notice("doorstop", move="walk", session="")

    second = client.get("/api/plugins/antemuse/state?graph=1&stills=0").json()["graph"]["lit"]
    assert second > first, "a serving between polls must show up on the next poll"


def test_a_node_carries_how_often_it_was_met():
    """Size is volume, colour is activation — two different questions.

    The pane drew every dot at the activation weight, so a concept the user keeps returning to was
    drawn exactly like one seen once. `v` is appearances across the ledger, sqrt-scaled: a concept
    met 400 times is not 400 times bigger.
    """
    from dashboard import plugin_api

    # Take labels the map actually shows (the ground is the ledger's busiest concepts), then give
    # two of them very different histories. Seeding arbitrary words proves nothing: they are not on
    # the map, so their volume never reaches a node.
    first = plugin_api.graph(limit=200)
    labels = [n["l"] for n in (first.get("nodes") or [])][:40]
    assert len(labels) >= 2, "the map is empty"

    from core import history
    conn = history._connect()
    assert conn is not None
    with conn:
        for label, times in ((labels[0], 40), (labels[1], 1)):
            cur = conn.execute(
                "INSERT OR IGNORE INTO concepts(kind,key,label,first_seen,last_seen,times) "
                "VALUES('term',?,?,0,0,?)", (label, label, times))
            cid = cur.lastrowid or conn.execute(
                "SELECT id FROM concepts WHERE key = ?", (label,)).fetchone()[0]
            for i in range(times):
                conn.execute("INSERT INTO appearances(concept_id, source, ref, at) "
                             "VALUES(?,?,?,0)", (cid, "message", f"v{i}"))
            conn.execute("INSERT INTO served(concept_id, move, session, at) VALUES(?,?,?,0)",
                         (cid, "walk", "volume-test"))
    conn.close()
    plugin_api._GRAPH_MEMO.clear()      # the payload is memoised per state and ledger stamp

    payload = plugin_api.graph(limit=200)
    by_label = {n["l"]: n for n in payload["nodes"]}
    heavy, light = by_label[labels[0]], by_label[labels[1]]
    assert "v" in heavy and "v" in light, "every node must say how often it was met"
    assert 0.0 <= float(light["v"]) < float(heavy["v"]) <= 1.0, (heavy["v"], light["v"])
    assert float(heavy["v"]) == pytest.approx(1.0, abs=0.01), heavy["v"]
    assert all(0.0 <= float(n["v"]) <= 1.0 for n in payload["nodes"])


def test_the_pane_sizes_a_dot_by_volume_and_colours_it_by_activation():
    js = (Path(__file__).resolve().parent.parent / "desktop" / "plugin.js").read_text()
    assert "attribute float aV" in js, "the pane must receive volume"
    assert "gl_PointSize = (2.2 + 6.5*aV) * (1.0 + 0.7*aW)" in js, \
        "size must come from volume, with activation as a modest multiplier"
    # the falloff is bounded, or the wide shot crushes every dot to a pixel and volume cannot show
    assert "(9.0 / max(2.5, p.w))" in js
    assert "vW = aW" in js, "colour still comes from activation"


def test_an_idle_pane_names_the_state_that_just_ended():
    """The corner said "no state" over a map still drawing a walk's firings.

    A state that finishes leaves a report in the residue and its firings keep decaying in the
    ledger, so the pane draws that picture for a few more minutes. With nothing naming it, the
    lights looked like the empty pane inventing concepts. The state's name is enough.
    """
    payload = project({"active": None, "journal": [],
                       "residue": [{"kind": "report", "state": "walk",
                                    "text": "walk 3m · 6 hop(s)", "turns_left": 2}]})
    assert payload["last"] == {"state": "walk"}
    # the account's own words stay in the chat: a surface that prints counts and names does not
    # print what the state said
    assert "6 hop" not in json.dumps(payload)


def test_an_idle_pane_with_no_account_has_no_last_state():
    payload = project({"active": None, "journal": [], "residue": [{"kind": "walk"}]})
    assert "last" not in payload


def test_the_empty_pane_says_what_starts_one():
    """A dark map with "no state" in the corner is a dead end: nothing to read, nothing to do."""
    import subprocess

    import pytest

    root = Path(__file__).resolve().parents[1]
    js = (root / "desktop" / "plugin.js").read_text()
    copy_src = js[js.index("const copy = {"):js.index("}", js.index("const copy = {")) + 1]
    start = js.index("export function whyFailed(err) {")
    end = js.index("\n}\n", js.index("export function viewModel(")) + 3
    fns = js[start:end].replace("export function", "function")
    harness = copy_src + "\n" + fns + """
const idleAlone = viewModel({active: null, residue: {count: 0, kinds: []}}, null)
const idleAfter = viewModel({active: null, last: {state: 'walk'}, residue: {count: 1, kinds: ['report']}}, null)
const running = viewModel({active: {key: 'walk', label: 'WALKING', seconds_left: 145, dose: 6,
  unit: 'hops', served: 3, tools: {mode: 'all'}, contract: 'work continues'}, residue: {count: 0, kinds: []}}, null)
const failed = viewModel(null, new Error('404 Not Found'))
console.log([idleAlone.note, idleAfter.note, running.note, failed.note].join('|'))
"""
    path = root / "tests" / "_empty_pane_probe.mjs"
    path.write_text(harness)
    try:
        done = subprocess.run(["node", str(path)], capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        path.unlink(missing_ok=True)
        pytest.skip("node is not installed here")
    path.unlink(missing_ok=True)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == (
        # One command, not a menu: the label above the note already says there is no state, and
        # the copy's own comment gives that as the reason. The ended case names the state and
        # the one line that starts another.
        "/walk starts one|walk ended · /walk again||"
    ), done.stdout
