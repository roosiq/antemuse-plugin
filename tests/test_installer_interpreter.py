"""The installer must not blame the network for a missing module.

Real failure on a Windows build: `hermes plugins validate --install-deps` installed nltk into
Hermes's own venv while `install.py` probed a *different* python (a tools interpreter beside a
staged runtime venv). The old code took validate's exit status as proof, then reported
`nltk corpus download failed (network?)` — a label claiming a cause it never established, and one
that sends people to check their connection for a two-interpreter split.

Two rules came out of that, and these tests pin them: the probe decides, not the exit status; and
a failure says which of the two things actually broke.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE = "import nltk"


def _installer():
    spec = importlib.util.spec_from_file_location("am_install", ROOT / "scripts" / "install.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in ("say", "ok", "warn"):
        setattr(mod, name, lambda *a, **k: None)
    return mod


def _deps(monkeypatch, mod, probes, validate=True, pip=True):
    """probes: what `import nltk` answers, in order. Returns the commands that ran."""
    answers = list(probes)
    calls = []

    def fake_run(cmd, dry=False, quiet=False):
        calls.append(" ".join(str(c) for c in cmd) if not isinstance(cmd, str) else cmd)
        text = calls[-1]
        if PROBE in text:
            return answers.pop(0) if answers else True
        if "--install-deps" in text:
            return validate
        if "pip" in text:
            return pip
        return True

    monkeypatch.setattr(mod, "run", fake_run)
    return calls


def test_validate_exiting_zero_is_not_proof_the_plugin_can_import(monkeypatch):
    """validate installs into its own venv; the probed interpreter must be fixed anyway."""
    mod = _installer()
    # probe fails, validate claims success, re-probe still fails, pip runs, re-probe passes
    calls = _deps(monkeypatch, mod, [False, False, True], validate=True, pip=True)
    mod.ensure_deps("/fake/tools/python", dry=False)

    pips = [c for c in calls if "pip" in c and "/fake/tools/python" in c]
    assert pips, f"the probed interpreter must receive the package; ran {calls}"


def test_validate_success_with_a_working_probe_needs_no_pip(monkeypatch):
    """If validate did land the packages where the plugin looks, don't install twice."""
    mod = _installer()
    calls = _deps(monkeypatch, mod, [False, True], validate=True)
    mod.ensure_deps("/fake/tools/python", dry=False)
    assert not [c for c in calls if "pip" in c], calls


def test_a_still_broken_interpreter_stops_the_install(monkeypatch):
    """No silent success: if the probe still fails after pip, the install stops and says so."""
    mod = _installer()
    _deps(monkeypatch, mod, [False, False, False], validate=True, pip=True)
    seen = []
    monkeypatch.setattr(mod, "die", lambda text: seen.append(text) or (_ for _ in ()).throw(SystemExit(1)))
    with pytest.raises(SystemExit):
        mod.ensure_deps("/fake/tools/python", dry=False)
    assert "still not importable" in seen[0], seen
    assert "/fake/tools/python" in seen[0], seen


def test_a_missing_module_is_not_reported_as_a_network_failure(monkeypatch):
    """The corpora step must name the missing module, never guess at connectivity."""
    mod = _installer()
    monkeypatch.setattr(mod, "run", lambda *a, **k: False)

    class Probe:
        returncode = 1
        stderr = "ModuleNotFoundError: No module named 'nltk'\n"

    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: Probe())
    monkeypatch.setattr(Path, "is_dir", lambda *a, **k: False)
    seen = []
    monkeypatch.setattr(mod, "die", lambda text: seen.append(text) or (_ for _ in ()).throw(SystemExit(1)))

    with pytest.raises(SystemExit):
        mod.ensure_corpora("/fake/tools/python", dry=False)

    assert seen, "a failed corpora step must stop the install"
    assert "network" not in seen[0].lower(), seen[0]
    assert "not importable" in seen[0], seen[0]
    assert "No module named 'nltk'" in seen[0], seen[0]


def test_a_real_download_failure_points_at_the_downloader(monkeypatch):
    """If nltk imports and the download still fails, say that — and give the command to see why."""
    mod = _installer()
    monkeypatch.setattr(mod, "run", lambda *a, **k: False)

    class Probe:
        returncode = 0
        stderr = ""

    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: Probe())
    monkeypatch.setattr(Path, "is_dir", lambda *a, **k: False)
    seen = []
    monkeypatch.setattr(mod, "die", lambda text: seen.append(text) or (_ for _ in ()).throw(SystemExit(1)))

    with pytest.raises(SystemExit):
        mod.ensure_corpora("/fake/tools/python", dry=False)

    assert "nltk.downloader" in seen[0], seen[0]
    assert "network" not in seen[0].lower(), seen[0]


def test_the_pane_dir_is_cleared_of_older_releases(tmp_path):
    """Third release in a row shipping stale bytes beside the new pane.

    The app owns `desktop-plugins/antemuse/`; 0.9.x left a scene3d.js, a vendor/, an art/ tree and
    a plugin.truncated.bak there. Copying plugin.js beside them looks like a clean install and is
    not one.
    """
    mod = _installer()
    pane = tmp_path / "desktop-plugins" / "antemuse"
    (pane / "vendor" / "react").mkdir(parents=True)
    (pane / "art").mkdir()
    (pane / "scene3d.js").write_text("// old\n")
    (pane / "plugin.truncated.bak").write_text("old bytes\n")
    (pane / "plugin.js").write_text("// current\n")
    (pane / ".hermes-package.json").write_text('{"package": "antemuse"}')

    gone = mod.clear_pane_dir(pane)

    assert sorted(gone) == ["art", "plugin.truncated.bak", "scene3d.js", "vendor"], gone
    assert (pane / "plugin.js").exists(), "the pane itself must survive"
    assert (pane / ".hermes-package.json").exists(), "the app's marker must survive"
    assert [c.name for c in pane.iterdir()] and sorted(c.name for c in pane.iterdir()) == \
        [".hermes-package.json", "plugin.js"]
