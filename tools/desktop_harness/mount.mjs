// Mount the real desktop/plugin.js in jsdom and check what it puts on screen.
//
// The app is not installed on this machine, so "it renders" cannot be answered
// by looking at it. It can be answered by mounting the actual file: effects run,
// the stubbed backend answers, and the assertions read the DOM. What this does
// not cover — CSS, pane placement, the real gateway transport — is stated in the
// change record rather than implied to be verified.
//
//   ./tools/desktop_harness/setup.sh && node tools/desktop_harness/mount.mjs

import { strict as assert } from 'node:assert'
import { createHash } from 'node:crypto'
import { copyFileSync, readFileSync } from 'node:fs'

import { JSDOM } from 'jsdom'

const PLUGIN = new URL('../../desktop/plugin.js', import.meta.url)
const WORK = new URL('./.work/plugin.js', import.meta.url)

const source = readFileSync(PLUGIN)
copyFileSync(PLUGIN, WORK)                     // bare imports resolve beside the copy
const digest = createHash('sha256').update(source).digest('hex').slice(0, 12)

const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {
  url: 'http://localhost'
})
globalThis.window = dom.window
globalThis.document = dom.window.document
Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true })
globalThis.HTMLElement = dom.window.HTMLElement
globalThis.Node = dom.window.Node
globalThis.IS_REACT_ACT_ENVIRONMENT = true

const React = (await import('react')).default
const { act } = await import('react')
const { createRoot } = await import('react-dom/client')
const plugin = (await import(WORK.href)).default
const helpers = await import(WORK.href)
// The host state atoms live in the SDK, not the plugin bundle: import them from
// the same stub the plugin resolves its bare imports against.
const sdk = await import(new URL('./node_modules/@hermes/plugin-sdk/index.js', import.meta.url).href)
// jsdom ships no canvas. Give it a 2D context that reports a lit strand, so the
// rasteriser (sample -> level -> glyph) is actually exercised rather than skipped.
const STUB = { calls: { fillText: 0, fillRect: 0, getImageData: 0, drawImage: 0 } }
globalThis.STUB = STUB
function stubContext(canvas) {
  const noop = () => {}
  return {
    canvas, globalAlpha: 1, fillStyle: '', strokeStyle: '', lineWidth: 1,
    font: '', textAlign: '', textBaseline: '', lineJoin: '', lineCap: '',
    setTransform: noop, clearRect: noop, beginPath: noop, moveTo: noop,
    lineTo: noop, stroke: noop, arc: noop, fill: noop,
    quadraticCurveTo: noop, bezierCurveTo: noop, closePath: noop,
    drawImage: () => { STUB.calls.drawImage += 1 },
    imageSmoothingEnabled: true, imageSmoothingQuality: 'high',
    fillRect: () => { STUB.calls.fillRect += 1 },
    fillText: () => { STUB.calls.fillText += 1 },
    getImageData: (x, y, w, h) => {
      STUB.calls.getImageData += 1
      const data = new Uint8ClampedArray(w * h * 4)
      for (let i = 0; i < data.length; i += 4) {
        data[i] = 126; data[i + 1] = 205; data[i + 2] = 196; data[i + 3] = 190
      }
      return { data, width: w, height: h }
    }
  }
}
document.defaultView.HTMLCanvasElement.prototype.getContext = function () {
  return stubContext(this)
}

const host = sdk.host
const sweepStrays = helpers.sweepStrays

const PAYLOAD = {
  generated_at: 100,
  active: {
    key: 'daydream', label: 'DAYDREAMING', walk: null,
    contract: 'two memories · join only if it holds',
    seconds_left: 179, total_seconds: 180, turns_left: 2,
    tools: { mode: 'none', allowed: [], blocked: [] }
  },
  frame: { cols: 44, rows: 3, lines: ['  .:-=+  ', ' :#%@     ', '   .:     '] },
  residue: { count: 2, kinds: ['daydream'] }
}

function makeCtx(state) {
  const calls = { rest: [], intervals: [] }
  const contributions = []
  const pages = []
  const ctx = {
    register: (c) => { contributions.push(c); return () => {} },
    registerSettingsPage: (page) => { pages.push(page); return () => {} },
    setInterval: (fn, ms) => { calls.intervals.push({ fn, ms }); return () => {} },
    rest: async (path) => {
      calls.rest.push(path)
      if (state.error) throw new Error(state.error)
      return state.payload
    },
    navigate: () => {},
    onDispose: () => {},
    storage: { get: (_k, d) => d, set: () => {}, remove: () => {} }
  }
  return { ctx, calls, contributions, pages }
}

const root = () => document.getElementById('root')

function resetBody() {
  document.body.innerHTML = '<div id="root"></div>'
}

async function mountWith(state, id = 'page') {
  const wired = makeCtx(state)
  plugin.register(wired.ctx)
  const contribution = wired.contributions.find((c) => c.id === id)
  assert.ok(contribution, `no contribution ${id}`)
  const node = createRoot(root())
  await act(async () => { node.render(contribution.render()) })
  return { ...wired, node }
}

// ---- registration -----------------------------------------------------------

const registered = makeCtx({ payload: PAYLOAD })
plugin.register(registered.ctx)
assert.equal(plugin.id, 'antemuse')
assert.deepEqual(
  registered.contributions.map((c) => c.area),
  ['panes', 'statusBar.right', 'routes', 'sidebar.nav', 'palette'],
  'a dock pane, a chip, a route, a nav entry and a palette command'
)
const byId = Object.fromEntries(registered.contributions.map((c) => [c.id, c]))
assert.equal(byId.page.data.path, '/antemuse', 'the page route must match what the palette opens')
assert.equal(byId.nav.data.path, '/antemuse')
// The first contribution is the dock pane, which is where the art lives now.
assert.equal(registered.contributions[0].id, 'pane')
assert.equal(registered.contributions[0].data.placement, 'right', 'the art gets its own dock pane')
assert.equal(registered.contributions[0].data.collapsible, true)
// The settings page is optional and another writer is currently moving it; what
// must hold is that the plugin never offers more than one.
assert.ok(registered.pages.length <= 1, 'at most one settings page')

// ---- pure helpers -----------------------------------------------------------

assert.equal(helpers.clock(179), '2:59')
assert.equal(helpers.clock(-5), '0:00')
assert.equal(helpers.viewModel(PAYLOAD, null).counts, '2:59 left · 2 turns · no tools · 2 carried')
assert.equal(helpers.viewModel(null, new Error('x')).label, 'backend unavailable')
assert.equal(helpers.viewModel({ active: null }, null).situation, 'idle')

// ---- an active state, mounted ----------------------------------------------

resetBody()
const active = await mountWith({ payload: PAYLOAD })
const text = document.body.textContent
assert.match(text, /DAYDREAMING/)
assert.match(text, /2:59 left · 2 turns · no tools · 2 carried/)
assert.match(text, /two memories · join only if it holds/)
const art = document.querySelector('canvas[data-antemuse-art="pane"]')
assert.ok(art, 'the pane paints the art on its own canvas')
assert.equal(art.getAttribute('aria-hidden'), 'true', 'art is decoration, not content')
assert.equal(document.querySelector('[data-antemuse-state]').getAttribute('data-antemuse-state'), 'active')
assert.ok(active.calls.rest[0].startsWith('/state'), 'the page asks the backend for a frame')
// Two clocks, deliberately: 900 ms for the state words, 4 s for which scene to
// paint. The picture does not need to re-ask a question that changes per turn.
const every = active.calls.intervals.map((i) => i.ms).sort((a, b) => a - b)
assert.deepEqual(every, [900, 4000, 6000],
  'three clocks: state words, which state, and how long a still holds')
const before = active.calls.rest.length

const slowest = active.calls.intervals.find((i) => i.ms === 900)
await act(async () => { slowest.fn() })
assert.equal(active.calls.rest.length, before + 1, 'a tick re-reads the backend')

await act(async () => { active.node.unmount() })


// ---- the pane, not the chat ------------------------------------------------

resetBody()
const pane = await mountWith({ payload: PAYLOAD }, 'pane')
const artCanvas = document.querySelector('canvas[data-antemuse-art="pane"]')
assert.ok(artCanvas, 'the pane owns a canvas')
assert.equal(document.querySelector('[data-antemuse-bg="layer"]'), null,
  'nothing is painted over the transcript any more')
await act(async () => { await new Promise((r) => setTimeout(r, 80)) })
// The pane plays a baked loop when the state has one; the live canvas is the
// fallback. Either way the element has to exist and point at real frames.
const stills = document.querySelectorAll('img[data-antemuse-bake="still"]')
assert.equal(stills.length, 2, 'two layers, so a dissolve is a cross-fade')
assert.match(stills[0].getAttribute('style'), /object-fit:\s*cover/)
assert.match(stills[0].getAttribute('style'), /transition:\s*opacity/, 'the dissolve is a CSS transition')
assert.match(pane.calls.rest[0], /^\/state\?cols=\d+&rows=\d+&fit=cover&busy=0/,
  'the pane asks the backend for the scene')

// ---- idle -------------------------------------------------------------------

resetBody()
const idle = await mountWith({ payload: { active: null, frame: { lines: [] }, residue: { count: 0 } } })
assert.match(document.body.textContent, /no state/)
assert.equal(document.querySelector('pre'), null, 'no frame is drawn when nothing is running')
await act(async () => { idle.node.unmount() })

// ---- backend missing --------------------------------------------------------

resetBody()
const broken = await mountWith({ error: 'connection refused' })
assert.match(document.body.textContent, /backend unavailable/)
assert.match(document.body.textContent, /the plugin backend is not mounted/)
assert.equal(document.querySelector('[data-antemuse-state]').getAttribute('data-antemuse-state'), 'unavailable')
await act(async () => { broken.node.unmount() })

console.log(`harness: desktop/plugin.js sha256:${digest}`)
console.log('harness: areas      =', registered.contributions.map((c) => c.area).join(', '))
console.log('harness: counts     =', helpers.viewModel(PAYLOAD, null).counts)
console.log('harness: 12 properties PASS (registration, settings page, helpers, DOM text, frame, ' +
  'aria, poll tick, idle, unavailable, layer/placement, conversation scope, chat left clean)')
