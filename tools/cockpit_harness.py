#!/usr/bin/env python3
"""Drive the cockpit pane's renderer in a real browser, without the desktop app.

The desktop half is one ES module that the host loads with only
``@hermes/plugin-sdk`` and ``react`` resolvable, so this harness reproduces that
environment with an import map and stub modules, imports the shipped
``desktop/plugin.js``, and calls the exported ``createCockpit`` on a real canvas
with a synthetic ``/graph`` payload.

What it proves: the payload is normalized and drawn, the canvas tracks its box,
throttle moves the ship, the net resolves to a den of nodes, clicking locks one,
and destroy() leaves nothing running. What it cannot prove: how the app lays the
pane out, which is the host's business.

Run:  /usr/bin/python3 tools/cockpit_harness.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import textwrap
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "desktop" / "plugin.js"

SDK_STUB = """
export const PANES_AREA = 'panes'
export const TITLEBAR_AREAS = { center: 'titlebar.center' }
export const ROUTES_AREA = 'routes'
export const SIDEBAR_NAV_AREA = 'sidebar.nav'
export const STATUSBAR_AREAS = { right: 'statusBar.right', left: 'statusBar.left' }
export const PALETTE_AREA = 'palette'
export const KEYBINDS_AREA = 'keybinds'
export const pluginSettingsHref = () => '#settings'
export const host = {
  state: {
    focusedSessionId: { get: () => 'session-test', listen: () => () => {} },
    busy: { get: () => false, listen: () => () => {} },
    cwd: { get: () => '/tmp' },
    gateway: { get: () => null },
    model: { get: () => null },
    profile: { get: () => 'default' },
    viewport: { get: () => ({}) }
  },
  request: () => Promise.reject(new Error('no gateway in harness')),
  onEvent: () => () => {},
  notify: () => {},
  navigate: () => {},
  logs: () => {},
  status: () => ({}),
  requestFullTools: () => Promise.resolve([])
}
export const useValue = (atom) => (atom && atom.get ? atom.get() : undefined)
export const usePluginI18n = () => (key) => key
export const atom = (v) => ({ get: () => v, set: () => {}, listen: () => () => {} })
export const computed = (fn) => ({ get: fn, listen: () => () => {} })
export const cx = (...a) => a.filter(Boolean).join(' ')
export const jsx = () => null
export const Contribute = () => null
export const Button = 'button'
export const Badge = 'span'
export const Kbd = 'kbd'
export const GlyphSpinner = () => null
export const icons = {}
export const useQuery = () => ({ data: null })
export const useMutation = () => ({ mutate: () => {} })
"""

REACT_STUB = """
export const useEffect = (fn) => { try { const off = fn(); return off } catch (e) { return undefined } }
export const useRef = (v) => ({ current: v })
export const useState = (v) => [v, () => {}]
export const useMemo = (fn) => fn()
export const useCallback = (fn) => fn
export const createElement = () => null
export default { useEffect, useRef, useState, useMemo, useCallback }
"""

JSX_STUB = """
export const jsx = (type, props) => ({ type, props })
export const jsxs = (type, props) => ({ type, props })
export const Fragment = 'fragment'
"""

PAYLOAD_JS = """
window.__makeGraph = (count) => {
  const nodes = []
  // three knots plus a sparse tail, so the cockpit has something to fly between
  const knots = [[0.4, 0.2, 0.3], [-0.5, -0.2, -0.4], [0.1, -0.5, 0.6]]
  for (let i = 0; i < count; i++) {
    const k = knots[i % knots.length]
    const spread = i < count * 0.7 ? 0.12 : 0.6
    nodes.push({
      l: 'concept-' + i,
      x: k[0] + (Math.sin(i * 2.3) * spread),
      y: k[1] + (Math.cos(i * 1.7) * spread),
      z: k[2] + (Math.sin(i * 0.9) * spread),
      w: i % 11 === 0 ? 0.8 : 0,
      v: (i % 7) / 7
    })
  }
  const links = []
  for (let i = 0; i < Math.min(60, count - 1); i++) links.push({ a: 'concept-' + i, b: 'concept-' + (i + 1), w: 2 })
  return { key: 'walk', nodes, links, path: ['concept-0', 'concept-1', 'concept-2', 'concept-3'], lit: nodes.filter(n => n.w > 0.05).length }
}
"""

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
/* stand in for the app's theme so the pane's colour resolution is exercised */
:root{
  --ui-text-secondary:#d9d3c8; --ui-text-quaternary:#8b857a;
  --ui-stroke-secondary:#3b3b3b; --ui-accent:#d2643f; --ui-panel-background:#131313;
}
html,body{margin:0;height:100%;background:#0e0e0e}
#box{width:900px;height:560px;position:relative}
/* the pane styles the canvas this way; without it a canvas feeds its own
   width attribute back into its layout box */
#cv{position:absolute;inset:0;width:100%;height:100%;display:block}
</style>
</head>
<body>
<div id="box"><canvas id="cv" tabindex="0"></canvas></div>
<script type="module">
import plugin from './plugin.js'
import { createCockpit } from './plugin.js'
window.__plugin = plugin
window.__errors = []
window.addEventListener('error', (e) => window.__errors.push(String(e.message)))
const log = []
for (const k of Object.keys(plugin || {})) log.push(k)
window.__exports = log
// The packaged app refuses pointer lock with WrongDocumentError ("the root document of this
// element is not valid for pointer lock"), so the harness refuses it too: otherwise headless
// Chromium grants the lock and the captured-steering path is never exercised.
HTMLCanvasElement.prototype.requestPointerLock = function () {
  return Promise.reject(new DOMException('The root document of this element is not valid for pointer lock.', 'WrongDocumentError'))
}
window.__mk = (opts) => {
  const payload = window.__makeGraph((opts && opts.count) || 120)
  const cv = document.getElementById('cv')
  const cockpit = createCockpit({
    ctx: { rest: (path, opts) => {
      // the host's REST door: a POST is recorded, a GET answers with the graph
      if (opts && opts.method === 'POST') { (window.__restPosts = window.__restPosts || []).push({ path, body: opts.body }); return Promise.resolve({ ok: true }) }
      return Promise.resolve(payload)
    }, setInterval: (fn, ms) => setInterval(fn, ms), navigate: () => {} },
    el: cv,
    callbacks: {
      onCatch: (list) => { window.__caught = list.map(n => n.l) },
      onTarget: (node) => { window.__locked = node ? node.l : null },
      onFlight: (left) => { (window.__flights = window.__flights || []).push(left) },
      onExit: () => { window.__exited = (window.__exited || 0) + 1 }
    }
  })
  window.__cockpit = cockpit
  return cockpit
}
window.__ready = true
</script>
</body></html>
"""


def serve(directory: Path) -> tuple[ThreadingHTTPServer, str]:
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/index.html"


results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail else ''}", flush=True)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="cockpit-harness-"))
    try:
        shutil.copy(PLUGIN, tmp / "plugin.js")
        (tmp / "sdk.js").write_text(SDK_STUB)
        (tmp / "react.js").write_text(REACT_STUB)
        (tmp / "jsx.js").write_text(JSX_STUB)
        (tmp / "graph.js").write_text(PAYLOAD_JS)
        (tmp / "index.html").write_text(PAGE.replace("<script type=\"module\">", "<script src=\"./graph.js\"></script>\n<script type=\"module\">"))

        httpd, url = serve(tmp)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1200, "height": 800}, device_scale_factor=2)
            errors: list[str] = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            # The pane files what it shoots with the plugin (`POST …/picks`). This server is
            # a static one, so the request is answered here and kept for a check: without
            # it the pane's own POST 501s and the console-error check fails for a reason
            # that has nothing to do with the cockpit.
            page.add_init_script("""
              (() => {
                const real = window.fetch.bind(window)
                window.__posted = []
                window.fetch = (url, opts) => {
                  if (String(url).indexOf('/picks') !== -1) {
                    try { window.__posted.push(JSON.parse((opts && opts.body) || '{}')) } catch (e) {}
                    return Promise.resolve(new Response('{"ok":true}', { status: 200 }))
                  }
                  return real(url, opts)
                }
              })()
            """)
            page.goto(url, wait_until="load")
            page.wait_for_function("window.__ready === true", timeout=10_000)

            check("module: the shipped plugin.js parses and registers a default export",
                  page.evaluate("!!window.__plugin && !!window.__plugin.register"), "")
            check("module: createCockpit is exported for the harness",
                  page.evaluate("(async () => { const m = await import('./plugin.js'); return typeof m.createCockpit === 'function' })()"))
            check("module: no load errors", not errors, "; ".join(errors[:3]))

            # The pane's own counts line, for the one state that has no dose: `/explore` must
            # read "3 picked · you end it", never "0 picks to go" — a countdown to nothing reads
            # as already finished.
            line = page.evaluate(
                "(async () => { const m = await import('./plugin.js');"
                " return m.counts({active: {dose: 0, unit: 'picks', served: 3, tools: {mode: 'all'}}}); })()")
            check("pane: an open-ended state says you end it",
                  "you end it" in line and "to go" not in line, line)

            page.evaluate("window.__mk({count: 120})")
            page.wait_for_timeout(400)
            stats = page.evaluate("__cockpit.stats()")
            check("data: payload is normalized into the cockpit", stats["nodes"] == 120, f"nodes={stats['nodes']}")
            check("data: lit count survives", stats["lit"] == 11, f"lit={stats['lit']}")
            check("data: the walk trail is carried", stats["path"] == 4, f"path={stats['path']}")

            # canvas tracks its box (attributes, not CSS)
            box = page.evaluate("(() => { const c=document.getElementById('cv'); return {w:c.width,h:c.height,cw:c.clientWidth,ch:c.clientHeight}; })()")
            check("canvas: backing store follows the pane box", box["w"] == box["cw"] * 2 and box["h"] == box["ch"] * 2,
                  f"{box}")

            # something was actually painted
            painted = page.evaluate("""() => {
                // sample a window, not the whole backing store: a dpr-2 canvas
                // this size is tens of megabytes and getImageData OOMs on it
                const c = document.getElementById('cv');
                const w = Math.min(c.width, 600), h = Math.min(c.height, 400);
                const d = c.getContext('2d').getImageData(0, 0, w, h).data;
                let n = 0;
                for (let i = 3; i < d.length; i += 4) if (d[i] > 8) n++;
                return n;
            }""")
            check("render: the glass has ink on it", painted > 500, f"{painted} opaque px")

            # throttle moves the ship along its heading
            before = page.evaluate("__cockpit.stats().cam")
            page.evaluate("__cockpit.key('w')")
            # the ship is deliberately slow (a third of a unit per second): a
            # half-second tap only nudges it, so hold long enough to measure
            page.wait_for_timeout(1400)
            page.evaluate("__cockpit.unkey('w')")
            page.wait_for_timeout(120)
            after = page.evaluate("__cockpit.stats().cam")
            moved = sum((after[k] - before[k]) ** 2 for k in "xyz") ** 0.5
            check("flight: W moves the ship", moved > 0.05, f"moved {moved:.2f}")

            # resize: the backing store must follow, or the pane blurs/stretches
            page.evaluate("document.getElementById('box').style.width = '520px'")
            page.wait_for_timeout(300)
            resized = page.evaluate("(() => { const c=document.getElementById('cv'); return {w:c.width,cw:c.clientWidth,h:c.height}; })()")
            check("canvas: ResizeObserver refits the backing store", resized["w"] == resized["cw"] * 2, f"{resized}")

            # shooting: hold the trigger, bullets travel, arrivals raise interest
            page.evaluate("__cockpit.home()")
            # the canvas is smaller than the page: a point has to land inside the
            # element, or the click goes to the page and nothing fires
            spot = page.evaluate("""() => {
                const r = document.getElementById('cv').getBoundingClientRect()
                for (let i = 0; i < 900; i++) {
                  const s = __cockpit.screenOf('concept-' + i)
                  if (s && s.x > r.left + 40 && s.y > r.top + 40
                      && s.x < r.right - 40 && s.y < r.bottom - 80) {
                    return { label: 'concept-' + i, s }
                  }
                }
                return null
            }""")
            if spot:
                before = page.evaluate("__cockpit.stats().shots")
                # a click captures the pointer, and captured fire aims at the
                # reticle. Release first so the shot can be aimed with the pointer.
                page.keyboard.press("Escape")
                page.wait_for_timeout(80)
                page.mouse.move(spot["s"]["x"], spot["s"]["y"])
                page.mouse.down()
                page.wait_for_timeout(420)
                mid = page.evaluate("__cockpit.stats()")
                check("shoot: holding fires a stream", mid["shots"] >= before + 2, f"shots={mid['shots']}")
                check("shoot: shots exist in flight", mid["bullets"] > 0, f"bullets={mid['bullets']}")
                check("shoot: the trigger is held", mid["firing"] is True, f"firing={mid['firing']}")
                # Capture without pointer lock: the browser may refuse the lock, and the pane
                # used to be unsteerable when it did. Holding the button must steer the ship
                # and must own the pointer, or "the mouse does nothing" is the only report a
                # person can give.
                check("look: holding owns the pointer", mid["pointer"] is True, f"pointer={mid['pointer']}")
                page.mouse.up()
                # The way out is behaviour, not a string in a file: Escape must ask the pane to
                # be left, and must not leave the trigger on. A test that only looked for the
                # word "onExit" stayed green with this call deleted.
                exited = page.evaluate("window.__exited || 0")
                page.keyboard.press("Escape")
                page.wait_for_timeout(120)
                after = page.evaluate("__cockpit.stats()")
                # Escape returns the mouse and nothing else: capture is sticky, so this is the
                # only key that gives the cursor back without ending the flight.
                check("escape: the mouse is handed back", after["pointer"] is False, f"pointer={after['pointer']}")
                check("escape: it does not leave",
                      page.evaluate("window.__exited || 0") == exited,
                      f"__exited={page.evaluate('window.__exited || 0')}")
                check("escape: it stops the trigger", after["firing"] is False, f"firing={after['firing']}")
                check("escape: it files nothing", not page.evaluate("window.__flights || []"),
                      f"flights={page.evaluate('window.__flights || []')}")

                # Capture is sticky: a press takes the mouse and releasing the button must not
                # give it back. Steering that needs the button held is what a person reports
                # as "the mouse does nothing".
                box = page.evaluate("(() => { const r = document.querySelector('canvas').getBoundingClientRect();"
                                    " return { x: r.x, y: r.y, w: r.width, h: r.height } })()")
                cx, cy = box["x"] + box["w"] / 2, box["y"] + box["h"] / 2
                page.mouse.move(cx, cy)
                page.mouse.down()
                page.wait_for_timeout(120)
                page.mouse.up()
                page.wait_for_timeout(120)
                check("look: the press keeps the pointer", page.evaluate("__cockpit.stats().pointer") is True,
                      "released the capture on mouseup")
                y0 = page.evaluate("__cockpit.stats().cam.yaw")
                page.mouse.move(cx + 150, cy + 40, steps=6)
                page.wait_for_timeout(120)
                y1 = page.evaluate("__cockpit.stats().cam.yaw")
                check("look: moving with no button held still turns the ship",
                      abs(y1 - y0) > 0.05, f"{y0:.3f} -> {y1:.3f}")
                page.keyboard.press("Escape")
                page.wait_for_timeout(100)
                page.wait_for_timeout(1400)
                st = page.evaluate("__cockpit.stats()")
                picks = page.evaluate("__cockpit.picks()")
                check("shoot: the trigger releases", st["firing"] is False, f"firing={st['firing']}")
                # Steering is proven in the running app rather than here: headless Chromium
                # grants pointer lock, which reports movementX itself and is a different path
                # from the captured one this pane has to carry when a host refuses the lock.
                check("shoot: an arriving shot picks a concept", st["picks"] >= 1, f"picks={st['picks']}")
                filed = page.evaluate("(window.__restPosts || []).filter(p => p.path === '/picks').flatMap(p => (p.body && p.body.picks) || [])")
                check("shoot: the picks are filed with the plugin", len(filed) >= 1,
                      f"posted={filed[:4]}")
                check("shoot: interest accumulates on the target", picks and picks[0]["hits"] >= 1,
                      f"{picks[0] if picks else None}")
                # a genuinely empty patch of glass: nothing drawn within 40px
                empty = page.evaluate("""() => {
                    const taken = []
                    for (let i = 0; i < 700; i++) {
                      const s = __cockpit.screenOf('concept-' + i)
                      if (s) taken.push(s)
                    }
                    for (let y = 30; y < innerHeight - 220; y += 20) {
                      for (let x = 30; x < innerWidth - 30; x += 20) {
                        if (taken.every((s) => Math.hypot(s.x - x, s.y - y) > 90)) return [x, y]
                      }
                    }
                    return [4, 4]
                }""")
                page.evaluate("([x, y]) => __cockpit.fire(x, y)", empty)
                page.wait_for_timeout(1200)
                st2 = page.evaluate("__cockpit.stats()")
                check("shoot: a shot fired at nothing picks nothing new",
                      st2["picks"] == st["picks"], f"picks={st2['picks']}")
            else:
                check("shoot: holding fires a stream", False, "no concept was on screen to shoot")

            # a ship banks: D rolls it, and the roll reaches the projection
            page.evaluate("__cockpit.home()")
            page.evaluate("__cockpit.key('d')")
            page.wait_for_timeout(420)
            page.evaluate("__cockpit.unkey('d')")
            roll = page.evaluate("__cockpit.stats().cam.roll")
            check("flight: D banks the ship", abs(roll) > 0.15, f"roll {roll:.2f} rad")

            # and it coasts: cut the throttle and it keeps moving
            page.evaluate("__cockpit.home()")
            page.evaluate("__cockpit.key('w')")
            page.wait_for_timeout(450)
            page.evaluate("__cockpit.unkey('w')")
            page.wait_for_timeout(120)
            p1 = page.evaluate("__cockpit.stats().cam")
            page.wait_for_timeout(900)
            p2 = page.evaluate("__cockpit.stats().cam")
            coast = sum((p2[k] - p1[k]) ** 2 for k in "xyz") ** 0.5
            check("flight: it coasts after the throttle is cut", coast > 0.01, f"coasted {coast:.3f}")

            # the net lands on structure
            page.evaluate("__cockpit.home(); __cockpit.draw()")
            page.evaluate("__cockpit.resolveNet()")
            page.wait_for_timeout(150)
            caught = page.evaluate("__cockpit.stats().catchCount")
            caught_list = page.evaluate("window.__caught || []")
            check("net: resolves to a set of concepts", caught > 0, f"caught={caught}")
            check("net: the caught list reaches the pane", isinstance(caught_list, list) and len(caught_list) == caught,
                  f"{len(caught_list)} labels")

            # clicking a concept fires at it: the shot is the interaction, so a
            # click must produce a shot aimed at that direction, not a selection.
            found = page.evaluate("""() => {
                const r = document.getElementById('cv').getBoundingClientRect()
                for (let i = 0; i < 900; i++) {
                  const label = 'concept-' + i
                  const s = __cockpit.screenOf(label)
                  if (s && s.x > r.left + 40 && s.y > r.top + 40
                      && s.x < r.right - 40 && s.y < r.bottom - 80) return { label, s }
                }
                return null
            }""")
            if found:
                before = page.evaluate("__cockpit.stats().shots")
                page.keyboard.press("Escape")
                page.wait_for_timeout(80)
                page.mouse.move(found["s"]["x"], found["s"]["y"])
                page.mouse.down()
                page.wait_for_timeout(60)
                page.mouse.up()
                page.wait_for_timeout(60)
                after = page.evaluate("__cockpit.stats().shots")
                check("shoot: a click fires at the pointer", after > before, f"{before} -> {after}")
            else:
                check("shoot: a click fires at the pointer", False, "the node was behind the ship")

            shot = os.environ.get("COCKPIT_SHOT")
            if shot:
                page.screenshot(path=shot)
                print(f"shot: {shot}")

            # leaving: the flight is handed over, not thrown away. A cockpit that closes
            # silently is a cockpit whose work was wasted.
            page.evaluate("__cockpit.home()")
            page.wait_for_timeout(250)
            target = page.evaluate("""() => {
                const r = document.getElementById('cv').getBoundingClientRect()
                for (let i = 0; i < 900; i++) {
                  const s = __cockpit.screenOf('concept-' + i)
                  if (s && s.x > r.left + 40 && s.y > r.top + 40 && s.x < r.right - 40 && s.y < r.bottom - 40) {
                    return { label: 'concept-' + i, x: s.x, y: s.y }
                  }
                }
                return null
            }""")
            if target:
                page.mouse.move(target["x"], target["y"])
                page.mouse.down()
                page.wait_for_timeout(200)
                page.mouse.up()
                page.wait_for_timeout(150)
                # The button in the pane is the exit, and it is not in this DOM: what this
                # harness can hold is that the flight is still there to be taken, with the label
                # that was hit. The button's own wiring is asserted in tools/desktop_harness.
                taken = page.evaluate("__cockpit.takeFlight()")
                check("exit: the trail is waiting to be taken",
                      target["label"] in (taken.get("trail") or []), f"trail={taken.get('trail')}")
                check("exit: taking it empties it", not page.evaluate("__cockpit.takeFlight().trail"), "trail kept")

            # frames stop after destroy
            page.evaluate("__cockpit.destroy()")
            page.wait_for_timeout(200)
            frames_a = page.evaluate("__cockpit.stats().frames")
            page.wait_for_timeout(400)
            frames_b = page.evaluate("__cockpit.stats().frames")
            check("lifecycle: destroy() stops the loop", frames_a == frames_b, f"{frames_a} -> {frames_b}")
            check("lifecycle: no errors during the run", not errors, "; ".join(errors[:4]))

            browser.close()
        httpd.shutdown()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
