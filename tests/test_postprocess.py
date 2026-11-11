"""The bake-time post-process: three.js changes the look of a still, never its content."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT))

_PAGE = ROOT / "tools" / "activation_post.html"


def _still(path: Path, dots: int = 14) -> None:
    """A still like the one the map draws: dark, with light on it."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (960, 600), (4, 4, 6))
    draw = ImageDraw.Draw(img)
    for i in range(dots):
        x, y = 90 + (i * 61) % 780, 70 + (i * 47) % 460
        draw.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(240, 190, 110))
    img.save(path, quality=90)


def _module():
    spec = importlib.util.spec_from_file_location("pp", ROOT / "tools" / "postprocess_activation.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_page_runs_the_official_composer():
    """It must be a three.js post-process, not a filter written to look like one."""
    html = _PAGE.read_text()
    for name in ("EffectComposer", "RenderPass", "UnrealBloomPass", "ShaderPass",
                 "RGBShiftShader", "OutputPass"):
        assert name in html, name
    assert "vendor/three-bake/three.module.js" in html


def test_the_page_draws_no_words():
    """A caption would make the picture a diagram."""
    html = _PAGE.read_text()
    assert "fillText" not in html
    assert "TextGeometry" not in html


def test_postprocessing_is_optional_and_named_when_missing():
    module = _module()
    reason = module.available()
    assert reason is None or isinstance(reason, str)


def test_nothing_to_do_returns_nothing():
    module = _module()
    assert module.apply([]) == []


def test_a_still_comes_back_post_processed(tmp_path):
    """Given a real still, the composer returns a JPEG of the same size — and the original stays."""
    module = _module()
    if module.available():
        import pytest
        pytest.skip("post-processing unavailable: " + str(module.available()))
    base = tmp_path / "f0.jpg"
    _still(base)
    from PIL import Image
    out = module.apply([base], size=(960, 600), timeout=120)
    assert out and out[0].exists(), out
    assert out[0].name == "f0-post.jpg"
    with Image.open(out[0]) as img:
        assert img.size == (960, 600)
    assert base.exists(), "post-processing must not consume the still it read"


def test_the_stills_path_prefers_the_processed_picture(tmp_path, monkeypatch):
    """When the composer runs, the surface is served the processed stills."""
    from core import activation_stills, history
    module = _module()
    if module.available():
        import pytest
        pytest.skip("post-processing unavailable: " + str(module.available()))
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    now = 1_760_000_000.0
    labels = ["gateway", "plugin", "ledger", "shipper", "walk"]
    for i, label in enumerate(labels):
        history.notice(label, move="walk", session="s1", at=now - i, ref=str(i))
    import json, random
    rng = random.Random(2)
    (tmp_path / "antemuse").mkdir(exist_ok=True)
    (tmp_path / "antemuse" / "embeddings.json").write_text(json.dumps(
        {"model": "t", "dim": 6, "vectors": {l: [rng.uniform(-1, 1) for _ in range(6)] for l in labels}}))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    paths = activation_stills.stills(move="walk", session="s1", dest=tmp_path / "stills", now=now)
    assert paths, "a state with servings has stills"
    assert all(p.name.endswith("-post.jpg") for p in paths), [p.name for p in paths]
    assert all(p.parent == tmp_path / "stills" for p in paths), "served from the state folder"

    again = activation_stills.fresh(move="walk", session="s1", dest=tmp_path / "stills")
    assert [p.name for p in again] == [p.name for p in paths], "cached, not re-rendered"


def test_a_state_with_no_servings_of_its_own_draws_the_session(tmp_path, monkeypatch):
    """A walk entered a minute ago has no `walk` servings yet; the session's firings are still
    what is on the map, and an empty field would be a lie about the picture."""
    from core import activation_stills, history
    module = _module()
    if module.available():
        import pytest
        pytest.skip("post-processing unavailable: " + str(module.available()))
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    now = 1_760_000_000.0
    labels = ["gateway", "plugin", "ledger", "shipper"]
    for i, label in enumerate(labels):
        history.notice(label, move="session", session="s1", at=now - i, ref=str(i))
    import json, random
    rng = random.Random(5)
    (tmp_path / "antemuse").mkdir(exist_ok=True)
    (tmp_path / "antemuse" / "embeddings.json").write_text(json.dumps(
        {"model": "t", "dim": 6, "vectors": {l: [rng.uniform(-1, 1) for _ in range(6)] for l in labels}}))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    paths = activation_stills.stills(move="walk", session="s1", dest=tmp_path / "s", now=now)
    assert len(paths) == activation_stills.STILL_COUNT, paths


def test_stills_are_written_under_predictable_names(tmp_path, monkeypatch):
    """A file:// page cannot list a directory, so the stills also land at f0.jpg..f2.jpg."""
    from core import activation_stills, history
    module = _module()
    if module.available():
        import pytest
        pytest.skip("post-processing unavailable: " + str(module.available()))
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    now = 1_760_000_000.0
    labels = ["gateway", "plugin", "ledger", "shipper"]
    for i, label in enumerate(labels):
        history.notice(label, move="walk", session="s1", at=now - i, ref=str(i))
    import json, random
    rng = random.Random(7)
    (tmp_path / "antemuse").mkdir(exist_ok=True)
    (tmp_path / "antemuse" / "embeddings.json").write_text(json.dumps(
        {"model": "t", "dim": 6, "vectors": {l: [rng.uniform(-1, 1) for _ in range(6)] for l in labels}}))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    dest = tmp_path / "walk"
    activation_stills.stills(move="walk", session="s1", dest=dest, now=now)
    for i in range(activation_stills.STILL_COUNT):
        stable = dest / f"f{i}.jpg"
        assert stable.exists() and stable.stat().st_size > 2000, stable


def test_a_chat_nothing_was_served_in_still_draws_the_profile(tmp_path, monkeypatch):
    """A fresh desktop session has no firings of its own. An empty field reads as the plugin
    doing nothing, so the busiest chat's recent firings stand in for it."""
    from core import activation_stills, history
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path))
    now = 1_760_000_000.0
    for i, label in enumerate(["gateway", "plugin", "ledger", "shipper"]):
        history.notice(label, move="session", session="busy-chat", at=now - i, ref=str(i))
    dest = tmp_path / "stills"
    activation_stills._PEAK["n"] = 0
    paths = activation_stills.stills(move="walk", session="never-seen", dest=dest, now=now)
    assert len(paths) == activation_stills.STILL_COUNT
    assert all(p.exists() and p.stat().st_size > 2000 for p in paths), paths


def test_the_camera_goes_to_what_just_fired_then_back_to_the_walk():
    """Two beats: a firing is an event, and a walk is a sequence.

    The pane must punch in on a concept the moment it lights and hold there — an event you have
    to hunt for in 1,400 points is not an event. But a camera that only ever punches in never
    shows the walk: filmed, a whole walk read as one node because every hop re-aimed the camera
    at distance 0.85 and the accumulating trail stayed outside the frame. So the dwell must
    release to the *path's* framing, not to the default wide shot. And none of it may fight a
    person who is dragging.
    """
    here = Path(__file__).resolve().parent.parent / "desktop" / "plugin.js"
    js = here.read_text()
    assert "focusTo = new Float32Array([go.x, go.y, go.z])" in js
    assert "distTo = 0.95" in js, "a firing still punches in"
    assert "if (fresh.length && !dragging)" in js
    # the release goes to the path, not to the origin at the default distance
    assert "pathDist = Math.max(1.3, Math.min(2.6, r * 3.0))" in js
    assert "distTo = pathDist" in js and "focusTo = new Float32Array([pathFocus[0]" in js
    # the focus point has to be applied to the view, or the camera just rotates
    assert "-focus[0], -focus[1], -focus[2]" in js


def test_the_firing_nodes_carry_their_names():
    """A firing you cannot name is a light. Only the firing set is labelled, and nothing overlaps.

    Labelling all 1,400 points would be a wall of text; labelling none leaves the pane decorative.
    """
    here = Path(__file__).resolve().parent.parent / "desktop" / "plugin.js"
    js = here.read_text()
    assert "const labelLayer" in js and "pointer-events:none;overflow:hidden" in js
    assert "const placeLabels = (MVP)" in js
    assert "(nodes[i].w || 0) > 0.05 && pts[i]" in js, "only firing nodes get a name"
    assert "if (k >= 9) break" in js, "a pane is not a word cloud"
    assert "clash" in js and "if (clash) continue" in js, "two names in one place is no name"
    # and the DOM layer is cleaned up with the surface
    assert "el.removeChild(labelLayer)" in js


def test_connections_carry_the_activation():
    """A firing must travel along relations, not sit there as a lone dot.

    Two kinds of edge carry it: a recorded relation incident to a firing node, and — because a
    walk serves one concept per message and so rarely has a recorded partner — proximity in the
    same projection the walk searches. Proximity is drawn dimmer, because it is not provenance.
    """
    here = Path(__file__).resolve().parent.parent / "desktop" / "plugin.js"
    js = here.read_text()
    assert "livePos" in js and "liveBuf" in js and "liveABuf" in js
    assert "const real = (links || [])" in js
    assert "gl.uniform3f(qColor, 1.0, 0.66, 0.34)" in js, "activation edges keep their own colour"
    assert "proximity is not provenance" in js
    assert "upload.liveN = live.length" in js
    # Carried activation is drawn as segments with per-vertex alpha, through the quad program.
    assert "segQuads(livePos, liveA, 0.3, 2.0 * dpr, MVP)" in js


def test_edges_are_quads_not_hairlines():
    """gl.LINES is one device pixel wide and ANGLE pins it there: relations vanished.

    A relation you cannot see is not drawn, so every edge class is expanded into camera-facing
    quads at a width in device pixels.
    """
    here = Path(__file__).resolve().parent.parent / "desktop" / "plugin.js"
    js = here.read_text()
    assert "const VS_QUAD" in js and "quadProg" in js
    assert "segQuads(edgePos, null, 0.26, 1.5 * dpr, MVP)" in js
    assert "segQuads(pathPos, pathA, 0.8, 2.4 * dpr, MVP)" in js
    # no edge class may fall back to lines
    assert "gl.drawArrays(gl.LINES" not in js, "an edge class still draws as a hairline"


def test_a_click_goes_to_the_node_and_holds():
    """The camera used to be owned entirely by whatever fired last.

    Navigation means: clicking a node takes the camera there and it stays while you look;
    empty space returns to the whole walk; `f` fits; the idle drift does not fight either.
    """
    here = Path(__file__).resolve().parent.parent / "desktop" / "plugin.js"
    js = here.read_text()
    assert "const gotoNode = (i) => {" in js
    assert "dwell = now() + 1e9" in js, "a held view must not be released by the dwell timer"
    assert "const fit = () => {" in js
    assert "if (i == null) { fit(); return }" in js, "empty space means show me the walk"
    assert "!dragging && !navLock" in js, "idle drift must not fight a held view"
    assert "canvas.addEventListener('keydown', onKey)" in js
    for key in ("arrowleft", "arrowup", "'f'", "escape"):
        assert key in js, key
