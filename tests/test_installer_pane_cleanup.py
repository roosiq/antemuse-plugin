"""The installer may clear its own debris, never somebody else's file.

0.11.16's ``clear_pane_dir`` removed everything in ``desktop-plugins/antemuse`` except the pane and
the app's marker. An upgrade therefore deleted a file a person had put there. The rule now: known
legacy names are removed, unknown names are left and reported.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _installer():
    path = Path(__file__).resolve().parent.parent / "scripts" / "install.py"
    spec = importlib.util.spec_from_file_location("antemuse_install_probe", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_an_unknown_file_survives_an_upgrade(tmp_path):
    inst = _installer()
    pane_dir = tmp_path / "desktop-plugins" / "antemuse"
    pane_dir.mkdir(parents=True)
    (pane_dir / "plugin.js").write_text("// pane")
    (pane_dir / ".hermes-package.json").write_text("{}")
    (pane_dir / "custom-note.txt").write_text("mine")

    gone = inst.clear_pane_dir(pane_dir)

    assert (pane_dir / "custom-note.txt").read_text() == "mine", "an unknown file was deleted"
    assert (pane_dir / "plugin.js").exists(), "the pane was removed"
    assert (pane_dir / ".hermes-package.json").exists(), "the app marker was removed"
    assert gone == [], f"claimed to clear files it did not own: {gone}"


def test_known_legacy_debris_is_removed(tmp_path):
    inst = _installer()
    pane_dir = tmp_path / "pane"
    pane_dir.mkdir()
    (pane_dir / "plugin.js").write_text("// pane")
    for name in ("scene3d.js", "plugin.truncated.bak"):
        (pane_dir / name).write_text("old")
    (pane_dir / "vendor").mkdir()
    (pane_dir / "vendor" / "three.js").write_text("old")
    (pane_dir / "art").mkdir()

    gone = inst.clear_pane_dir(pane_dir)

    assert sorted(gone) == ["art", "plugin.truncated.bak", "scene3d.js", "vendor"]
    assert (pane_dir / "plugin.js").exists()
    assert not (pane_dir / "vendor").exists()
