"""Does the pane actually put edge pixels on the glass?

The source locks in tests/test_postprocess.py can only prove the pipeline was not reverted. This
runs the real desktop/plugin.js in a real browser against the real /state handler and counts
pixels, so "the edges draw" is a measurement rather than a claim.

    python tools/pane_pixels.py [--frames 90] [--size 700x746]

Exit codes: 0 measured and edges present; 1 edges missing; 2 could not measure (no playwright,
or the pane never left its first frame) — which is a result, not a pass.

What it counts, per class, on a 1:1 screenshot:
  relation  bluish low-alpha edge pixels (the ground's relation web)
  path      the walk's trail, warm gold
  lit       firing nodes and their halos

The page is a stand-in host: the same SDK surface the app provides, the same plugin file the app
loads, and the plugin's own `ctx.rest` pointed at the handler. Nothing is synthesised — the graph
and the walk come from the ledger this machine has.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = 18979

SDK = """export const PANES_AREA = 'panes'
export const TITLEBAR_AREAS = { left: 'titlebar-left', right: 'titlebar-right' }
export const ROUTES_AREA = 'routes'
export const SIDEBAR_NAV_AREA = 'sidebar-nav'
export const STATUSBAR_AREAS = { left: 'statusbar-left', right: 'statusbar-right' }
export const PALETTE_AREA = 'palette'
export const pluginSettingsHref = (id) => `#settings/${id}`
const atom = (value) => ({ get: () => value, listen: () => () => {} })
export const host = { state: { focusedSessionId: atom('pane-pixels'), busy: atom(false) } }
"""

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>pane</title>
<style>html,body{margin:0;padding:0;background:#06070a}
#host{width:WIDTHpx;height:HEIGHTpx;overflow:hidden;background:#06070a}
#host *{box-sizing:border-box}</style>
<script type="importmap">
{"imports":{"react":"https://esm.sh/react@18.3.1",
"react/jsx-runtime":"https://esm.sh/react@18.3.1/jsx-runtime",
"react-dom/client":"https://esm.sh/react-dom@18.3.1/client",
"@hermes/plugin-sdk":"/sdk.js"}}
</script></head>
<body><div id="host"></div>
<script type="module">
import plugin from '/plugin.js'
import React from 'react'
import { createRoot } from 'react-dom/client'
const regs = []
const ctx = {
  rest: (p) => fetch('/api/plugins/antemuse' + p).then(r => r.json()),
  register: (r) => { regs.push(r); return r },
  navigate: () => {}, manifest: { id: 'antemuse', settings: {} },
  pluginSettingsHref: () => '#settings/antemuse',
  setInterval: (fn, ms) => window.setInterval(fn, ms),
  clearInterval: (h) => window.clearInterval(h),
  setTimeout: (fn, ms) => window.setTimeout(fn, ms),
  clearTimeout: (h) => window.clearTimeout(h),
  onDispose: (fn) => { window.addEventListener('beforeunload', fn); return fn }
}
plugin.register(ctx)
const pane = regs.find(r => r.id === 'pane')
if (!pane) throw new Error('no pane registration: ' + regs.map(r => r.id).join(','))
createRoot(document.getElementById('host')).render(pane.render())
window.__ready = true
</script></body></html>
"""


def serve(suffix: str, width: int, height: int, plugin: Path | None = None):
    page = PAGE.replace("WIDTH", str(width)).replace("HEIGHT", str(height))

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path in ("/", "/index.html"):
                body = page.encode()
                ctype = "text/html"
            elif u.path == "/sdk.js":
                body = SDK.encode()
                ctype = "application/javascript"
            elif u.path == "/plugin.js":
                body = (plugin or (ROOT / "desktop" / "plugin.js")).read_bytes()
                ctype = "application/javascript"
            elif u.path == "/api/plugins/antemuse/state":
                from dashboard import plugin_api
                q = urllib.parse.parse_qs(u.query)
                try:
                    payload = plugin_api.state(
                        None,
                        with_graph=int((q.get("graph") or ["0"])[0]),
                        stills=int((q.get("stills") or ["1"])[0]),
                        session=None)
                    if (q.get("graph") or ["0"])[0] in ("1", "true", "True"):
                        payload["graph"] = plugin_api.graph()
                    body = json.dumps(payload).encode()
                    ctype = "application/json"
                except Exception as exc:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(str(exc).encode())
                    return
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def count(path: Path, width: int, height: int) -> dict:
    from PIL import Image
    im = Image.open(path).convert("RGB")
    px = im.load()
    out = {"relation": 0, "path": 0, "lit": 0, "pixels": width * height}
    for y in range(im.height):
        for x in range(im.width):
            r, g, b = px[x, y]
            if r > 150 and 100 < g < 200 and b < 130:
                out["path"] += 1          # warm trail / activation
            if r > 120 and g > 80 and b < 100:
                out["lit"] += 1           # firing nodes and their halos
            if b > r + 6 and 20 <= b <= 110:
                out["relation"] += 1      # bluish low-alpha relations
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=90)
    ap.add_argument("--size", default="700x746")
    ap.add_argument("--out", default="")
    ap.add_argument("--plugin", default="", help="pane file to measure (default: the repo's)")
    args = ap.parse_args()
    width, height = (int(v) for v in args.size.lower().split("x"))
    out = Path(args.out or (Path.home() / ".cache/antemuse" / "pane-pixels.png"))
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("cannot measure: playwright is not installed (pip install playwright && "
              "playwright install chromium)")
        return 2

    os.environ.setdefault("ANTEMUSE_STATES_HOME", str(Path.home() / ".hermes/plugin-data/antemuse"))
    sys.path.insert(0, str(ROOT))
    httpd = serve("", width, height, Path(args.plugin) if args.plugin else None)
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
            p = b.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
            p.goto(f"http://127.0.0.1:{PORT}/index.html")
            p.wait_for_selector("canvas", timeout=20000)
            p.wait_for_function(
                "() => { const a = window.__antemuse || {}; const g = a.g3s || {};"
                f" const k = Object.keys(g)[0]; return !!(k && g[k] && g[k].frames > {args.frames}) }}",
                timeout=60000)
            probe = p.evaluate(
                "() => { const a = window.__antemuse || {}; const g = a.g3s || {};"
                " const k = Object.keys(g)[0]; return (k && g[k]) || {} }")
            p.screenshot(path=str(out))
            b.close()
    finally:
        httpd.shutdown()

    counts = count(out, width, height)
    edges = int(probe.get("edges") or 0)
    links = int(probe.get("linksN") or 0)
    print(f"pane {width}x{height} · frames {probe.get('frames')} · nodes {probe.get('nodes')} · "
          f"edges {edges} · linksN {links} · litN {probe.get('litN')}")
    ink = int(probe.get("ink") or 0)
    print(f"edge ink {ink} px² of stroke · culled {probe.get('culled')} · "
          f"screenshot classes: relation {counts['relation']} · path {counts['path']} · "
          f"lit {counts['lit']} of {counts['pixels']}")
    print(f"screenshot {out}")
    if not edges:
        print("no edges in the pane's own buffer: nothing was built from the payload")
        return 1
    if counts["relation"] == 0:
        print("edges exist in the buffer but no relation pixel reached the framebuffer")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
