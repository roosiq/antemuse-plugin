"""Antemuse desktop backend — mounted at ``/api/plugins/antemuse/``.

One route, ``GET /state``, so a pane can show what a turn is governed by while it
is running. The payload is counts, names and glyphs; its shape lives in
``projection.py``, which is pure and tested without a server.

Deliberately absent: the state's ``directive`` (that is model-facing), any goal,
any journal text, any candidate text.

Rendering happens here, not in the plugin's JavaScript, so there is exactly one
renderer of these scenes: the same ``surfaces.art`` the CLI draws, served as
text. The desktop half displays it and does not sample images, so the
fourth-renderer problem recorded in ``specs/changes/desktop-surfaces/spec.md``
does not arise.

The Hermes web server imports this file and mounts ``router`` at
``/api/plugins/<name>/``; it does so only while the plugin is in
``plugins.enabled``.
"""
from __future__ import annotations

import importlib.util
import sys
import threading
from pathlib import Path
import time
from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter()

ROOT = Path(__file__).resolve().parents[1]
_HERE = Path(__file__).resolve().parent
_MODULE = "antemuse_desktop_backend"
_PROJECTION = "antemuse_desktop_projection"
_load_lock = threading.Lock()


def _by_path(name: str, path: Path, *, package: bool = False):
    """Load a sibling module by path, once, under a private name."""
    with _load_lock:
        cached = sys.modules.get(name)
        if cached is not None:
            return cached
        spec = importlib.util.spec_from_file_location(
            name,
            path,
            submodule_search_locations=[str(path.parent)] if package else None,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module


def projection():
    return _by_path(_PROJECTION, _HERE / "projection.py")


def plugin():
    """This repository's plugin package, loaded once under a private name.

    The web server imports this file by path, so ``antemuse`` is not importable
    under its own name here. The private name also keeps this plugin's ``core``
    from colliding with any other plugin that ships one. Two copies of module
    state is harmless: the state itself lives in ``state.json``.
    """
    return _by_path(_MODULE, ROOT / "__init__.py", package=True)


#: Seconds per baked frame, per state. A walk steps slowly (a frame every three
#: seconds), a doomscroll moves fast, a dream barely moves at all. The bake sampled
#: t at f/n of a 2*pi loop, so a wall-clock index is enough to animate it.
FRAME_SECONDS = {"walk": 3.0, "daydream": 2.4, "doomscroll": 1.1, "dream": 4.0}
FRAME_DEFAULT = 2.5


def frame_index(key: str, frames: int = 8, now: float | None = None) -> int:
    """Which baked frame is on screen right now. Deterministic in time, not random."""
    if frames <= 0:
        return 0
    step = FRAME_SECONDS.get(key, FRAME_DEFAULT)
    return int((time.time() if now is None else now) // step) % frames


@router.get("/state")
def state(cols: int | None = None, rows: int | None = None, fit: str = "contain",
          busy: bool = False) -> Dict[str, Any]:
    """The current state, as counts and a served frame.

    ``?busy=1`` says a turn is in flight, which changes only the ambient scene:
    between states the pane paints ``work`` instead of ``idle``.

    ``?cols=&rows=`` lets a surface ask for the grid its own pixel box can hold.
    The numbers are clamped to the projection's envelope and echoed back in the
    payload, so a caller can tell what it got rather than assume what it asked for.
    """
    proj = projection()
    width, height = proj.grid(cols, rows)
    watch = plugin().core.panel.engine_state()
    active = watch.get("active") or {}
    lines: List[str] = []
    if active:
        try:
            lines = plugin().core.surfaces.art(
                cols=width, rows=height,
                index=frame_index(str(active.get("key") or ""), frames=8),
                scene=str(active.get("key") or ""),
                fit="cover" if fit == "cover" else "contain",
                pane=fit == "cover",
                # dither buys the pane its gradients; on a card it buys a block
                dither=fit == "cover",
                gamma=1.0,
            )
        except Exception:  # health: BLE001 -- a missing frame is not a broken state
            lines = []
    if not lines:
        # Between states the agent still exists, so the pane is never blank:
        # `work` while a turn is in flight, `idle` when nothing is running.
        scene_name = "work" if busy else "idle"
        try:
            lines = plugin().core.screensaver.frame(scene_name, width, height)
        except Exception:  # health: BLE001 -- art is never worth a 500
            lines = []
    return proj.project(watch, lines, cols=width, rows=height)
