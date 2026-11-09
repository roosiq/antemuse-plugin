"""Post-process the activation stills with three.js, at bake time.

The plugin never imports three: this drives headless Chromium over a page that loads one still,
runs it through the official ``EffectComposer`` (bloom, chromatic separation, grain, vignette) and
hands back the same picture, photographed rather than plotted. Nothing is added to it — the passes
change how it looks, not what it says.

Bake time only, and optional: if no browser or no three build is present, the stills keep their
plain render and the caller is told why, by name.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
PAGE = "/tools/activation_post.html"
SHOOT = ROOT / "tools" / "shoot.mjs"
NODE_MODULES = Path("/home/ryan/.hermes/hermes-agent/node_modules")
TIMEOUT_S = 120


def _wait_for(port: int, timeout: float = 8.0) -> bool:
    """The server is a subprocess; a request before it listens fails as a refused connection."""
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.25)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.05)
    return False


def _real_home() -> Path:
    """The account's home, not ``$HOME`` — a test harness points ``$HOME`` at a temp dir, and
    Playwright's browsers live under the real one."""
    try:
        import pwd
        return Path(pwd.getpwuid(os.getuid()).pw_dir)
    except Exception:
        return Path.home()


def _env() -> dict:
    env = dict(os.environ)
    if not env.get("PLAYWRIGHT_BROWSERS_PATH"):
        cache = _real_home() / ".cache" / "ms-playwright"
        if cache.is_dir():
            env["PLAYWRIGHT_BROWSERS_PATH"] = str(cache)
    return env


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def available() -> Optional[str]:
    """Why post-processing cannot run, or None when it can."""
    if not (ROOT / "vendor" / "three-bake" / "three.module.js").exists():
        return "three build missing · vendor/three-bake"
    if not SHOOT.exists():
        return "shoot.mjs missing"
    if not shutil.which("node"):
        return "node missing"
    return None


def apply(paths: List[Path], size: tuple = (960, 600), timeout: int = TIMEOUT_S) -> List[Path]:
    """Post-process each still in place; return the ones that came back.

    A still that fails to render is left exactly as it was — a missing effect is not a reason to
    lose the picture.
    """
    if not paths or available():
        return []
    # The server is rooted at the repo (that is where the page and the three build live), and a
    # still may live in the plugin's data directory, so each one is staged inside the repo first.
    stage = ROOT / "tools" / ".post-staging"
    stage.mkdir(parents=True, exist_ok=True)
    port = _free_port()
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port),
                               "--bind", "127.0.0.1"],
                              cwd=str(ROOT), stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    done: List[Path] = []
    try:
        if not _wait_for(port):
            return []
        # One browser for the batch: three launches back to back is where this was flaky.
        args: List[str] = ["node", str(SHOOT)]
        wanted: List[Path] = []
        for path in paths:
            staged = stage / path.name
            shutil.copyfile(path, staged)
            out = path.with_name(path.stem + "-post.jpg")
            wanted.append(out)
            args += [str(out), f"http://127.0.0.1:{port}{PAGE}"
                               f"?src=/{staged.relative_to(ROOT)}&w={size[0]}&h={size[1]}"]
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                                env=_env())
        for out in wanted:
            if out.exists() and out.stat().st_size > 2000:
                done.append(out)
            else:
                print(f"postprocess: {out.name} did not come back · "
                      f"{(result.stderr or '').strip()[:200]}", file=sys.stderr)
    except subprocess.SubprocessError as exc:
        print(f"postprocess: {exc}", file=sys.stderr)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
    return done
