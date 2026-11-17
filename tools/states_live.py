#!/usr/bin/env python3
"""Drive the real art pane in a real browser with a real mouse and keyboard.

The desktop app shell is not on this host (it lives on the operator's machine), so this
harness reproduces the two things the pane actually is: an HTTP backend running the real
engine handlers, and a Chromium canvas running the shipped ``desktop/plugin.js``. Input is
dispatched as real browser events — mouse move/press/release and key presses — and what is
monitored is what a person would see: the pane's scene, its pixels, its console, and the
strings the chat would print.

Run:  PLAYWRIGHT_BROWSERS_PATH=0 uvx --with playwright --quiet python tools/states_live.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ANTEMUSE_STATES_HOME", tempfile.mkdtemp(prefix="states-live-"))

from core import engine, recall, states  # noqa: E402


def state_payload(session: str) -> dict:
    """The fields the pane actually reads. Built here rather than through the FastAPI router,
    which cannot import under this interpreter; the shape is the one `/state` returns."""
    data = __import__("json").loads((engine.storage.data_dir() / "state.json").read_text()) \
        if (engine.storage.data_dir() / "state.json").exists() else {}
    active = data.get("active") or {}
    if not active:
        return {"active": None}
    spec = states.spec(str(active.get("key") or ""))
    return {"active": {"key": active.get("key"),
                       "served": int(active.get("served") or 0),
                       "dose": int((spec.get("dose") or {}).get("n") or 0)}}

SEED = (
    "A recorded turn with enough words for one memory.",
    "Another recorded turn with enough words for another memory.",
    "A third recorded turn lets two memory pairs remain distinct.",
)

REACT_STUB = """
const noop = () => null
export const useState = (v) => [typeof v === 'function' ? v() : v, noop]
export const useEffect = () => {}
export const useMemo = (f) => f()
export const useCallback = (f) => f
export const useRef = (v) => ({ current: v })
export const createElement = () => null
export default { createElement, useState, useEffect, useMemo, useCallback, useRef }
"""

PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
  html,body{margin:0;background:#0b0b0b}
  #art{display:block;width:640px;height:400px}
</style>
<script type="importmap">
{"imports":{"@hermes/plugin-sdk":"/__sdk.js","react":"/__react.js","react/jsx-runtime":"/__jsx.js"}}
</script>
</head><body>
<canvas id="art" width="640" height="400"></canvas>
<script type="module">
import { createArt, sceneFor } from '/desktop/plugin.js'
const art = createArt(document.getElementById('art'), { dark: true })
window.__harness = { art, sceneFor }
window.__ready = true
</script>
</body></html>
"""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass

    def _json(self, body):
        raw = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        try:
            return self._do_get()
        except Exception as exc:
            import traceback

            return self._json({"error": f"{exc}", "trace": traceback.format_exc()[-800:]})

    def _do_get(self):
        parsed = urlparse(self.path)
        if parsed.path == "/__sdk.js":
            return self._raw(SDK_STUB.encode(), "text/javascript")
        if parsed.path == "/__react.js":
            return self._raw(REACT_STUB.encode(), "text/javascript")
        if parsed.path == "/__jsx.js":
            return self._raw(JSX_STUB.encode(), "text/javascript")
        if parsed.path == "/__page":
            return self._raw(PAGE.encode(), "text/html")
        if parsed.path == "/api/state":
            session = (parse_qs(parsed.query).get("session") or [""])[0]
            return self._json(state_payload(session))
        return super().do_GET()

    def _raw(self, body, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            return self._do_post()
        except Exception as exc:  # a crash inside a handler must be visible, not a dropped socket
            import traceback

            return self._json({"error": f"{exc}", "trace": traceback.format_exc()[-800:]})

    def _do_post(self):
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)
        name = (q.get("name") or [""])[0]
        session = (q.get("session") or [""])[0] or "live"
        if parsed.path == "/api/enter":
            return self._json({"said": engine.enter(name, session=session)})
        if parsed.path == "/api/stop":
            return self._json({"said": engine.stop(session, reason="returned")})
        self.send_error(404)


# The harness already carries the SDK's shape; serving that file keeps this harness honest
# instead of maintaining a second guess at the host's exports.
STUB_FILE = Path(__file__).resolve().parent / "desktop_harness" / "sdk-stub.js"
SDK_STUB = STUB_FILE.read_text()

JSX_STUB = """
export const jsx = (type, props) => ({ type, props })
export const jsxs = jsx
export const Fragment = 'fragment'
"""


def main() -> int:
    for line in SEED:
        recall.remember(line)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"

    from playwright.sync_api import sync_playwright

    shots = Path(tempfile.mkdtemp(prefix="state-shots-"))
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(viewport={"width": 700, "height": 460})
        errors: list[str] = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto(f"{base}/__page", wait_until="load")
        page.wait_for_function("window.__ready === true", timeout=20000)

        box = page.evaluate("() => { const r = document.getElementById('art').getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height} }")

        for key in ("walk", "daydream", "doomscroll", "dream", "unstuck"):
            import urllib.request

            req = urllib.request.Request(f"{base}/api/enter?name={key}&session=live", method="POST")
            answer = json.loads(urllib.request.urlopen(req, timeout=10).read())
            if "said" not in answer:
                print("server refused:", json.dumps(answer)[:600])
                raise SystemExit(2)
            said = answer["said"]

            entered = not said.startswith("cannot enter")
            # The chat order, so the pane is looking at a state that has actually served
            # something: a turn starts, the hook takes its block.
            block = ""
            if entered:
                engine.note_turn("live")
                block = engine.inject("live") or ""
            state = json.loads(urllib.request.urlopen(f"{base}/api/state?session=live", timeout=10).read())
            scene = page.evaluate("(a) => window.__harness.sceneFor(a, false)", (state or {}).get("active"))
            painted = page.evaluate("""(s) => {
                const { art } = window.__harness
                art.setScene(s)
                for (let i = 0; i < 6; i++) art.render(1 / 60)
                const c = document.getElementById('art')
                const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data
                let lit = 0
                for (let i = 0; i < d.length; i += 4) {
                  const lum = 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2]
                  if (lum > 40) lit++
                }
                return { scene: art.stats().scene, frames: art.stats().frames,
                         lit: lit, total: c.width * c.height }
            }""", scene)

            # real input: drag across the canvas, then keys the cockpit and pane already answer
            page.mouse.move(box["x"] + box["w"] * 0.2, box["y"] + box["h"] * 0.5)
            page.mouse.down()
            for step in range(8):
                page.mouse.move(box["x"] + box["w"] * (0.2 + step * 0.08),
                                box["y"] + box["h"] * (0.5 - step * 0.02))
            page.mouse.up()
            for key_name in ("a", "d", "f", "Escape", "Tab"):
                page.keyboard.press(key_name)

            after = page.evaluate("() => window.__harness.art.stats()")
            shot = shots / f"{key}.png"
            page.locator("#art").screenshot(path=str(shot))

            import urllib.request as u

            stop = json.loads(u.urlopen(u.Request(f"{base}/api/stop?session=live", method="POST"),
                                        timeout=10).read())["said"]
            rows.append({
                "state": key,
                "entered": entered,
                "chat_entry": said.split("\n")[0][:96],
                "chat_block": block.split("\n")[0][:64],
                "chat_account": stop.split("\n")[0][:96],
                "pane_served": ((state or {}).get("active") or {}).get("served"),
                "pane_dose": ((state or {}).get("active") or {}).get("dose"),
                "scene": painted["scene"],
                "frames": painted["frames"],
                "ink_pct": round(100.0 * painted["lit"] / painted["total"], 2),
                "after_input_frames": after.get("frames"),
                "errors": errors[-3:],
                "shot": str(shot),
            })
        browser.close()
    server.shutdown()

    width = max(len(r["state"]) for r in rows)
    print(f"{'state'.ljust(width)}  scene       ink%   frames  pane  chat")
    for r in rows:
        print(f"{r['state'].ljust(width)}  {r['scene']:<10}  {r['ink_pct']:>5}  "
              f"{r['after_input_frames']:>5}  {str(r['pane_served'])}/{str(r['pane_dose']):<3}  "
              f"{'entered' if r['entered'] else 'refused'}")
        print(f"    chat : {r['chat_entry']}")
        print(f"    end  : {r['chat_account']}")
        if r["errors"]:
            print(f"    console: {r['errors']}")
    print(f"\nshots: {shots}")
    print("matrix:", json.dumps([{k: r[k] for k in ('state','scene','ink_pct','pane_served','entered')} for r in rows]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
