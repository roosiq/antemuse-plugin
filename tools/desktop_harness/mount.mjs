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

async function mountWith(state) {
  const wired = makeCtx(state)
  plugin.register(wired.ctx)
  const node = createRoot(root())
  await act(async () => { node.render(wired.contributions[0].render()) })
  return { ...wired, node }
}

// ---- registration -----------------------------------------------------------

const registered = makeCtx({ payload: PAYLOAD })
plugin.register(registered.ctx)
assert.equal(plugin.id, 'antemuse')
assert.deepEqual(
  registered.contributions.map((c) => c.area),
  ['panes', 'statusBar.right', 'routes', 'sidebar.nav', 'palette'],
  'a pane, a chip, a page, a nav entry and a palette command'
)
const byId = Object.fromEntries(registered.contributions.map((c) => [c.id, c]))
assert.equal(byId.page.data.path, '/antemuse', 'the page route must match what the palette opens')
assert.equal(byId.nav.data.path, '/antemuse')
assert.equal(registered.contributions[0].data.placement, 'right')
assert.equal(registered.contributions[0].data.collapsible, true)
assert.equal(registered.pages.length, 1, 'a settings page is offered when the host supports one')

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
assert.deepEqual(active.calls.rest, ['/state'])
assert.equal(active.calls.intervals.length, 1)
assert.equal(active.calls.intervals[0].ms, 2000)

await act(async () => { active.calls.intervals[0].fn() })
assert.deepEqual(active.calls.rest, ['/state', '/state'], 'a tick re-reads the backend')

await act(async () => { active.node.unmount() })

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
console.log('harness: 9 properties PASS (registration, settings page, helpers, DOM text, frame, aria, poll tick, idle, unavailable)')
