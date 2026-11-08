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


@router.get("/state")
def state(cols: int | None = None, rows: int | None = None, fit: str = "contain") -> Dict[str, Any]:
    """The current state, as counts and a served frame.

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
                cols=width, rows=height, index=0,
                scene=str(active.get("key") or ""),
                fit="cover" if fit == "cover" else "contain",
                pane=fit == "cover",
            )
        except Exception:  # health: BLE001 -- a missing frame is not a broken state
            lines = []
    return proj.project(watch, lines, cols=width, rows=height)
