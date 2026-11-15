#!/usr/bin/env python3
"""Record a short screen video of the cockpit pane's real renderer.

Uses the same stubs as tools/cockpit_harness.py: the shipped desktop/plugin.js is
imported with @hermes/plugin-sdk, react and react/jsx-runtime mapped to local
stand-ins, and createCockpit is driven on a real canvas. The graph payload is
synthetic (the live /graph route needs the gateway cookie), and the page says so
on screen for the whole recording.

Out: /tmp/cockpit-video/cockpit.webm, then contacts ffmpeg via --encode.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cockpit_harness as H  # stubs + payload generator, no side effects on import

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "desktop" / "plugin.js"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/cockpit-video/cockpit.webm")
OUT.parent.mkdir(parents=True, exist_ok=True)

PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<script type="importmap">
{"imports": {
  "@hermes/plugin-sdk": "./sdk.js",
  "react": "./react.js",
  "react/jsx-runtime": "./jsx.js"
}}
</script>
<style>
:root{
  --ui-text-secondary:#d9d3c8; --ui-text-quaternary:#8b857a;
  --ui-stroke-secondary:#3b3b3b; --ui-accent:#d2643f; --ui-panel-background:#131313;
}
html,body{margin:0;height:100%;background:#0e0e0e;font-family:ui-sans-serif,system-ui,sans-serif}
#box{position:fixed;inset:0}
#cv{position:absolute;inset:0;width:100%;height:100%;display:block;cursor:crosshair;touch-action:none}
#title{
  position:absolute;left:50%;top:44%;transform:translate(-50%,-50%);text-align:center;
  color:#e8e1d5;letter-spacing:.14em;text-transform:uppercase;font-size:15px;
  transition:opacity 900ms ease;pointer-events:none;
}
#title b{display:block;font-size:30px;letter-spacing:.04em;margin-bottom:.5rem;text-transform:none}
#title span{color:#8b857a;font-size:12px}
#caption{
  position:absolute;right:14px;bottom:10px;color:#6d6a63;
  font:10px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.06em;text-transform:uppercase;
}
</style>
</head>
<body>
<div id="box"><canvas id="cv" tabindex="0"></canvas></div>
<div id="title"><b>antemuse · cockpit</b><span>harness run · synthetic graph payload · real pane code</span></div>
<div id="caption">harness · synthetic payload</div>
<script>
  // The recording drives drag-look, not pointer capture: synthetic absolute
  // mouse moves under pointer lock arrive as large relative deltas and would
  // fling the pitch. The captured path is covered by the static tests instead.
  Element.prototype.requestPointerLock = function () { return Promise.resolve() }
</script>
<script src="./graph.js"></script>
<script type="module">
import { createCockpit } from './plugin.js'
window.__errors = []
window.addEventListener('error', (e) => window.__errors.push(String(e.message)))
window.__start = () => {
  const payload = window.__makeGraph(700)
  window.__payload = payload
  window.__cockpit = createCockpit({
    ctx: { rest: () => Promise.resolve(payload), setInterval: (fn, ms) => setInterval(fn, ms) },
    el: document.getElementById('cv'),
    callbacks: {
      onCatch: (list) => { window.__caught = list.map(n => n.l) },
      onTarget: (node) => { window.__locked = node ? node.l : null }
    }
  })
  return true
}
window.__ready = true
</script>
</body></html>
"""


def serve(directory: Path):
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/index.html"


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="cockpit-video-"))
    try:
        shutil.copy(PLUGIN, tmp / "plugin.js")
        (tmp / "sdk.js").write_text(H.SDK_STUB)
        (tmp / "react.js").write_text(H.REACT_STUB)
        (tmp / "jsx.js").write_text(H.JSX_STUB)
        (tmp / "graph.js").write_text(H.PAYLOAD_JS)
        (tmp / "index.html").write_text(PAGE)

        httpd, url = serve(tmp)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--force-device-scale-factor=1"])
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 760},
                record_video_dir=str(OUT.parent),
                record_video_size={"width": 1280, "height": 760},
            )
            page = ctx.new_page()
            page.goto(url, wait_until="load")
            page.wait_for_function("window.__ready === true")
            page.evaluate("window.__start()")
            page.wait_for_timeout(1500)
            page.evaluate("document.getElementById('title').style.opacity = '0'")
            page.wait_for_timeout(400)

            # look around, from the knot the ship starts in
            page.mouse.move(640, 380)
            page.mouse.down()
            page.mouse.move(742, 368, steps=22)
            page.mouse.up()
            page.wait_for_timeout(400)

            def on_screen(min_x=140, max_x_off=140):
                return page.evaluate("""(minX) => {
                    for (let i = 0; i < 700; i++) {
                      const s = __cockpit.screenOf('concept-' + i)
                      if (s && s.x > minX && s.y > 120 && s.x < innerWidth - 140 && s.y < innerHeight - 190) {
                        return { label: 'concept-' + i, s }
                      }
                    }
                    return null
                }""", min_x)

            def spot_for(exclude=None, sep=0.0):
                """The farthest shootable concept on screen: shots then travel."""
                return page.evaluate(
                    """([exLabel, exX, exY, sep]) => {
                        let best = null
                        for (let i = 0; i < 700; i++) {
                          const label = 'concept-' + i
                          if (label === exLabel) continue
                          const s = __cockpit.screenOf(label)
                          if (!s || s.z <= 0.05) continue
                          if (s.x < 150 || s.y < 130 || s.x > innerWidth - 150 || s.y > innerHeight - 210) continue
                          if (sep && Math.hypot(s.x - exX, s.y - exY) < sep) continue
                          if (!best || s.scale < best.scale) best = { label, x: s.x, y: s.y, scale: s.scale }
                        }
                        return best && { label: best.label, x: best.x, y: best.y }
                    }""",
                    [exclude[0] if exclude else None, exclude[1] if exclude else 0,
                     exclude[2] if exclude else 0, sep],
                )

            def look_toward():
                page.mouse.move(700, 380)
                page.mouse.down()
                page.mouse.move(660, 372, steps=10)
                page.mouse.up()
                page.wait_for_timeout(220)

            # hold the trigger: a stream of shots walks across the field
            first = spot_for()
            for _ in range(3):
                if first:
                    break
                look_toward()
                first = spot_for()
            if first:
                page.mouse.move(first["x"], first["y"])
                page.mouse.down()
                page.wait_for_timeout(700)
                page.mouse.move(first["x"] + 18, first["y"] - 6, steps=8)
                page.wait_for_timeout(600)
                page.mouse.up()
            page.wait_for_timeout(450)
            print("picks:", page.evaluate("__cockpit.picks()"))
            print("shots/picks:", page.evaluate("__cockpit.stats().shots"), page.evaluate("__cockpit.stats().picks"))

            # a burst into open sky, so the bullets themselves are on camera:
            # fire, confirm they are alive, and shoot the still in that same beat
            page.mouse.move(430, 190)
            page.mouse.down()
            page.wait_for_timeout(560)
            alive = page.evaluate("__cockpit.stats().bullets")
            page.screenshot(path="/tmp/fire-mid.png")
            print("mid-flight bullets:", alive, page.evaluate("__cockpit.bulletScreen()"))
            page.wait_for_timeout(240)
            page.mouse.up()

            # the net still gathers a whole knot in one throw
            page.keyboard.press(" ")
            page.wait_for_timeout(1300)
            print("caught:", page.evaluate("window.__caught || []"))

            # bank the ship: the horizon and the whole cloud tilt with it
            page.keyboard.down("d")
            page.wait_for_timeout(430)
            page.keyboard.up("d")
            page.wait_for_timeout(250)

            # thrust out of the knot, easing the nose with a short drag, then
            # cut the throttle and coast — the ship keeps its momentum
            page.keyboard.down("w")
            page.wait_for_timeout(800)
            page.mouse.move(700, 380)
            page.mouse.down()
            page.mouse.move(688, 392, steps=10)
            page.mouse.up()
            page.wait_for_timeout(600)
            page.keyboard.up("w")
            page.wait_for_timeout(800)

            # roll back toward level and let it drift
            page.keyboard.down("a")
            page.wait_for_timeout(430)
            page.keyboard.up("a")
            page.wait_for_timeout(900)
            print("locked:", page.evaluate("window.__locked"))
            print("errors:", page.evaluate("window.__errors"))
            print("stats:", json.dumps(page.evaluate("__cockpit.stats()")))

            video = page.video
            assert video is not None, "no video handle: the context was not recording"
            ctx.close()          # finalizes the recording
            browser.close()
            saved = Path(video.path())
            shutil.copy(saved, OUT)
            print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
        httpd.shutdown()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
