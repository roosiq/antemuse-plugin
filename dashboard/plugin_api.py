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

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

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


def _core():
    """The plugin's own `core` package, whichever way this module was loaded.

    Three shapes reach this file and each broke the one before it:

    * `<plugin>.dashboard.plugin_api` (the tests) -> `from .. import core`.
    * flat with the plugin root on sys.path -> `import core`.
    * a router file loaded as a bare module with nothing on sys.path (the gateway) -> neither
      works, and the ImportError was swallowed into an empty `stills` with a blank note, which is
      why the pane showed nothing for four rounds. It is also why every such fix needs a gateway
      restart to take effect: the module is imported once, at startup.

    The last leg therefore loads the package straight off disk under the name `core`, which does
    not depend on sys.path order or on what else has already claimed that name.
    """
    try:
        from .. import core as core_pkg  # imported as <plugin>.dashboard.plugin_api
        return core_pkg
    except Exception:
        pass

    import sys
    from pathlib import Path as _Path

    try:
        root = _Path(__file__).resolve().parent.parent
    except NameError:  # loaded without a __file__ (exotic importer)
        raise ImportError("cannot locate the plugin root: __file__ is undefined")

    def _inside(module) -> bool:
        # `core.__file__` is `<root>/core/__init__.py`, so the plugin root is a PARENT of it,
        # not its parent directory: comparing `.parent` rejected the correct package.
        try:
            return root in _Path(module.__file__).resolve().parents
        except (AttributeError, OSError, TypeError):
            return False

    known = sys.modules.get("core")
    if known is not None and _inside(known):
        return known

    try:
        import core as flat_pkg  # flat, with the plugin root on sys.path
        if _inside(flat_pkg):
            return flat_pkg
    except Exception:
        pass

    import importlib.util

    package_dir = root / "core"
    spec = importlib.util.spec_from_file_location(
        "core", package_dir / "__init__.py", submodule_search_locations=[str(package_dir)]
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable core package at {package_dir}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["core"] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if known is not None:
            sys.modules["core"] = known
        else:
            sys.modules.pop("core", None)
        raise
    return module


def _plugin_version() -> str:
    """The version of the code that is answering, not the version on disk.

    A gateway holds the module it imported at startup, so "is this the new code?" was being
    guessed from mtimes and file stats — and guessed wrong twice. Shipping the version in the
    payload makes a stale process say its own name.
    """
    try:
        from pathlib import Path as _Path
        text = (_Path(__file__).resolve().parent.parent / "plugin.yaml").read_text()
        for line in text.splitlines():
            if line.strip().startswith("version:"):
                return line.split(":", 1)[1].strip().strip('"\'')
    except Exception:
        pass
    return "unknown"


_LOADED_VERSION = _plugin_version()


def _core_module(name: str):
    """One submodule of `core` (`core.activation_stills`), loaded the same way either time."""
    import importlib
    return importlib.import_module(_core().__name__ + "." + name)


@router.get("/graph")
def graph(session: str = "", limit: int = 1400):
    """The same map the stills draw, as numbers a 3D surface can turn.

    The stills are 960x600 JPEGs: a picture of the map. This is the map — labels, their real 3D
    position from the stored projection, and how strongly each is firing. The pane builds its own
    edges from these positions (k-nearest in this space, the same rule `nearest()` uses), so an
    edge means "these two are near here", exactly as in the stills.

    Nothing here is invented: a concept with no projection simply is not in the list, and nothing
    is lit unless the ledger says it fired.
    """
    engine_state = _core_module("engine").peek() or {}
    active = engine_state or {}
    belongs_here = True
    if active and session:
        origin = active.get("origin") or {}
        owner = origin.get("session_id") if isinstance(origin, dict) else None
        belongs_here = owner in (None, "") or owner == session
    drawable = bool(active and belongs_here)
    key = str(active.get("key") or "") if drawable else "profile"
    own = ((active.get("origin") or {}).get("session_id") if drawable else session) or session or ""

    activation_stills = _core_module("activation_stills")
    activation = _core_module("activation")
    labels = activation_stills._all_labels(int(max(120, min(limit, 2400))))
    pos = activation_stills.positions(labels) if labels else {}
    lit = {}
    try:
        lit = activation.activations(own, key if drawable else None) or {}
    except Exception:  # health: BLE001 -- no firings is a fact, not a failure
        lit = {}
    nodes = []
    for label, xyz in pos.items():
        slot = lit.get(label) or {}
        try:
            w = max(0.0, min(1.0, float(slot.get("weight", 0.0))))
        except (TypeError, ValueError):
            w = 0.0
        nodes.append({"l": label, "x": float(xyz[0]), "y": float(xyz[1]), "z": float(xyz[2]),
                      "w": w})
    nodes.sort(key=lambda n: n["w"])  # brightest last: a stable draw order across polls
    return {
        "key": key,
        "session": own,
        "nodes": nodes,
        "lit": sum(1 for n in nodes if n["w"] > 0.05),
        "plugin": _LOADED_VERSION,
        "server": f"{Path(__file__).stat().st_mtime_ns}",
    }


@router.get("/state")
# The request is injected by FastAPI and optional so the route can be called directly in tests.
def state(request: Request = None, cols: int | None = None, rows: int | None = None, fit: str = "contain",
          busy: bool = False, session: str | None = None) -> Dict[str, Any]:
    """The current state, as counts and a served frame.

    ``?busy=1`` says a turn is in flight, which changes only the ambient scene:
    between states the pane paints ``work`` instead of ``idle``.

    ``?session=`` scopes the *art* to one conversation. A state is entered per
    profile, so if the active state belongs to another chat the layer must not
    borrow it: that chat gets its ambient scene instead. The counts stay
    profile-level — they are what the engine holds, not what one chat owns.

    ``?cols=&rows=`` lets a surface ask for the grid its own pixel box can hold.
    The numbers are clamped to the projection's envelope and echoed back in the
    payload, so a caller can tell what it got rather than assume what it asked for.
    """
    proj = projection()
    width, height = proj.grid(cols, rows)
    watch = plugin().core.panel.engine_state()
    active = watch.get("active") or {}
    lines: List[str] = []
    # Whose state is this? A per-profile state entered in one chat must not paint
    # itself behind a different chat just because both share a profile.
    belongs_here = True
    if active and session:
        origin = active.get("origin") or {}
        owner = origin.get("session_id") if isinstance(origin, dict) else None
        belongs_here = owner in (None, "") or owner == session

    if active and belongs_here:
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
    payload = proj.project(watch, lines, cols=width, rows=height)

    # The pane draws images. When a state is live and the ledger has servings for it, serve the
    # activation stills and let the surface paint those instead of the baked art. An empty list
    # means "nothing is firing" and the surface keeps its baked scene.
    payload["stills"] = []
    payload["files"] = []
    payload["still_note"] = ""
    # Which build of this file answered: the pane and the app can disagree about that, and the
    # field is how you tell instead of guessing.
    payload["server"] = f"{Path(__file__).stat().st_mtime_ns}"
    # the version THIS PROCESS loaded, captured at import: a gateway that started before a
    # fix says its own old number instead of leaving "is it stale?" to be guessed
    payload["plugin"] = _LOADED_VERSION
    if active and not belongs_here:
        # Named, not silent: a pane asking about another chat's state gets its ambient scene, and
        # whoever wonders why can find out.
        payload["still_note"] = "state belongs to another chat"
    # The map is the pane's whole surface, not a decoration that appears only while a state runs:
    # with no state (or one belonging to another chat) it draws the profile's recent firings on
    # the ledger's concept space. An empty pane shows the app's own artwork, which is not ours to
    # show — and that is exactly what "I still see the wrong viz" was.
    drawable = bool(active and belongs_here)
    key = str(active.get("key") or "") if drawable else "profile"
    own = ((active.get("origin") or {}).get("session_id") if drawable else session) or session or ""
    try:
        activation_stills = _core_module("activation_stills")
        try:
            paths = activation_stills.fresh(move=key, session=str(own))
        except OSError:
            # The frame set was rotated away under us. One forced redraw is cheaper than telling
            # the person their picture failed when it did not.
            paths = activation_stills.stills(move=key, session=str(own))
        payload["stills"] = [f"/api/plugins/antemuse/art/{key}/{p.name}" for p in paths]
        payload["files"] = [p.as_uri() for p in paths]
        # Three ways to reach the same picture, because the pane's surface decides which one
        # works: absolute HTTP URLs (a remote desktop, where the files are on the host and not on
        # the computer showing the pane), which the pane cannot fetch from a file:// page but the
        # gateway serves anyway, and the router-relative paths the pane reaches over ctx.rest.
        base = str(request.base_url).rstrip("/") if request is not None else ""
        payload["files_http"] = ([f"{base}/api/plugins/antemuse/art/{key}/{p.name}" for p in paths]
                                 if base else [])
        payload["stills_b64"] = [f"/art_b64/{key}/{p.name}" for p in paths]
        if not paths:
            payload["still_note"] = f"nothing firing in {key}" if drawable else "nothing firing yet"
    except Exception as exc:  # health: BLE001 -- a missing picture is not a broken state
        payload["stills"] = []
        payload["files"] = []
        payload["files_http"] = []
        payload["stills_b64"] = []
        payload["still_note"] = f"picture failed: {type(exc).__name__}: {exc}"[:160]
    return payload


def _still_path(name: str, filename: str):
    """Where a still actually is, for this machine.

    `stills()` draws into `<state>/base/` and only promotes them to `<state>/` when the three.js
    post-process succeeds. Without playwright there is no post-process, so the stamped files stay in
    `base/` — and this route used to look only at `<state>/`, 404ing every URL `/state` had just
    advertised. The pane then fell through its legs to nothing, which is what "the wrong viz" was
    on a machine without the bake step.
    """
    storage = _core_module("storage")
    root = storage.data_dir() / "activation" / name
    for candidate in (root / filename, root / "base" / filename):
        if candidate.is_file():
            return candidate
    return None


@router.get("/art/{name}/{filename}")
def art(name: str, filename: str):
    """Serve one activation still. Only files this plugin wrote are reachable: the name and the
    filename are matched against the state directory, never joined from user input."""
    safe_name = "".join(ch for ch in name if ch.isalnum() or ch in "-_")
    safe_file = "".join(ch for ch in filename if ch.isalnum() or ch in "-_.")
    if not safe_name or not safe_file or not safe_file.endswith(".jpg"):
        raise HTTPException(status_code=404, detail="not found")
    try:
        path = _still_path(safe_name, safe_file)
    except Exception:
        path = None
    if path is None:
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(str(path), media_type="image/jpeg")


@router.get("/art_b64/{name}/{filename}")
def art_b64(name: str, filename: str):
    """The same still, carried as base64 instead of bytes.

    A desktop pane is a file:// page: an <img> pointed at this route reaches it with no cookie and
    no host path, which is fine on the machine that has the files and useless on a remote desktop.
    The pane already talks to this router over the gateway RPC, so the bytes can travel that way.
    """
    safe_name = "".join(ch for ch in name if ch.isalnum() or ch in "-_")
    safe_file = "".join(ch for ch in filename if ch.isalnum() or ch in "-_.")
    if not safe_name or not safe_file or not safe_file.endswith(".jpg"):
        raise HTTPException(status_code=404, detail="not found")
    try:
        path = _still_path(safe_name, safe_file)
    except Exception:
        path = None
    if path is None:
        raise HTTPException(status_code=404, detail="not found")
    import base64
    return {"type": "image/jpeg",
            "data": base64.b64encode(path.read_bytes()).decode("ascii")}
