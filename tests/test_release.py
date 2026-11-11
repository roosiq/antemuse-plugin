"""The package a fresh Hermes install receives.

An install that half-works is worse than none: these tests pin the parts that are easy to lose —
the interpreter the dependencies must land in, the desktop copy the app actually loads, and the
evidence that must not ship.
"""
from __future__ import annotations

from pathlib import Path

from conftest import needs_bash  # noqa: E402

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
    for excluded in ("--exclude experiments", "--exclude evaluation"):
        assert excluded in text, excluded
    # tests/ is not excluded: see test_the_package_ships_its_tests
    # A package that cannot be installed is never produced.
    assert "plugins validate" in text


def test_the_projection_is_built_not_committed():
    """It holds 117k WordNet labels, so it cannot live in the repository (the retired-name rule
    forbids those words) — but a package without it draws a plain circle instead of the map.

    The earlier form of this test asserted the file does not exist, which was true of a checkout
    and false of the packed tree: on the shipped artifact it failed while the packer was doing
    exactly the right thing. The rule is direction-dependent, so the test is too.
    """
    build = (ROOT / "scripts" / "build-release.sh").read_text()
    assert "assets/projection" in build

    shipped = (ROOT / "assets" / "projection" / "wordnet.proj.json").exists()
    if (ROOT / ".git").exists():
        assert not shipped, "the projection must not be committed: build it into the package"
    else:
        assert shipped, "this tree is a package and must carry the projection"



@needs_bash()
def test_the_doctor_count_reads_the_number_the_doctor_printed():
    """A regex that matched zero digits once made a perfect install report "registered 0 hooks".
    The counter is a separate, sourced file now, so it can be exercised on its own."""
    import shlex
    import subprocess

    script = ROOT / "scripts" / "doctor_counts.sh"
    line = "  registrations: 1 tool(s), 8 hook(s)"

    def doctor_count(what: str, text: str = line) -> str:
        # The script goes in on stdin, never as a path interpolated into the command: a WindowsPath
        # reads `C:\...\doctor_counts.sh` inside bash -c, which bash cannot source.
        prog = script.read_text() + "\ndoctor_count " + shlex.quote(text) + " " + what + "\n"
        out = subprocess.run(["bash", "-s"], input=prog, capture_output=True,
                             text=True, check=True).stdout
        return out.strip()

    count = doctor_count

    assert count("tool") == "1"
    assert count("hook") == "8"
    # and it does not invent a number when there is none
    assert count("hook", "nothing here") == ""


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


def test_the_desktop_half_is_one_file():
    """`desktop/` shipped 1.9 MB of dead bytes: a three.js vendor tree, a scene3d.js nobody
    imported, a plugin.truncated.bak, and a baked art/ folder the pane never reads.

    `install.py` copied the whole directory into `plugins/antemuse/`, and the app's own
    reconciler does `fs.cp(source.dir, staged, {recursive:true})` — so the junk was copied twice
    and clearing the destination was pointless while the source stayed dirty. What ships is what
    gets re-materialized, so the source has to be one file.
    """
    desktop = ROOT / "desktop"
    assert [p.name for p in desktop.iterdir()] == ["plugin.js"], \
        f"desktop/ carries more than the pane: {sorted(p.name for p in desktop.iterdir())}"
    size = (desktop / "plugin.js").stat().st_size
    assert size < 200_000, f"the pane is {size} bytes; that is not a single file's worth"


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


def test_the_package_ships_its_tests():
    """Evidence travels with the artifact.

    The packer used to exclude `tests/`, so an independent verifier on another machine could not
    check any behavioural claim — the fixes had to be reproduced by hand against the engine. That
    is a decision, not a side effect, and this pins it.
    """
    build = (ROOT / "scripts" / "build-release.sh").read_text()
    assert "--exclude tests" not in build
    assert ",tests," not in build and ",tests}" not in build


def test_the_build_prunes_what_validation_leaves_inside_the_stage():
    """A source lock, not a proof of the artifact.

    0.10.15 shipped 104 .pyc files and a walk cursor, and the exclusions could not catch them:
    `hermes plugins validate` imports the staged package, which writes __pycache__ into the stage
    *after* the copy. The prune has to happen after the gate. What this test can assert here is
    that the build still does that — the artifact itself is checked by building it.
    """
    script = (ROOT / "scripts" / "build-release.sh").read_text()
    gate = script.index("hermes plugins validate")
    # rindex: the fallback branch has the same command earlier, before the gate
    prune = script.rindex('find "$STAGE" -name __pycache__ -prune -exec rm -rf')
    assert prune > gate, "the prune must come after validation, or it prunes a clean tree"
    assert 'die "the staged tree still carries build residue' in script, \
        "the build must fail rather than ship residue"
    for junk in (".pytest_cache", ".antemuse"):
        assert junk in script, f"{junk} is not excluded from the package"


def test_the_catalog_entry_travels_with_what_it_describes():
    """The submission artifact cannot be missing from the submission."""
    entry = ROOT / "plugin-catalog" / "antemuse.yaml"
    assert entry.exists(), "no catalog entry: the catalog PR would have nothing to copy"
    import yaml

    held = yaml.safe_load(entry.read_text())
    manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())
    assert held["version"] == manifest["version"], (held["version"], manifest["version"])
    assert len(str(held["sha"])) == 40, held["sha"]
    assert held["platforms"] == manifest["platforms"], (held["platforms"], manifest["platforms"])
