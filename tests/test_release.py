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


def test_the_projection_ships_from_the_cache_not_from_the_repository():
    """It holds 117k WordNet labels, so it cannot live in the tree (the retired-name rule forbids
    those words), but a package without it draws a plain circle instead of the semantic map."""
    build = (ROOT / "scripts" / "build-release.sh").read_text()
    assert "assets/projection" in build
    assert "wordnet.proj.json" in build
    assert not (ROOT / "assets" / "projection" / "wordnet.proj.json").exists()
