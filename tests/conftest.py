"""Suite-wide isolation.

Two things must never leak between tests or into the person's own data:

- the plugin's data dir, which holds the state file and now the concept ledger;
- the automatic session scan, which starts a daemon thread and writes to both.

A test that wants either of them gets them explicitly. The exception is a test that renders
the *installed* frames — that is its subject, so it says so with `@pytest.mark.real_home`.
"""
from __future__ import annotations

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "real_home: this test reads the installed plugin data dir")


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch, request):
    if request.node.get_closest_marker("real_home"):
        yield
        return
    monkeypatch.setenv("ANTEMUSE_STATES_HOME", str(tmp_path / "antemuse-home"))
    (tmp_path / "antemuse-home").mkdir(exist_ok=True)
    yield


@pytest.fixture(autouse=True)
def _no_automatic_scan(monkeypatch):
    """Off by default: a scan that starts itself is not a test fixture.

    `tests/test_session_scan.py` deletes this to exercise the real thing.
    """
    monkeypatch.setenv("ANTEMUSE_NO_SCAN", "1")
    yield


def requires_tree(*names):
    """Skip a test that reads a repository-only tree, naming the reason.

    `installable package` and `author's checkout` are different artifacts on purpose: docs, specs,
    site and .git are not packed. A test that needs them must say so, because a collection error or
    an unexplained failure in the shipped tree makes the shipped tests worthless.
    """
    import pathlib

    import pytest

    root = pathlib.Path(__file__).resolve().parent.parent
    missing = [n for n in names if not (root / n).exists()]
    return pytest.mark.skipif(
        bool(missing), reason=f"needs {', '.join(missing)}: repository-only, not in the package")


def needs_bash():
    """A test that shells out to a bash script cannot run where bash is not installed."""
    import shutil

    import pytest

    return pytest.mark.skipif(shutil.which("bash") is None,
                              reason="needs bash on PATH (not installed on stock Windows)")


def needs_git():
    import shutil

    import pytest

    return pytest.mark.skipif(shutil.which("git") is None,
                              reason="needs git on PATH")


def needs_symlinks():
    """Windows refuses symlinks without Developer Mode or an elevated shell (WinError 1314)."""
    import sys
    import tempfile
    from pathlib import Path as _Path

    import pytest

    if not sys.platform.startswith("win"):
        return pytest.mark.skipif(False, reason="")
    ok = True
    try:
        with tempfile.TemporaryDirectory() as tmp:
            (_Path(tmp) / "a").write_text("x")
            (_Path(tmp) / "b").symlink_to(_Path(tmp) / "a")
    except (OSError, NotImplementedError):
        ok = False
    return pytest.mark.skipif(not ok, reason="symlinks need Developer Mode on Windows")
