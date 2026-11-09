"""Serve the activation route over real HTTP, against the real ledger, and prove the picture comes back.

    python3 tools/e2e_activation.py [--session ID]

What this exercises, and why it is separate from the unit tests: the tests call the route function
directly. This starts a server, makes HTTP requests, and checks bytes — the route as the desktop
pane will actually meet it. It runs against a scratch states home with a copy of the real ledger,
so nothing here touches the agent's own state or the live plugin data.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REAL_HOME = Path.home() / ".hermes" / "plugin-data" / "antemuse"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _prepare(session: str) -> Path:
    """A scratch home holding a copy of the real ledger and one active walk."""
    home = Path(tempfile.mkdtemp(prefix="antemuse-e2e-"))
    ledger = REAL_HOME / "concepts.db"
    if not ledger.exists():
        raise SystemExit(f"no ledger at {ledger} · nothing to draw")
    shutil.copyfile(ledger, home / "concepts.db")
    (home / "state.json").write_text(json.dumps({
        "active": "walk",
        "key": "walk",
        "origin": {"session_id": session},
        "turns_left": 3,
    }))
    return home


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default="20261108_091834_aa6c8db0")
    args = ap.parse_args(argv)

    home = _prepare(args.session)
    os.environ["ANTEMUSE_STATES_HOME"] = str(home)
    os.environ.setdefault("NLTK_DATA", str(Path.home() / "nltk_data"))

    import importlib.util
    from fastapi import FastAPI
    import uvicorn

    spec = importlib.util.spec_from_file_location(
        "antemuse_e2e_api", ROOT / "dashboard" / "plugin_api.py")
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)

    from core import screensaver, storage
    state = json.loads((home / "state.json").read_text())

    class _Panel:
        @staticmethod
        def engine_state():
            return {"active": state, "residue": [], "journal": []}

    core = type("_Core", (), {"panel": _Panel, "screensaver": screensaver})
    api.plugin = lambda: type("_Plugin", (), {"core": core})()
    # the stills live in the scratch home, as they do in the real one
    storage.data_dir = lambda: home

    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/antemuse")
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.05)

    base = f"http://127.0.0.1:{port}/api/plugins/antemuse"
    ok = True
    try:
        with urllib.request.urlopen(f"{base}/state?cols=48&rows=24&fit=cover&session={args.session}",
                                    timeout=60) as response:
            payload = json.loads(response.read())
        stills = payload.get("stills") or []
        print(f"state      : active={payload.get('active', {}).get('key')} stills={len(stills)}")
        for url in stills:
            print(f"             {url}")

        if not stills:
            print("FAIL: a live state with a real ledger served no stills")
            ok = False
        for url in stills[:1]:
            with urllib.request.urlopen(base + url.replace("/api/plugins/antemuse", ""), timeout=30) as r:
                blob = r.read()
                ctype = r.headers.get("content-type")
            signature = blob[:2] == b"\xff\xd8"
            print(f"still      : {len(blob)} bytes · {ctype} · jpeg={signature}")
            ok = ok and signature and len(blob) > 5000

        # a traversal must be a refusal, not a file
        for probe in ("/art/walk/../../state.json", "/art/walk/state.json"):
            try:
                with urllib.request.urlopen(base + probe, timeout=10) as r:
                    body = r.read()[:80]
                print(f"refusal    : {probe} -> {r.status} {body!r}")
                ok = False
            except urllib.error.HTTPError as exc:
                print(f"refusal    : {probe} -> {exc.code}")
            except Exception as exc:
                print(f"refusal    : {probe} -> {type(exc).__name__}")

        # a chat that does not own the state gets its ambient scene and no activation stills
        with urllib.request.urlopen(f"{base}/state?cols=48&rows=24&session=someone-else",
                                    timeout=60) as response:
            other = json.loads(response.read())
        print(f"other chat : stills={len(other.get('stills') or [])} (must be 0)")
        ok = ok and not (other.get("stills") or [])
    finally:
        server.should_exit = True
        thread.join(timeout=10)

    print("\nOK" if ok else "\nFAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
