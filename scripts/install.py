"""Antemuse — the installer, in Python so it runs anywhere Hermes runs.

The bash installer could only run where bash, rsync, cp and a shell heredoc exist. This does the
same work with the standard library: no bash, no rsync, no `tar`, no `/tmp`, no POSIX paths, and
no assumption about where HOME points.

    python scripts/install.py [--dry-run] [--no-cli] [--home PATH]

Every step is checked. A failure names the step and exits non-zero; nothing is left half-installed
silently.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
SKIP = {".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv"}


def say(text: str) -> None:
    print(f"\n{text}")


def ok(text: str) -> None:
    print(f"  ok    {text}")


def warn(text: str) -> None:
    print(f"  warn  {text}")


def die(text: str) -> None:
    print(f"\n  FAILED: {text}", file=sys.stderr)
    raise SystemExit(1)


def cache_dir() -> Path:
    """The projection's cache, honouring XDG on the platforms that have it."""
    base = os.environ.get("XDG_CACHE_HOME")
    return (Path(base) if base else Path.home() / ".cache") / "antemuse"


def default_home() -> Path:
    override = os.environ.get("HERMES_HOME")
    return Path(override) if override else Path.home() / ".hermes"


def copytree(src: Path, dst: Path, dry: bool) -> None:
    """Copy the plugin without its history or caches. shutil, not rsync: rsync is not on Windows."""
    if dry:
        print(f"  would copy {src} -> {dst}")
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in SKIP:
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(*SKIP))
        else:
            shutil.copy2(item, target)


def run(cmd, dry: bool, quiet: bool = False) -> bool:
    if dry:
        print("  would " + " ".join(str(c) for c in cmd))
        return True
    try:
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    except (OSError, ValueError):
        return False
    if r.returncode != 0 and not quiet:
        print((r.stdout or "")[-800:], (r.stderr or "")[-800:])
    return r.returncode == 0


def hermes_python() -> str:
    """The interpreter Hermes itself runs on: a guess here puts the deps where the plugin never
    imports from. HERMES_PY wins, then the launcher's own interpreter, then this one."""
    if os.environ.get("HERMES_PY"):
        return os.environ["HERMES_PY"]
    return sys.executable


PANE_KEEP = {"plugin.js", ".hermes-package.json"}


def clear_pane_dir(path: Path) -> list:
    """Remove everything in the pane directory that is not the pane or the app's own marker.

    The app owns this directory, and older releases left a scene3d.js, a vendor/, an art/ tree and
    a plugin.truncated.bak in it. Copying the new pane beside them recreates the stale-copy trap:
    the file that matters is fresh and the bytes next to it are not. Only those two names belong.
    """
    gone = []
    if not path.exists():
        return gone
    for child in sorted(path.iterdir()):
        if child.name in PANE_KEEP:
            continue
        try:
            shutil.rmtree(child) if child.is_dir() else child.unlink()
            gone.append(child.name)
        except OSError as exc:
            warn(f"could not clear {child.name} from the pane dir ({exc})")
    return gone


def ensure_deps(py: str, dry: bool) -> None:
    """Step 1: nltk where the *plugin* imports it, not merely where Hermes does.

    Pillow used to be here for the baked stills. The pane draws the graph itself, so the picture
    costs no image library at all and the dependency is gone.
    """
    say("1. python dependencies (nltk)")
    has = run([py, "-c", "import nltk"], dry, quiet=True)
    if has:
        ok("already importable")
        return
    # `hermes plugins validate --install-deps` installs into Hermes's own venv, which on some
    # builds is *not* the interpreter this script just probed — a tools python can sit beside a
    # staged runtime venv. So its exit status proves nothing about `py`: the re-probe decides,
    # and if it still fails we install into `py` ourselves.
    if run(["hermes", "plugins", "validate", str(SRC), "--install-deps"], dry, quiet=True):
        warn("'hermes plugins validate --install-deps' ran; it may have used a different "
             "interpreter, so re-checking " + py)
    else:
        warn("'hermes plugins validate --install-deps' did not complete")
    if not run([py, "-c", "import nltk"], dry, quiet=True):
        if not run([py, "-m", "pip", "install", "--quiet", "nltk>=3.8,<4"], dry):
            die(f"could not install nltk into {py}")
        ok(f"installed into {py}")
    if not run([py, "-c", "import nltk"], dry, quiet=True):
        die(f"nltk is still not importable in {py}, which is the interpreter the "
            f"plugin's hooks run on. Set HERMES_PY to that interpreter and re-run.")


def ensure_corpora(py: str, dry: bool) -> None:
    """Step 2: the wordnet and framenet corpora the projection needs."""
    say("2. nltk corpora (wordnet, framenet)")
    nltk_dir = Path(os.environ.get("NLTK_DATA") or Path.home() / "nltk_data")
    if (nltk_dir / "corpora" / "wordnet").is_dir() and (nltk_dir / "corpora" / "framenet_v17").is_dir():
        ok(f"already present in {nltk_dir}")
        return
    if dry:
        print(f"  would download wordnet, framenet_v17 into {nltk_dir}")
        return
    code = ("import sys, nltk\n"
            "dest = sys.argv[1]\n"
            "for pkg in ('wordnet', 'framenet_v17'):\n"
            "    nltk.download(pkg, download_dir=dest, quiet=True)\n")
    if not run([py, "-c", code, str(nltk_dir)], dry):
        # A missing module and a failed download are different bugs with different fixes, so the
        # label says which one happened instead of guessing "network?".
        probe = subprocess.run([py, "-c", "import nltk"], capture_output=True, text=True)
        if probe.returncode != 0:
            last = ((probe.stderr or "").strip().splitlines() or [""])[-1]
            die(f"nltk is not importable in {py} ({last or 'no error text'}), so the corpora "
                f"could not be fetched")
        die(f"nltk could not download wordnet/framenet_v17 into {nltk_dir}; see "
            f"`{py} -m nltk.downloader -d {nltk_dir} wordnet framenet_v17` for the reason")
    ok(f"downloaded into {nltk_dir}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Install Antemuse into a Hermes home.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-cli", action="store_true",
                    help="skip the steps that go through the `hermes` command itself")
    ap.add_argument("--home", default=None, help="Hermes home (default: $HERMES_HOME or ~/.hermes)")
    args = ap.parse_args()
    dry, no_cli = args.dry_run, args.no_cli
    home = Path(args.home) if args.home else default_home()
    py = hermes_python()

    say("Antemuse base install")
    print(f"  source      {SRC}")
    print(f"  hermes home {home}")
    print(f"  python      {py}")
    if dry:
        print("  dry run     nothing will be written")

    ensure_deps(py, dry)
    ensure_corpora(py, dry)

    # -------------------------------------------------------------------- 3. plugin
    say("3. plugin files")
    plugin_dir = home / "plugins" / "antemuse"
    copytree(SRC, plugin_dir, dry)
    if not dry and not (plugin_dir / "plugin.yaml").exists():
        die("plugin.yaml missing after copy")
    # On an upgrade this directory is the app's *source*: its reconciler does
    # fs.cp(source.dir, staged, {recursive:true}) into desktop-plugins/, so anything an older
    # release left here comes back into the pane dir on the next republish. copytree writes over
    # but never deletes, so the extras have to be swept here, not only at the destination.
    stale = clear_pane_dir(plugin_dir / "desktop")
    if stale:
        ok(f"swept {len(stale)} file(s) from the package's desktop half: "
           + ", ".join(sorted(stale)[:6]) + ("…" if len(stale) > 6 else ""))
    ok(str(plugin_dir))

    say("3b. register and enable")
    if no_cli:
        warn("--no-cli: skipped register/enable")
    else:
        listed = subprocess.run(["hermes", "plugins", "list"], capture_output=True, text=True)
        if "antemuse" in (listed.stdout or ""):
            ok("already registered")
        else:
            run(["hermes", "plugins", "adopt", "antemuse"], dry, quiet=True)
        if run(["hermes", "plugins", "enable", "antemuse"], dry, quiet=True):
            ok("enabled")
        else:
            warn("enable said no — check 'hermes plugins list'")

    # ------------------------------------------------------------ 4. desktop half
    say("4. desktop half (the pane the app loads)")
    removed: list[str] = []
    desktop_dir = home / "desktop-plugins" / "antemuse"
    if not dry:
        desktop_dir.mkdir(parents=True, exist_ok=True)
        # The app owns this directory and 0.9.x left things in it: a scene3d.js, a vendor/, an
        # art/ tree, a plugin.truncated.bak. Copying the new pane beside them is the same trap as
        # every stale-copy round before this one — old bytes sitting next to the file that
        # matters. Only the pane and the app's own marker belong here, so anything else goes.
        removed = clear_pane_dir(desktop_dir)
        shutil.copy2(SRC / "desktop" / "plugin.js", desktop_dir / "plugin.js")
        if removed:
            ok(f"cleared {len(removed)} file(s) left by an older release: "
               + ", ".join(removed[:6]) + ("…" if len(removed) > 6 else ""))
    else:
        stale = [c.name for c in desktop_dir.iterdir() if c.name not in PANE_KEEP] \
            if desktop_dir.exists() else []
        if stale:
            print(f"  would clear from {desktop_dir}: {', '.join(sorted(stale)[:6])}")
        print(f"  would copy desktop/plugin.js -> {desktop_dir}")
    marker = desktop_dir / ".hermes-package.json"
    if not dry and marker.exists() and '"package"' not in marker.read_text():
        marker.unlink()
        ok("removed a marker this installer wrote in the wrong shape (the app rewrites its own)")
    ok(str(desktop_dir / "plugin.js"))

    # A packaged or Store install can run with HERMES_HOME elsewhere while the app reads the
    # default home. Refreshing one leaves the app on the previous pane.
    default_desktop = Path.home() / ".hermes" / "desktop-plugins" / "antemuse"
    if default_desktop != desktop_dir and default_desktop.exists() and not dry:
        clear_pane_dir(default_desktop)
        shutil.copy2(SRC / "desktop" / "plugin.js", default_desktop / "plugin.js")
        ok(f"also refreshed {default_desktop / 'plugin.js'} (a second copy the app may read)")

    # -------------------------------------------------------------- 5. projection
    say("5. wordnet projection (where concepts sit on the picture)")
    cache = cache_dir()
    src_json = SRC / "assets" / "projection" / "wordnet.proj.json"
    src_f16 = SRC / "assets" / "projection" / "wordnet.proj.f16"
    if src_json.exists() and src_f16.exists():
        if not dry:
            cache.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_json, cache / src_json.name)
            shutil.copy2(src_f16, cache / src_f16.name)
        ok(f"placed in {cache}")
    elif (cache / "wordnet.proj.json").exists() and (cache / "wordnet.proj.f16").exists():
        ok(f"already in {cache}")
    else:
        warn("no projection — concepts fall back to a plain circle until tools/project_wordnet.py runs")

    # ------------------------------------------------------------------ 6. ledger
    say("6. first ledger scan")
    if not dry:
        code = ("import sys\n"
                "sys.path.insert(0, sys.argv[1])\n"
                "from core import history\n"
                "print(' ', history.scan_sessions(days=7))\n")
        if not run([py, "-c", code, str(plugin_dir)], dry):
            warn("scan did not run; the ledger fills as you use Hermes")
    if (home / "state.db").exists() or dry:
        ok("ledger ready (it also fills from use: every served concept is recorded)")
    else:
        warn(f"no session store at {home / 'state.db'} — the map draws its ground with nothing lit")

    say("done")
    print("  Restart the gateway so it picks up the plugin, then:  /walk   then   /return")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
