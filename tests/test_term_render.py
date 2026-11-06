"""The live renderer: three.js software-rasterised into terminal pixels."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "tools", "term_scene.cjs")
NODE = shutil.which("node")


def _ready() -> bool:
    return bool(NODE) and os.path.exists(SCRIPT) and os.path.isdir(os.path.join(ROOT, "node_modules", "three"))


@pytest.mark.skipif(not _ready(), reason="node or the renderer's packages are missing")
@pytest.mark.parametrize("scene", ["walk", "dream", "daydream", "doomscroll"])
def test_every_scene_renders_light(scene):
    out = subprocess.run(
        [NODE, SCRIPT, "--scene", scene, "--cols", "80", "--rows", "20", "--debug"],
        capture_output=True, text=True, timeout=90, cwd=ROOT,
    )
    assert out.returncode == 0, out.stderr
    lit = int(out.stderr.strip().split("lit=")[-1])
    assert lit > 100, f"{scene} rendered almost nothing: {lit} lit pixels"


@pytest.mark.skipif(not _ready(), reason="node or the renderer's packages are missing")
def test_a_frame_is_truecolor_half_blocks(tmp_path):
    ppm = tmp_path / "frame.ppm"
    subprocess.run(
        [NODE, SCRIPT, "--scene", "walk", "--cols", "40", "--rows", "12", "--ppm", str(ppm)],
        check=True, capture_output=True, timeout=90, cwd=ROOT,
    )
    data = ppm.read_bytes()
    assert data.startswith(b"P6")
    width, height = data.split(b"\n")[1].split()
    assert int(width) > 20 and int(height) > 10


@pytest.mark.skipif(not _ready(), reason="node or the renderer's packages are missing")
def test_scene_switch_is_written_where_the_renderer_looks(tmp_path, monkeypatch):
    from kitchen import tui
    monkeypatch.setattr(tui.store, "data_dir", lambda: tmp_path)
    tui._write_scene("dream")
    import json
    assert json.loads((tmp_path / "scene.json").read_text())["scene"] == "dream"
