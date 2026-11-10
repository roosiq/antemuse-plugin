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


def test_the_doctor_count_reads_the_number_the_doctor_printed():
    """A regex that matched zero digits once made a perfect install report "registered 0 hooks".
    The counter is a separate, sourced file now, so it can be exercised on its own."""
    import subprocess

    script = ROOT / "scripts" / "doctor_counts.sh"
    line = "  registrations: 1 tool(s), 8 hook(s)"

    def count(what: str) -> str:
        out = subprocess.run(
            ["bash", "-c", f'. {script}; doctor_count "$1" {what}', "_", line],
            capture_output=True, text=True, check=True).stdout
        return out.strip()

    assert count("tool") == "1"
    assert count("hook") == "8"
    # and it does not invent a number when there is none
    out = subprocess.run(["bash", "-c", f'. {script}; doctor_count "$1" hook', "_", "nothing here"],
                         capture_output=True, text=True, check=True).stdout
    assert out.strip() == ""


def test_the_desktop_half_is_one_file_the_host_can_load():
    """The desktop loader accepts a single ES module importing only the plugin SDK and react.
    Anything else in that directory is either dead weight or — worse — an older pane's asset that
    an older copy of the module can still find, which is what "I still see the old viz" means."""
    js = (ROOT / "desktop" / "plugin.js").read_text()
    imports = [ln for ln in js.splitlines() if ln.startswith("import")]
    for line in imports:
        assert "from './" not in line and 'from "./' not in line, line
    assert "applyScene" not in js and "BAKED" not in js


def test_the_installer_does_not_take_ownership_of_the_app_s_directory():
    """`<home>/desktop-plugins/<name>/` belongs to the desktop app: it materializes the half and
    stamps `.hermes-package.json` with the fields it needs. Deleting the directory, or writing a
    marker by hand, makes the app's reconcile see something it did not make — and the pane can
    disappear from the sidebar."""
    text = (ROOT / "scripts" / "install.sh").read_text()
    install_step = text.split('say "4. desktop half')[1].split('5. projection')[0]
    assert "cp -f" in install_step
    assert "--delete" not in install_step
    assert "rm -rf \"$DESKTOP_DIR\"" not in install_step
    # it may only remove a marker it wrote itself, and only when that marker is the wrong shape
    assert '"package"' in install_step


def test_the_package_carries_no_baked_scenes():
    build = (ROOT / "scripts" / "build-release.sh").read_text()
    assert "desktop/art" in build


def test_the_installer_runs_where_hermes_runs():
    """The install used to be bash + rsync + cp + tar, which is Linux and macOS only.

    Hermes runs on Windows, so the installer must be Python: no shell, no external tools, no
    POSIX paths. The shell script stays as an entry point and nothing more.
    """
    root = Path(__file__).resolve().parent.parent
    py = (root / "scripts" / "install.py").read_text()
    sh = (root / "scripts" / "install.sh").read_text()

    assert "install.py" in sh, "the shell entry point must delegate"
    assert "exec " in sh
    # no external binaries the standard library already covers
    for tool in ('"rsync"', '"cp"', '"tar"', '"bash"'):
        assert tool not in py, f"{tool} is not available everywhere Hermes runs"
    # paths come from the environment, not from a POSIX assumption
    assert "HERMES_HOME" in py and "Path.home()" in py
    assert "shutil.copytree" in py, "copy with the standard library"
    # it has to compile on any platform
    compile(py, "install.py", "exec")


def test_the_e2e_does_not_shell_out_to_posix_tools():
    root = Path(__file__).resolve().parent.parent
    src = (root / "tools" / "e2e_install_walk.py").read_text()
    assert "tarfile.open" in src, "extract with the standard library"
    assert '"tar"' not in src and '"bash"' not in src
    assert "/home/" not in src and "/tmp/" not in src, "no hand-written host paths"
