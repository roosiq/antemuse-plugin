"""Antemuse desktop backend — mounted at ``/api/plugins/antemuse/``.

Two routes: ``GET /graph`` (the map as numbers) and ``GET /state`` (what a turn is governed by).

There is one renderer and it is the pane: ``desktop/plugin.js`` draws the concept activation graph
from ``/graph`` in raw WebGL. This module sends numbers and counts, never pictures, never glyphs —
the baked stills, the ASCII frame and the ambient screensaver are gone, and with them Pillow,
Playwright, node and a browser download.

Deliberately absent from the payload: the state's ``directive`` (that is model-facing), any goal,
any journal text, any candidate text.
"""
from __future__ import annotations

import importlib.util
import sys
import threading
from pathlib import Path
import time
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Request

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
    """One submodule of `core` (`core.atlas`), loaded the same way either time."""
    import importlib
    return importlib.import_module(_core().__name__ + "." + name)


_GRAPH_MEMO: Dict[str, Any] = {"key": None, "at": 0.0, "payload": None}


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
    import time as _time
    started = _time.time()
    engine_state = _core_module("engine").peek() or {}
    # The memo must know what state it was drawn for. Entering a walk within three seconds of a
    # poll otherwise served the previous "profile" map, and the pane showed no state at all.
    # ...and it must know whether the ledger has moved. A walk that stepped between two polls
    # served a new concept, and the memo answered the old picture for the rest of its three
    # seconds: every poll in a test showed lit 0 while three servings were already recorded.
    try:
        stamp = (_core_module("activation")._rows("SELECT MAX(at) FROM served") or [[0]])[0][0] or 0
    except Exception:  # health: BLE001 -- no ledger is a fact, not a failure
        stamp = 0
    want = (session, int(limit), str(engine_state.get("key") or ""),
            float(engine_state.get("entered_at") or 0.0), float(stamp))
    if (_GRAPH_MEMO.get("want") == want and _GRAPH_MEMO.get("payload") is not None
            and _time.time() - float(_GRAPH_MEMO.get("at") or 0) < 3.0):
        return _GRAPH_MEMO["payload"]
    active = engine_state or {}
    belongs_here = True
    if active and session:
        origin = active.get("origin") or {}
        owner = origin.get("session_id") if isinstance(origin, dict) else None
        belongs_here = owner in (None, "") or owner == session
    drawable = bool(active and belongs_here)
    key = str(active.get("key") or "") if drawable else "profile"
    # A state entered with no session — from the app, or by a script — records its firings with an
    # empty session. Falling back to the *pane's* session there filtered those firings out, so a
    # running walk served nine concepts and the pane lit two. The owner is empty means everyone.
    if drawable:
        own = str((active.get("origin") or {}).get("session_id") or "")
    else:
        own = str(session or "")

    activation = _core_module("activation")
    lit = {}
    try:
        lit = activation.activations(own, key if drawable else None) or {}
    except Exception:  # health: BLE001 -- no firings is a fact, not a failure
        lit = {}
    # The ground is the busiest `limit` concepts, so a concept the state just served can fall
    # outside it — and then it had nothing to light: the walk served three concepts per hop and
    # the map drew none of them. Whatever is firing is always part of the picture.
    # The trail the state actually walked, in order. The firings say which concepts are live; they
    # do not say that the walk went A -> B -> C, which is the thing a path is. Servings are the
    # record of that order: each hop serves the concept it lands on.
    path: List[str] = []
    if drawable and key == "walk":
        try:
            trail = activation._rows(
                "SELECT c.label FROM served s JOIN concepts c ON c.id = s.concept_id "
                "WHERE s.move = 'walk' AND s.session = ? AND s.at >= ? "
                "ORDER BY s.at DESC LIMIT 32",
                (own, float(active.get("entered_at") or 0.0)))
            path = [row[0] for row in reversed(trail or []) if row and row[0]]
        except Exception:  # health: BLE001 -- no trail is a fact, not a failure
            path = []

    # How much has been said about each concept: appearances across the ledger, not activation.
    # Size answers "is this a thing we keep coming back to"; colour answers "is it firing now".
    volume: Dict[str, int] = {}
    try:
        for label, n in activation._rows(
                "SELECT c.label, COUNT(*) FROM appearances a JOIN concepts c ON c.id = a.concept_id "
                "GROUP BY a.concept_id") or []:
            if label:
                volume[str(label)] = int(n)
    except Exception:  # health: BLE001 -- no counts is a fact, not a failure
        volume = {}
    top = max(volume.values()) if volume else 1

    atlas = _core_module("atlas")
    ground = atlas._all_labels(int(max(120, min(limit, 2400))))
    # Whatever the surface has to draw must be on it: firings and the trail are drawn, so they
    # join the ground even when they are not among its busiest concepts.
    labels = sorted(set(ground) | set(lit) | set(path))
    pos = atlas.positions(labels) if labels else {}
    nodes = []
    for label, xyz in pos.items():
        slot = lit.get(label) or {}
        try:
            w = max(0.0, min(1.0, float(slot.get("weight", 0.0))))
        except (TypeError, ValueError):
            w = 0.0
        # sqrt: a concept met 400 times is not 400 times bigger than one met once
        v = (float(volume.get(label, 0)) / top) ** 0.5 if top else 0.0
        nodes.append({"l": label, "x": float(xyz[0]), "y": float(xyz[1]), "z": float(xyz[2]),
                      "w": w, "v": round(v, 4)})
    nodes.sort(key=lambda n: n["w"])  # brightest last: a stable draw order across polls
    # The relations this graph actually has. The pane used to draw k-nearest neighbours in the
    # projection, which is geometry, not connection — so an edge could light up only if the two
    # points happened to be near each other. These are co-occurrences from the ledger.
    links: List[Dict[str, Any]] = []
    try:
        rows = activation._rows(
            "SELECT ca.label, cb.label, COUNT(*) AS n FROM appearances a "
            "JOIN appearances b ON b.source = a.source AND b.ref = a.ref AND b.concept_id > a.concept_id "
            "JOIN concepts ca ON ca.id = a.concept_id JOIN concepts cb ON cb.id = b.concept_id "
            "WHERE a.source = 'message' GROUP BY a.concept_id, b.concept_id "
            "ORDER BY n DESC LIMIT 2400")
        for left, right, n in rows or []:
            if left and right:
                links.append({"a": left, "b": right, "w": int(n)})
    except Exception:  # health: BLE001 -- no links is a fact, not a failure
        links = []

    payload = {
        "key": key,
        "links": links,
        "path": path,
        "session": own,
        "nodes": nodes,
        "lit": sum(1 for n in nodes if n["w"] > 0.05),
        "plugin": _LOADED_VERSION,
        "server": f"{Path(__file__).stat().st_mtime_ns}",
        "ms": int((_time.time() - started) * 1000),
    }
    # The pane polls this every four seconds and the positions only change when the projection or
    # the ledger changes, so a short memo keeps a poll from re-walking 1,373 labels. The weights
    # are part of the payload, so the TTL stays below the poll interval.
    _GRAPH_MEMO.update({"want": want, "at": _time.time(), "payload": payload})
    return payload


@router.get("/state")
# The request is injected by FastAPI and optional so the route can be called directly in tests.
def state(request: Request = None, session: str | None = None,
          with_graph: int = Query(0, alias="graph"),
          stills: int = Query(1), cols: int | None = None, rows: int | None = None,
          fit: str = "contain", busy: bool = False) -> Dict[str, Any]:
    """What is running, as counts — and, with ``?graph=1``, the map as numbers.

    ``?session=`` scopes the *map* to one conversation: a state is entered per profile, so a chat
    that did not enter it gets no map borrowed from another.

    The picture comes from ``/graph`` and is drawn by the pane (``desktop/plugin.js``, raw WebGL).
    This route used to also render a glyph grid, three JPEG stills and an ambient screensaver —
    three renderers for one picture, each with its own dependency, all hidden by the pane on its
    first successful poll. ``cols``/``rows``/``fit``/``busy``/``stills`` are still accepted so a
    pane built against the old shape is not answered with a 422; they change nothing.
    """
    proj = projection()
    watch = plugin().core.engine.watch_state()
    payload = proj.project(watch, None)
    payload["picture"] = "pane"
    payload["plugin"] = _LOADED_VERSION          # the build this process actually loaded
    payload["server"] = f"{Path(__file__).stat().st_mtime_ns}"
    if with_graph:
        try:
            payload["graph"] = graph(session=str(session or ""), limit=1400)
        except Exception as exc:  # health: BLE001 -- no map is not a broken state
            payload["graph"] = {"nodes": [], "lit": 0, "error": f"{type(exc).__name__}: {exc}"[:160]}
    return payload
