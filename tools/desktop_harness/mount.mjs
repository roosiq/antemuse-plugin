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
  ['titleBar.right', 'statusBar.right', 'routes', 'sidebar.nav', 'palette'],
  'a background mount, a chip, a page, a nav entry and a palette command'
)
const byId = Object.fromEntries(registered.contributions.map((c) => [c.id, c]))
assert.equal(byId.page.data.path, '/antemuse', 'the page route must match what the palette opens')
assert.equal(byId.nav.data.path, '/antemuse')
// The first contribution is no longer a pane: it is the invisible mount that
// owns the layer behind the chat, so it carries no pane data at all.
assert.equal(registered.contributions[0].id, 'backdrop')
assert.equal(registered.contributions[0].data, undefined, 'a mount point has no pane geometry')
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
const pre = document.querySelector('pre')
assert.ok(pre, 'the frame should render as a pre')
assert.equal(pre.textContent, PAYLOAD.frame.lines.join('\n'))
assert.equal(pre.getAttribute('aria-hidden'), 'true', 'art is decoration, not content')
assert.equal(document.querySelector('[data-antemuse-state]').getAttribute('data-antemuse-state'), 'active')
assert.equal(active.calls.rest.length, 1)
assert.ok(active.calls.rest[0].startsWith('/state'), 'the page asks the backend for a frame')
assert.equal(active.calls.intervals.length, 1)
assert.equal(active.calls.intervals[0].ms, 900, 'poll faster than the slowest baked frame')

await act(async () => { active.calls.intervals[0].fn() })
assert.deepEqual(active.calls.rest, ['/state', '/state'], 'a tick re-reads the backend')

await act(async () => { active.node.unmount() })


// ---- the layer behind the chat ---------------------------------------------

resetBody()
const bg = await mountWith({ payload: PAYLOAD }, 'backdrop')
const layer = document.querySelector('[data-antemuse-bg="layer"]')
assert.ok(layer, 'the mount point creates the layer')
assert.equal(layer.getAttribute('aria-hidden'), 'true', 'the layer is decoration')
const css = layer.getAttribute('style')
assert.match(css, /position:\s*fixed/)
assert.match(css, /pointer-events:\s*none/, 'clicks pass through to the chat')
// jsdom's body has no background, so this mount exercises the "behind" branch.
assert.match(css, /z-index:\s*-1/, 'a transparent surface gets a layer behind it')
assert.equal(layer.getAttribute('data-antemuse-bg-placement'), 'behind')
assert.match(css, /contain:\s*strict/)
const glyph = layer.querySelector('pre[data-antemuse-bg="glyphs"]')
assert.ok(glyph, 'one pre holds the glyphs')
assert.equal(glyph.textContent, PAYLOAD.frame.lines.join('\n'))
assert.match(glyph.getAttribute('style'), /opacity:\s*0\.18/, 'default strength, capped low')

assert.ok(document.querySelector('style[data-antemuse-bg-style]'), 'one version-stamped style element')
assert.equal(document.documentElement.getAttribute('data-antemuse-bg'), 'on', 'the root flag marks it disposable')
assert.match(bg.calls.rest[0], /^\/state\?cols=\d+&rows=\d+&fit=cover&busy=0/, 'grid and busy are asked for')

// it re-reads when the focused conversation changes
host.state.focusedSessionId.set('sess-42')
await act(async () => {})
assert.ok(bg.calls.rest.some((p) => p.includes('session=sess-42')), 'the layer follows the conversation')

await act(async () => { bg.node.unmount() })
assert.equal(document.querySelector('div[data-antemuse-bg="layer"]'), null, 'unmount removes the layer')
assert.equal(document.querySelector('style[data-antemuse-bg-style]'), null, 'and its style element')
assert.equal(document.documentElement.getAttribute('data-antemuse-bg'), null, 'and the root flag')

// stray sweep must not delete the document element (it did, once)
sweepStrays(document)
assert.ok(document.documentElement, 'sweeping strays leaves <html> alone')

// The other branch: an opaque shell cannot show a z-index -1 layer (measured in
// the app — an opaque body hid it completely), so it goes in front, fainter.
resetBody()
document.body.style.background = 'rgb(12, 12, 14)'
const front = await mountWith({ payload: PAYLOAD }, 'backdrop')
const frontLayer = document.querySelector('div[data-antemuse-bg="layer"]')
assert.equal(frontLayer.getAttribute('data-antemuse-bg-placement'), 'front', 'opaque surface flips placement')
assert.match(frontLayer.getAttribute('style'), /z-index:\s*2147483646/)
assert.match(frontLayer.getAttribute('style'), /pointer-events:\s*none/, 'in front still passes clicks through')
const frontGlyph = frontLayer.querySelector('pre[data-antemuse-bg="glyphs"]')
const frontOpacity = Number((frontGlyph.getAttribute('style').match(/opacity:\s*([\d.]+)/) || [])[1])
assert.ok(frontOpacity < 0.18 && frontOpacity > 0.05, `in front is fainter: ${frontOpacity}`)
assert.match(frontGlyph.getAttribute('style'), /color:\s*(#cfd6dd|rgb\(207, 214, 221\))/,
  'dark surface gets the light ink')
await act(async () => { front.node.unmount() })
document.body.style.background = ''
assert.equal(document.querySelector('div[data-antemuse-bg="layer"]'), null, 'the front layer is removed too')

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
  'aria, poll tick, idle, unavailable, layer/placement, conversation scope, cleanup + stray sweep)')
