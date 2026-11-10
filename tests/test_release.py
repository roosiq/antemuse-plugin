"""The package a fresh Hermes install receives.

An install that half-works is worse than none: these tests pin the parts that are easy to lose —
the interpreter the dependencies must land in, the desktop copy the app actually loads, and the
evidence that must not ship.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_installer_puts_the_dependencies_where_hermes_reads():
    text = (ROOT / "scripts" / "install.sh").read_text()
    # Hermes' own interpreter, followed through its launcher — a guess here installs pillow into
    # an environment the plugin never imports from.
    assert "hermes_python()" in text
    assert "plugins validate" in text and "--install-deps" in text
    assert 'nltk.download' in text
    assert "desktop-plugins/antemuse" in text
    assert ".hermes-package.json" in text
    assert "wordnet.proj" in text
    assert "scan_sessions" in text


def test_the_release_ships_runtime_only():
    text = (ROOT / "scripts" / "build-release.sh").read_text()
    for excluded in ("--exclude experiments", "--exclude evaluation", "--exclude tests"):
        assert excluded in text, excluded
    # A package that cannot be installed is never produced.
    assert "plugins validate" in text


def test_the_projection_is_bundled_so_the_picture_is_semantic():
    assert (ROOT / "assets" / "projection" / "wordnet.proj.json").is_file()
    assert (ROOT / "assets" / "projection" / "wordnet.proj.f16").is_file()
