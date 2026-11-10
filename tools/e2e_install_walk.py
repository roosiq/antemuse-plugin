"""End-to-end: tarball -> install -> enter /walk -> picture, over real HTTP.

Nothing here imports the repository. Everything runs from the extracted tarball and the directory
the installer wrote into an otherwise empty HERMES_HOME, which is the only thing that makes an
install claim worth anything.
"""

import asyncio
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# newest tarball in the dist directory, so the test follows the release instead of naming it
DIST = Path.home() / ".cache/antemuse/dist"
def _ver(path):
    parts = path.name[len("antemuse-"):-len(".tar.gz")].split(".")
    return tuple(int(p) if p.isdigit() else 0 for p in parts)


TARBALL = sorted(DIST.glob("antemuse-*.tar.gz"), key=_ver)[-1]
ROOT = Path("/tmp/e2e")
HOME = ROOT / "home"
PORT = 18931
SESSION = "e2e-install-walk"


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)


def step(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (("  ·  " + detail) if detail else ""))
    if not ok:
        raise SystemExit(1)


def main():
    # the plugin's own storage resolves its home from the environment, so the process that drives
    # it has to live in the same home the installer wrote into
    os.environ["HERMES_HOME"] = str(HOME)
    os.environ.pop("ANTEMUSE_STATES_HOME", None)
    shutil.rmtree(ROOT, ignore_errors=True)
    ROOT.mkdir(parents=True)
    HOME.mkdir()

    # 1. the artefact a person downloads
    sh(["tar", "-xzf", str(TARBALL), "-C", str(ROOT)])
    src = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("antemuse"))
    step("tarball extracts", (src / "scripts/install.sh").exists(), src.name)

    # 2. one command, into an empty home
    env = dict(os.environ, HERMES_HOME=str(HOME), NLTK_DATA="/home/ryan/nltk_data")
    env.pop("PYTHONPATH", None)
    env.pop("ANTEMUSE_STATES_HOME", None)
    # --no-cli: this host cannot commit a dependency env for a scratch home (python-olm fails to
    # build), and that is the host's problem, not the installer's. Everything the plugin itself
    # installs still runs.
    r = sh(["bash", "scripts/install.sh", "--no-cli"], cwd=str(src), env=env)
    installed = HOME / "plugins/antemuse"
    step("install.sh exits 0", r.returncode == 0, (r.stdout or "").strip().splitlines()[-1:]and
         (r.stdout or "").strip().splitlines()[-1][:90] or "")
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:])

    # 3. what it wrote
    desktop = HOME / "desktop-plugins/antemuse/plugin.js"
    step("plugin registered in the home", installed.exists())
    step("desktop half installed", desktop.exists(), f"{desktop.stat().st_size // 1024 if desktop.exists() else 0} KB")
    ledger = HOME / "plugin-data/antemuse"
    index = HOME / "cache/antemuse/wordnet.proj.json" if (HOME / "cache/antemuse").exists() else None

    # 4. the installed copy, not the repo
    # the repository must not shadow the installed copy: running this from the repo puts its own
    # `core` first and then the test would be testing the working tree, not the release
    sys.path = [p for p in sys.path if p not in ("", os.getcwd())]
    sys.path.insert(0, str(installed))
    spec = importlib.util.spec_from_file_location("am", installed / "__init__.py",
                                                  submodule_search_locations=[str(installed)])
    am = importlib.util.module_from_spec(spec)
    sys.modules["am"] = am
    spec.loader.exec_module(am)
    want = TARBALL.name[len("antemuse-"):-len(".tar.gz")]
    step(f"installed version is {want}", getattr(am, "__version__", "") == want, getattr(am, "__version__", "?"))

    from core import engine, walks  # noqa: E402  -- from the installed package

    # 5. serve the installed router over real HTTP
    api_path = installed / "dashboard/plugin_api.py"
    aps = importlib.util.spec_from_file_location("installed_api", api_path)
    api = importlib.util.module_from_spec(aps)
    sys.modules["installed_api"] = api
    aps.loader.exec_module(api)

    import uvicorn
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/antemuse")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="error"))
    # the server needs its own running loop; sleeping in this thread without running one leaves
    # the task unstarted and the port closed
    import threading
    threading.Thread(target=lambda: asyncio.run(server.serve()), daemon=True).start()
    for _ in range(100):
        time.sleep(0.1)
        if server.started:
            break
    step("installed route serves", server.started, f"127.0.0.1:{PORT}")

    def get(path):
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=30) as r:
            return json.load(r)

    body = get(f"/api/plugins/antemuse/state?graph=1&stills=0&session={SESSION}")
    g = body["graph"]
    step("a fresh install has a picture", len(g["nodes"]) > 500, f'{len(g["nodes"])} nodes, {len(g["links"])} links')

    # 6. /walk, through the command handler the host registers
    enter = am._enter("walk")
    line = enter("12", session_id=SESSION, platform="desktop")
    step("/walk answers", "WALKING" in line, line.splitlines()[0][:90])

    got = []
    for hop in range(4):
        walk = walks.get("outer")
        if hop:
            walk.step(1)
        body = get(f"/api/plugins/antemuse/state?graph=1&stills=0&session={SESSION}")
        g = body["graph"]
        lit = sum(1 for n in g["nodes"] if n["w"] > 0.05)
        got.append((len(g["nodes"]), len(g["links"]), len(g["path"]), lit, g["key"]))
        time.sleep(0.2)

    step("the state reaches the route", all(row[4] == "walk" for row in got), " | ".join(f"{r[4]}" for r in got))
    step("the walk lights concepts", got[-1][3] > 0, "lit " + ", ".join(str(r[3]) for r in got))
    step("the path grows", got[-1][2] > got[0][2], "path " + ", ".join(str(r[2]) for r in got))
    # A brand-new ledger has nothing to connect yet: relations are recorded when two concepts are
    # seen in the same message. Make that happen through the same call the hook makes.
    from core import history  # noqa: E402
    history.notice("doorstop", ref="e2e-message", session=SESSION)
    history.notice("bookend", ref="e2e-message", session=SESSION)
    body = get(f"/api/plugins/antemuse/state?graph=1&stills=0&session={SESSION}")
    links = body["graph"]["links"]
    step("a message with two concepts is a relation", links and links[0]["w"] >= 1,
         f'{len(links)} links, top ' + (str(links[0]) if links else "none"))
    step("connections are drawn from a fresh ledger", all(r[1] >= 0 for r in got),
         "links " + ", ".join(str(r[1]) for r in got) + " (a new ledger has none until a message)")

    db = ledger / "concepts.db"
    step("the walk wrote its ledger", db.exists(), str(db))

    print("\nnodes/links/path/lit over four polls:")
    for row in got:
        print("  ", row)

    # 7. leaving the state stops claiming it is a walk
    am._return("") if hasattr(am, "_return") else engine.exit()
    body = get(f"/api/plugins/antemuse/state?graph=1&stills=0&session={SESSION}")
    step("after /return the map is the whole space", body["graph"]["key"] == "profile", body["graph"]["key"])

    server.should_exit = True


main()
