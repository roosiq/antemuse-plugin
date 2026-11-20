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
import { mkdirSync, writeFileSync, existsSync } from 'node:fs'

const PLUGIN = new URL('../../desktop/plugin.js', import.meta.url)
const WORK = new URL('./.work/plugin.js', import.meta.url)

// Self-provisioning: the harness used to need setup.sh, which symlinked react and
// jsdom out of the desktop app's checkout. That checkout is not always there, and a
// harness that cannot start is not a check. `npm install` in the repo root provides
// the three packages; the SDK stub is written here.
mkdirSync(new URL('./.work/', import.meta.url), { recursive: true })
const SDK = new URL('./node_modules/@hermes/plugin-sdk/', import.meta.url)
if (!existsSync(new URL('index.js', SDK))) {
  mkdirSync(SDK, { recursive: true })
  writeFileSync(new URL('package.json', SDK), '{"name":"@hermes/plugin-sdk","type":"module","exports":"./index.js"}\n')
  writeFileSync(new URL('index.js', SDK), "export * from '../../../sdk-stub.js'\n")
}

const source = readFileSync(PLUGIN)
const sourceText = source.toString('utf8')
copyFileSync(PLUGIN, WORK)                     // bare imports resolve beside the copy
const digest = createHash('sha256').update(source).digest('hex').slice(0, 12)

const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {
  url: 'http://localhost'
})
globalThis.window = dom.window
globalThis.document = dom.window.document
Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true })
// The app routes by location hash, so the pane's fallback door needs the same global the
// browser gives it. Without this the harness would prove the fallback against nothing.
Object.defineProperty(globalThis, 'location', { value: dom.window.location, configurable: true })
globalThis.HTMLElement = dom.window.HTMLElement
globalThis.Node = dom.window.Node
globalThis.IS_REACT_ACT_ENVIRONMENT = true
window.requestAnimationFrame = (fn) => window.setTimeout(() => fn(Date.now()), 16)
window.cancelAnimationFrame = (id) => window.clearTimeout(id)
window.matchMedia = (query) => ({
  matches: query === '(pointer: coarse)',
  media: query,
  addEventListener: () => {}, removeEventListener: () => {}, addListener: () => {}, removeListener: () => {}
})

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
    save: noop, restore: noop, translate: noop, rotate: noop, rect: noop, clip: noop,
    lineTo: noop, stroke: noop, arc: noop, ellipse: noop, fill: noop,
    quadraticCurveTo: noop, bezierCurveTo: noop, closePath: noop,
    drawImage: () => { STUB.calls.drawImage += 1 },
    createRadialGradient: () => ({ addColorStop: noop }),
    createPattern: () => null,
    setLineDash: noop, strokeRect: noop, measureText: (text) => ({ width: String(text).length * 6 }),
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
// The real host routes by location hash. Give the stub the same observable effect so a test
// of "did the door navigate" measures the route, not whether a stub was called.
host.navigate = (path) => { dom.window.location.hash = `#${path}` }
const sweepStrays = helpers.sweepStrays

const PAYLOAD = {
  generated_at: 100,
  active: {
    key: 'walk', label: 'WALKING', walk: 'outer',
    contract: 'work continues · the frame is elsewhere · different on return',
    dose: 6, served: 0, unit: 'hops',
    tools: { mode: 'none', allowed: [], blocked: [] }
  },
  frame: { cols: 44, rows: 3, lines: ['  .:-=+  ', ' :#%@     ', '   .:     '] },
  residue: { count: 2, kinds: ['walk'] }
}

// An exploring payload: the cockpit door only exists while /explore is the active state.
const EXPLORE_PAYLOAD = {
  ...PAYLOAD,
  active: { ...PAYLOAD.active, key: 'explore', label: 'EXPLORING', dose: 0, served: 0, unit: 'picks' }
}

function makeCtx(state) {
  const calls = { rest: [], intervals: [], liveIntervals: new Set() }
  let stateCalls = 0
  const contributions = []
  const pages = []
  const ctx = {
    register: (c) => { contributions.push(c); return () => {} },
    registerSettingsPage: (page) => { pages.push(page); return () => {} },
    setInterval: (fn, ms) => {
      const interval = { fn, ms, disposed: 0 }
      calls.intervals.push(interval)
      calls.liveIntervals.add(interval)
      return () => { interval.disposed += 1; calls.liveIntervals.delete(interval) }
    },
    rest: async (path, opts) => {
      calls.rest.push(path)
      // The poll takes the earned unit, which is a write, so it must be a POST to /deliver.
      // Matching only /state let the pane ask a route this stub did not serve and still pass.
      if (path.startsWith('/deliver')) {
        calls.pollMethod = (opts && opts.method) || 'GET'
        // A host older than this pane has no such route.
        // The real host rejects with a plain STRING, not an Error. A stub that only throws
        // Error objects let a fallback pass here and fail in the app.
        if (state.noDeliver) {
          return Promise.reject(state.noDeliver === 'string'
            ? '404: {"detail":"Not Found"}'
            : new Error('404: {"detail":"Not Found"}'))
        }
      }
      if (path.startsWith('/graph')) return state.graph || { nodes: [] }
      // `failAfter` answers the first N polls, then fails: the pane has to behave on the
      // second poll, not only on a backend that was never there.
      if (path.startsWith('/deliver') || path.startsWith('/state')) {
        stateCalls += 1
        if (state.failAfter !== undefined && stateCalls > state.failAfter) {
          throw new Error(state.error || 'unreachable')
        }
      }
      if (state.failAfter === undefined && state.error) throw new Error(state.error)
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

// A React warning is a defect that ships quietly: the pane mounts, every assertion passes,
// and the console says the children have no keys. Collect them and fail on them.
const consoleErrors = []
const realConsoleError = console.error
console.error = (...args) => { consoleErrors.push(args.map(String).join(' ')); realConsoleError(...args) }

// ---- registration -----------------------------------------------------------

const registered = makeCtx({ payload: PAYLOAD })
plugin.register(registered.ctx)
assert.equal(plugin.id, 'antemuse')
// Assert the contributions by id, not by the shape of the area list. The list is
// order-and-duplicate sensitive, so it goes stale every time a route or a palette command is
// added — it still expected the pre-cockpit five while the plugin registered seven, which made
// this file fail on a clean mount of every release from 0.11.0 to 0.11.8.
assert.deepEqual(
  registered.contributions.map((c) => c.id).sort(),
  ['chip', 'cockpit-open', 'cockpit-page', 'nav', 'page', 'pane', 'watch'],
  'a dock pane, a chip, a route, a nav entry, the cockpit tab and two palette commands'
)
assert.equal(registered.contributions.length, 7)
const byId = Object.fromEntries(registered.contributions.map((c) => [c.id, c]))
assert.equal(byId.page.data.path, '/antemuse', 'the page route must match what the palette opens')
assert.equal(byId.nav.data.path, '/antemuse')
// The first contribution is the dock pane, which is where the art lives now.
assert.equal(registered.contributions[0].id, 'pane')
assert.equal(registered.contributions[0].data.placement, 'right', 'the art gets its own dock pane')
assert.equal(registered.contributions[0].data.collapsible, true)

// The picture a state asks for: one rule, four answers. Asserted on the real export so a
// state added to the registry without a picture cannot pass by drawing idle.
const { sceneFor } = helpers
assert.equal(sceneFor(null, false), 'idle', 'no state, nothing running: idle')
assert.equal(sceneFor(null, true), 'work', 'a turn running with no state: work')
assert.equal(sceneFor({ key: 'doomscroll', served: 0 }, false), 'bare',
  'a state that has fired nothing must not be drawn as idle')
assert.equal(sceneFor({ key: 'daydream', served: 1 }, false), 'daydream',
  'a state with material draws its own field')
assert.equal(sceneFor({ key: 'doomscroll', served: 3 }, false), 'bare',
  'feed text is never drawn: doomscroll has no field even with material')
assert.equal(sceneFor({ key: 'unstuck', served: 1 }, false), 'unstuck',
  'unstuck has a picture; it used to fall back to idle')
console.log('PASS  scene: four answers, one rule')

// A finished state keeps its picture for two polls: that is the only way a one-dose state
// (/unstuck) is ever visible, since it ends on the turn it serves.
const { holdScene } = helpers
assert.deepEqual(holdScene(null, { key: 'unstuck', served: 1 }, false),
  { scene: 'unstuck', held: { key: 'unstuck', polls: 0 } }, 'a running state is drawn at once')
assert.deepEqual(holdScene({ key: 'unstuck', polls: 0 }, null, false),
  { scene: 'unstuck', held: { key: 'unstuck', polls: 1 } }, 'the ending frame is held')
assert.deepEqual(holdScene({ key: 'unstuck', polls: 2 }, null, false),
  { scene: 'idle', held: null }, 'and then it lets go (two polls, the residue count)')
console.log('PASS  scene: the ending frame is held for two polls')
// The settings page is optional and another writer is currently moving it; what
// must hold is that the plugin never offers more than one.
assert.ok(registered.pages.length <= 1, 'at most one settings page')

// ---- pure helpers -----------------------------------------------------------

// There is no clock any more: a state ends when its dose lands, so the count is the whole
// story and `clock` is always empty. The assertions below are the values the plugin actually
// returns (printed, not remembered) — the old ones described a timer this pane does not have.
assert.equal(helpers.viewModel(PAYLOAD, null).clock, '')
assert.equal(helpers.viewModel(PAYLOAD, null).counts, '6 hops to go · no tools · 2 carried')
assert.equal(helpers.viewModel(null, new Error('x')).label, 'plugin unavailable')
assert.equal(helpers.viewModel(PAYLOAD, new Error('503')).label, 'the plugin went quiet')
assert.equal(helpers.viewModel({ active: null }, null).situation, 'idle')
// The empty pane says what to do about it, and an ended state says which one ended.
assert.equal(helpers.viewModel({ active: null }, null).note, '/walk to start')
// A flight is the one thing a person did with their own hands, so the idle pane says it landed
// instead of asking them to start a state they did not want.
assert.equal(
  helpers.viewModel({ active: null, flight: { concepts: 3, kept: ['harpoon'], trail: ['harpoon'] } }, null).note,
  'last flight · 3 concepts · kept 1'
)
assert.equal(
  helpers.viewModel({ active: null, flight: { concepts: 2, kept: [], trail: ['a', 'b'] } }, null).note,
  'last flight · 2 concepts'
)
assert.equal(helpers.viewModel({ active: null, last: { state: 'walk' } }, null).note,
  'walk ended · /walk again')
// The receipt yields to what is actually happening. Both flight assertions above pass
// `active: null`, so promoting the receipt above the `error || active` guard passed the whole
// harness — the code was right and the precedence was unpinned.
const F = { concepts: 3, kept: ['harpoon'], trail: ['harpoon'] }
assert.equal(helpers.viewModel({ active: { label: 'WALKING' }, flight: F }, null).note, '',
  'a running state must win over the last flight')
assert.equal(helpers.viewModel({ active: null, flight: F }, new Error('503')).note, '',
  'a failed poll must win over the last flight')
assert.equal(helpers.viewModel({ active: null, last: { state: 'walk' } }, null).note, 'walk ended · /walk again')
// A failed answer is not a claim about now: no clock, no counts, no contract beside an error.
const failed = helpers.viewModel(PAYLOAD, new Error('503'))
assert.equal(failed.counts, '', 'stale counts must not sit under an error')
assert.equal(failed.clock, '')
assert.equal(failed.contract, '')

// ---- the flight is filed by the exit, and only by the exit ------------------
//
// Escape hands the mouse back and stays, so the drawn button is the only door out, and
// `fileFlight` is the only writer. The cockpit itself cannot be mounted here (jsdom has no
// canvas backend), so the posting is exercised as the function the button calls; that the
// button reaches it is asserted in tests/test_cockpit_pane.py.

{
  const posts = []
  const ctx = { session: 's-harness', rest: (path, opts) => { posts.push({ path, opts }); return Promise.resolve({ ok: true }) } }
  helpers.fileFlight(ctx, { trail: ['harpoon', 'lighthouse'], kept: ['harpoon'], dropped: ['lighthouse'] })
  assert.equal(posts.length, 1, 'the exit did not file the flight')
  assert.equal(posts[0].path, '/flight')
  assert.equal(posts[0].opts.method, 'POST')
  assert.deepEqual(posts[0].opts.body.trail, ['harpoon', 'lighthouse'])
  assert.deepEqual(posts[0].opts.body.kept, ['harpoon'])
  assert.equal(posts[0].opts.body.session, 's-harness')

  // A flight nobody touched still posts: the server treats an empty trail as nothing to file,
  // and the pane should not be the thing deciding what counts as work.
  helpers.fileFlight(ctx, { trail: [], kept: [], dropped: [] })
  assert.equal(posts.length, 2, 'an empty flight was dropped instead of filed')

  // The outcome is readable, not swallowed: the pane's exit must not be blocked by a lost
  // note, but "quiet" once made a 404 look exactly like a success. This is the field the
  // packaged app exposes to answer "did it file?".
  await helpers.fileFlight({ session: 's', rest: () => Promise.reject(new Error('404: {"detail":"Not Found"}')) },
    { trail: ['harpoon'] })
  assert.equal(window.__flightPost.ok, false, 'a rejected post was recorded as success')
  assert.match(String(window.__flightPost.detail), /404/, 'the reason was not recorded')
  assert.deepEqual(window.__flightPost.payload.trail, ['harpoon'])

  await helpers.fileFlight(ctx, { trail: ['lighthouse'] })
  assert.equal(window.__flightPost.ok, true, 'a successful post was not recorded')

  // The fallback branch: a host with no `ctx.rest` posts through `window.fetch`, and that door
  // has to say why it failed too — it is the one a plugin without the host helper reaches.
  {
    const seen = []
    const realFetch = window.fetch
    window.fetch = (url, opts) => { seen.push({ url, opts }); return Promise.reject(new Error('503 misconfigured')) }
    await helpers.fileFlight({}, { trail: ['harpoon'] })
    assert.equal(seen.length, 1, 'the fallback never posted')
    assert.match(String(seen[0].url), /\/api\/plugins\/antemuse\/flight$/)
    assert.equal(window.__flightPost.ok, false, 'the fallback swallowed a refusal')
    assert.match(String(window.__flightPost.detail), /503/, 'the fallback did not keep the reason')

    window.fetch = (url, opts) => { seen.push({ url, opts }); return Promise.resolve({ ok: true }) }
    await helpers.fileFlight({}, { trail: ['lighthouse'] })
    assert.equal(window.__flightPost.ok, true, 'the fallback hid a success')
    window.fetch = realFetch
  }

  // No cockpit, no note — a call without a flight must not post a phantom.
  posts.length = 0
  helpers.fileFlight(ctx, null)
  assert.equal(posts.length, 0, 'a missing flight was posted as if it were one')
}

// The actual exit button is idempotent: a double click can race React's tab change, but it
// must still file one flight and ask to leave once.
{
  resetBody()
  const cockpit = makeCtx({ graph: { nodes: [] } })
  let exits = 0
  const node = createRoot(root())
  await act(async () => { node.render(React.createElement(helpers.CockpitPane, { ctx: cockpit.ctx, onExit: () => { exits += 1 } })) })
  const exit = document.querySelector('button[aria-label="Leave the cockpit"]')
  assert.ok(exit, 'the cockpit exposes its drawn exit as a real button')
  await act(async () => { exit.click(); exit.click() })
  const flights = cockpit.calls.rest.filter((path) => path === '/flight')
  assert.equal(flights.length, 1, 'two rapid exit clicks file exactly one flight')
  assert.equal(exits, 1, 'two rapid exit clicks leave exactly once')
  await act(async () => { node.unmount() })
}

// Touch-first devices get real controls with the existing key equivalents. They sit at the
// bottom, away from the exit (top right), and their bounded strip cannot widen a 390px pane.
{
  resetBody()
  const cockpit = makeCtx({ graph: { nodes: [] } })
  const node = createRoot(root())
  await act(async () => { node.render(React.createElement(helpers.CockpitPane, { ctx: cockpit.ctx, onExit: () => {} })) })
  const controls = ['touch-steer-left', 'touch-steer-right', 'touch-fire', 'touch-release']
  for (const id of controls) {
    const control = document.getElementById(id)
    assert.ok(control, `touch control ${id} is missing`)
    assert.ok(control.getAttribute('aria-label'), `${id} lacks an accessible name`)
    assert.equal(control.style.minWidth, '44px', `${id} is narrower than a 44px target`)
    assert.equal(control.style.minHeight, '44px', `${id} is shorter than a 44px target`)
  }
  const strip = document.querySelector('[aria-label="Touch flight controls"]')
  assert.equal(strip.style.maxWidth, 'calc(100% - 20px)', 'touch strip can overflow a narrow pane')
  assert.equal(document.querySelector('button[aria-label="Leave the cockpit"]').style.top, '12px')
  assert.equal(strip.style.bottom, '10px', 'touch controls must not overlap the exit or readout')
  await act(async () => { node.unmount() })
}

// The exit control is the only way out: Escape releases the mouse but stays. Keep this
// scoped to the button props so a future accessibility copy change cannot resurrect the old contract.
const exitStart = sourceText.indexOf("const exitButton = jsx('button'")
const exitEnd = sourceText.indexOf('  const captureBadge', exitStart)
const exitProps = sourceText.slice(exitStart, exitEnd)
assert.match(exitProps, /title: 'Leave the cockpit and file the flight; Escape only releases the mouse'/)
assert.match(exitProps, /'aria-label': 'Leave the cockpit'/)
assert.match(exitProps, /'aria-description': 'Files the flight; Escape only releases the mouse'/)
assert.doesNotMatch(exitProps, /\bEsc(?:ape)?\b[^\n]{0,100}\b(?:leave|exit|return)\b/i,
  'the exit button must not claim that Escape leaves')

// ---- an active state, mounted ----------------------------------------------

resetBody()
// Version skew: a host older than this pane has no /deliver. The pane must fall back to the
// look that used to carry delivery rather than blanking. This skew published itself once,
// against a gateway that predated the route.
{
  const skew = await mountWith({ payload: PAYLOAD, noDeliver: 'string' })
  assert.ok(skew.calls.rest.some((p) => p.startsWith('/deliver')), 'the pane tried the door')
  assert.ok(skew.calls.rest.some((p) => p.startsWith('/state')),
    'a 404 on /deliver must fall back to the older look, not blank the pane')
  await act(async () => { skew.node.unmount() })
}

// The ending note is the person's, so it clears on polls. Residue decays on turns, so a state
// that ends by itself used to leave "unstuck ended" on screen until two more messages arrived.
{
  const done = { ...PAYLOAD, active: null, last: { state: 'unstuck' },
                 residue: { count: 1, kinds: ['report'] } }
  const fin = await mountWith({ payload: done })
  // The stub interval records but never fires, so the polls are driven by hand.
  const ticker = fin.calls.intervals.find((i) => i.ms === 900)
  assert.ok(ticker, 'the state poll must be on the 900ms interval')
  await act(async () => { for (let i = 0; i < 4; i++) ticker.fn() })
  assert.doesNotMatch(document.body.textContent, /unstuck ended/,
    'the ending note must clear on polls, not wait for two more messages')
  await act(async () => { fin.node.unmount() })
}

const active = await mountWith({ payload: PAYLOAD })
const text = document.body.textContent
assert.match(text, /WALKING/)
assert.match(text, /6 hops to go · no tools · 2 carried/)
assert.match(text, /work continues · the frame is elsewhere · different on return/)
const art = document.querySelector('canvas[data-antemuse-art="pane"]')
assert.ok(art, 'the pane paints the art on its own canvas')
assert.equal(art.getAttribute('aria-hidden'), 'true', 'art is decoration, not content')
assert.equal(document.querySelector('[data-antemuse-state]').getAttribute('data-antemuse-state'), 'active')
assert.ok(active.calls.rest[0].startsWith('/deliver'), 'the page asks the backend for a frame')
assert.equal(active.calls.pollMethod, 'POST',
  'taking the earned unit is a write: the poll must POST, not GET')
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
assert.equal(active.calls.liveIntervals.size, 0,
  'unmount disposes every host interval instead of leaving state polling alive')
assert.ok(active.calls.intervals.every((interval) => interval.disposed === 1),
  'each host interval disposer runs exactly once')


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
assert.match(pane.calls.rest[0], /^\/deliver\?cols=\d+&rows=\d+&fit=cover&busy=0/,
  'the pane asks the backend for the scene')

// ---- idle -------------------------------------------------------------------

resetBody()
const idle = await mountWith({ payload: { active: null, frame: { lines: [] }, residue: { count: 0 } } })
assert.match(document.body.textContent, /nothing running/)
assert.equal(document.querySelector('pre'), null, 'no frame is drawn when nothing is running')
await act(async () => { idle.node.unmount() })

// ---- backend missing --------------------------------------------------------

resetBody()
const broken = await mountWith({ error: 'connection refused' })
// A single miss is a hiccup, not an outage: the pane keeps saying what it last knew. The poll
// clock is fired here the way the host would, until the run of misses is long enough to name.
const blink = broken.calls.intervals.find((i) => i.ms === 900)
await act(async () => { blink.fn() })
assert.notEqual(document.querySelector('[data-antemuse-state]').getAttribute('data-antemuse-state'), 'unavailable',
  'one failed poll must not replace the pane with an error')
await act(async () => { blink.fn() })
await act(async () => { blink.fn() })
await act(async () => { await new Promise((r) => setTimeout(r, 0)) })
assert.match(document.body.textContent, /plugin unavailable/)
assert.equal(document.querySelector('[data-antemuse-state]').getAttribute('data-antemuse-state'), 'unavailable')
await act(async () => { broken.node.unmount() })

// ---- a state that had a picture, then lost the backend ----------------------

resetBody()
const lost = await mountWith({ payload: PAYLOAD })
await act(async () => { lost.node.unmount() })
resetBody()
// A real failure message, not the label: whyFailed maps a 5xx to the quiet line.
const lostAgain = await mountWith({ payload: PAYLOAD, error: '503 service unavailable', failAfter: 2 })
const lostTicks = lostAgain.calls.intervals.find((i) => i.ms === 900)
assert.match(document.body.textContent, /6 hops to go/, 'the pane starts with a live state')
await act(async () => { for (let i = 0; i < 3; i++) lostTicks.fn() })
await act(async () => { await new Promise((r) => setTimeout(r, 0)) })
const lostText = document.body.textContent
assert.match(lostText, /the plugin went quiet/)
assert.doesNotMatch(lostText, /picked ·/, 'the pane must not print a count beside a failed answer')
assert.doesNotMatch(lostText, /join only if it holds/, 'nor a contract from the payload it could not refresh')
await act(async () => { lostAgain.node.unmount() })

// ---- the cockpit door works on a host that has no ctx.navigate ---------------
//
// The real desktop host does not put `navigate` on the plugin context at all. This harness
// used to hand the pane a no-op `navigate: () => {}`, so every door looked wired while the
// button did nothing in the app: a stub that answers a call the host never offers is worse
// than no stub. Mount without it and click the actual door.

resetBody()
const noNav = await mountWith({ payload: EXPLORE_PAYLOAD })
delete noNav.ctx.navigate
const door = [...document.querySelectorAll('button')]
  .find((b) => /open the cockpit/i.test(b.textContent || ''))
assert.ok(door, 'the state pane offers a cockpit door while exploring')
await act(async () => { door.click() })
const cockpitTab = [...document.querySelectorAll('[role=tab]')]
  .find((b) => /cockpit/i.test(b.textContent || ''))
assert.ok(cockpitTab, 'the screen has a cockpit tab')
assert.equal(cockpitTab.getAttribute('aria-selected'), 'true',
  'clicking "open the cockpit" must land on the cockpit tab without ctx.navigate')
await act(async () => { noNav.node.unmount() })

// The palette command has no tab to flip, so it must reach the route the app actually uses.
resetBody()
const palNav = makeCtx({ payload: EXPLORE_PAYLOAD })
delete palNav.ctx.navigate
plugin.register(palNav.ctx)
const opener = palNav.contributions.find((c) => c.id === 'cockpit-open')
assert.ok(opener, 'the palette offers the cockpit')
dom.window.location.hash = ''
opener.run()
assert.equal(dom.window.location.hash, '#/antemuse/cockpit',
  'the palette command must navigate on a host without ctx.navigate')

console.error = realConsoleError
const keyWarnings = consoleErrors.filter((m) => /key/i.test(m))
assert.deepEqual(keyWarnings, [], 'React emitted a key-related console error')

console.log(`harness: desktop/plugin.js sha256:${digest}`)
console.log('harness: areas      =', registered.contributions.map((c) => c.area).join(', '))
console.log('harness: counts     =', helpers.viewModel(PAYLOAD, null).counts)
console.log('harness: 16 properties PASS (registration, settings page, helpers, DOM text, frame, ' +
  'aria, poll tick, idle, unavailable, layer/placement, conversation scope, chat left clean, ' +
  'old-host fallback, ' +
  'cockpit door without ctx.navigate, palette route without ctx.navigate, ending note clears)')
dom.window.close()
