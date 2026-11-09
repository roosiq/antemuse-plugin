// Antemuse — the state a turn is governed by, as glyphs and counts.
//
// Loaded from ~/.hermes/plugins/antemuse/desktop/plugin.js (the unified agent
// plugin's desktop half) or copies of it under desktop-plugins/. Everything it
// shows comes from `GET /api/plugins/antemuse/state`, served by this plugin's
// own Python backend, which renders the same luminance-ramp art the CLI draws.
// This file samples nothing and invents nothing: if the backend is not mounted,
// it says so instead of drawing an empty box.
//
// The state is drawn *behind the chat it governs*, as a layer this plugin owns:
// a fixed, click-through <div> holding one <pre> of glyphs, appended to the body
// from a title-bar mount point. The shell has no plugin-facing chat background
// (its own backdrop is a boolean toggling one statue image), and atlas-style
// plugins solve this the same way — own the layer, own its cleanup.
//
// The layer is scoped to the focused conversation, not the profile: it reads
// host.state.focusedSessionId and host.state.busy, so two chats can differ and a
// chat with no state still paints `idle`.

import {
  TITLEBAR_AREAS,
  ROUTES_AREA,
  SIDEBAR_NAV_AREA,
  STATUSBAR_AREAS,
  PALETTE_AREA,
  pluginSettingsHref,
  host
} from '@hermes/plugin-sdk'
import { useEffect, useRef, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'antemuse'
// Fast enough that a baked frame is not stale when it lands: the slowest state,
// dream, holds a frame four seconds, so polling under a second never skips one.
const POLL_MS = 900

// A monospace glyph cell is about 0.6 advances wide by one line tall. Both the
// requested grid and the font that fills it come from these two numbers, so the
// art ends up exactly the size of the box instead of a thumbnail inside it.
const CELL_W = 0.6
const CELL_H = 1.0
const PROBE_FONT = 10

const copy = {
  pane: 'State',
  idle: 'no state',
  unavailable: 'backend unavailable',
  unreachable: 'the plugin backend is not mounted',
  watch: 'show antemuse state'
}

// ---------------------------------------------------------------- pure helpers

/** Seconds as a short clock: 179 -> "2:59". Never negative. */
export function clock(seconds) {
  const s = Math.max(0, Math.floor(Number(seconds) || 0))
  const m = Math.floor(s / 60)
  const rest = String(s % 60).padStart(2, '0')
  return `${m}:${rest}`
}

/** One line of counts under the frame — no prose, no adjectives. */
export function counts(payload) {
  const active = payload && payload.active
  if (!active) return ''
  const bits = [
    `${clock(active.seconds_left)} left`,
    `${active.turns_left} turn${active.turns_left === 1 ? '' : 's'}`
  ]
  const tools = active.tools || {}
  if (tools.mode === 'none') bits.push('no tools')
  else if (tools.mode === 'some') bits.push(`${tools.allowed.length} tool${tools.allowed.length === 1 ? '' : 's'}`)
  else bits.push('all tools')
  if (payload.residue && payload.residue.count) bits.push(`${payload.residue.count} carried`)
  return bits.join(' · ')
}

/** What the pane is looking at, in one of four honest states. */
export function situation(payload, error) {
  if (error) return 'unavailable'
  if (!payload) return 'loading'
  return payload.active ? 'active' : 'idle'
}

/** Everything the surface shows, derived once from one payload. */
export function viewModel(payload, error) {
  const active = (payload && payload.active) || null
  const frame = (payload && payload.frame) || {}
  return {
    situation: situation(payload, error),
    label: error ? copy.unavailable : active ? String(active.label || '') : copy.idle,
    note: error ? copy.unreachable : '',
    clock: active ? clock(active.seconds_left) : '',
    counts: counts(payload),
    contract: active ? String(active.contract || '') : '',
    lines: Array.isArray(frame.lines) ? frame.lines : [],
    residue: (payload && payload.residue && payload.residue.count) || 0
  }
}

// ---------------------------------------------------------------- the surface

function useStatePayload(ctx, cells) {
  const [payload, setPayload] = useState(null)
  const [error, setError] = useState(null)
  // The grid is part of the request, so a resize must re-ask rather than stretch
  // an old frame: the server renders at the size it is told.
  const query = cells ? `?cols=${cells.cols}&rows=${cells.rows}&fit=cover` : ''
  useEffect(() => {
    let alive = true
    const read = () => {
      ctx.rest('/state' + query).then(
        (data) => { if (alive) { setPayload(data); setError(null) } },
        (err) => { if (alive) setError(String((err && err.message) || err || 'unreachable')) }
      )
    }
    read()
    ctx.setInterval(read, POLL_MS)
    return () => { alive = false }
  }, [ctx, query])
  return { payload, error }
}

/** The largest box this pane actually has, measured rather than assumed. */
function useCells() {
  const ref = useRef(null)
  const [cells, setCells] = useState(null)
  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const fit = () => {
      const w = el.clientWidth || 0
      const h = el.clientHeight || 0
      if (!w || !h) return
      const cols = Math.max(1, Math.floor(w / (PROBE_FONT * CELL_W)))
      const rows = Math.max(1, Math.floor(h / (PROBE_FONT * CELL_H)))
      setCells((prev) => (prev && prev.cols === cols && prev.rows === rows ? prev : { w, h, cols, rows }))
    }
    fit()
    const observer = new ResizeObserver(fit)
    observer.observe(el)
    return () => observer.disconnect()
  }, [])
  return { ref, cells }
}

function Frame({ lines, cells }) {
  if (!lines.length) return null
  // Fill the box: the grid was requested from it, so the type is derived from the
  // grid that came back, not from a font size chosen in advance.
  // Fill the measured box with the art that actually came back: a frame narrower
  // than the grid is centred at its own width rather than stretched into it.
  const cols = Math.max(1, ...lines.map((l) => l.length))
  const rows = lines.length
  const fontSize = cells
    ? Math.max(2, Math.min(cells.w / (cols * CELL_W), cells.h / (rows * CELL_H)))
    : PROBE_FONT
  return jsx('pre', {
    'aria-hidden': 'true',
    'data-antemuse-frame': `${cols}x${rows}`,
    style: {
      margin: 0,
      padding: 0,
      lineHeight: 1,
      fontSize: `${fontSize.toFixed(2)}px`,
      letterSpacing: 0,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
      color: '#cfd6dd',
      opacity: 0.96,
      textShadow: '0 0 6px rgba(120,200,255,0.18)',
      overflow: 'hidden',
      whiteSpace: 'pre'
    },
    children: lines.join('\n')
  })
}

function StateView({ ctx }) {
  const { ref, cells } = useCells()
  const { payload, error } = useStatePayload(ctx, cells)
  const vm = viewModel(payload, error)
  const frame = (payload && payload.frame) || {}

  // The art is the pane; the words are furniture in the corner of it.
  return jsxs('div', {
    ref,
    style: {
      position: 'relative', height: '100%', width: '100%', overflow: 'hidden', margin: 0,
      background: 'radial-gradient(ellipse at 50% 38%, #0d1219 0%, #05070a 62%, #000 100%)'
    },
    'data-antemuse-state': vm.situation,
    children: [
      jsx('div', {
        style: { position: 'absolute', inset: 0, overflow: 'hidden', display: 'flex',
                 alignItems: 'flex-start', justifyContent: 'flex-start' },
        children: jsx(Frame, { lines: vm.lines, cells })
      }),
      vm.situation === 'loading'
        ? jsx('div', { style: { position: 'absolute', top: 10, left: 12, fontSize: '11px', opacity: 0.6 }, children: '…' })
        : null,
      jsxs('div', {
        style: {
          position: 'absolute', left: 12, bottom: 10, fontSize: '11px', lineHeight: 1.35,
          opacity: 0.5, pointerEvents: 'none', display: 'flex', flexDirection: 'column', gap: '1px',
          color: '#9aa6b2', letterSpacing: '0.02em'
        },
        children: [
          jsx('div', { style: { letterSpacing: '0.08em', fontWeight: 600 }, children: vm.label }),
          vm.note ? jsx('div', { children: vm.note }) : null,
          vm.counts ? jsx('div', { children: vm.counts }) : null,
          vm.contract ? jsx('div', { children: vm.contract }) : null
        ]
      })
    ]
  })
}

// A status chip: one glance, no prose. Present whether or not the pane is open.
function StateChip({ ctx }) {
  const { payload, error } = useStatePayload(ctx)
  const vm = viewModel(payload, error)
  const label = vm.clock ? `${vm.label} · ${vm.clock}` : vm.label
  return jsx('button', {
    type: 'button',
    title: label,
    onClick: () => { if (ctx.navigate) ctx.navigate(pluginSettingsHref(ID)) },
    style: {
      background: 'transparent',
      border: 0,
      padding: '0 6px',
      cursor: 'pointer',
      font: 'inherit',
      fontSize: '11px',
      opacity: vm.situation === 'active' ? 0.9 : 0.5,
      color: 'var(--ui-text-secondary, inherit)'
    },
    children: label
  })
}


// ------------------------------------------------------- the layer behind chat
//
// A plugin cannot ask the shell for a chat background: `areas.ts` offers panes,
// statusBar, titleBar, routes, sidebar nav and palette, and the shell's own
// backdrop is a boolean that toggles one fixed statue image. So the layer is
// ours — created, positioned, styled and removed by this file alone.

const LAYER = {
  attr: 'data-antemuse-bg',
  styleAttr: 'data-antemuse-bg-style',
  version: '1.0.0',
  // Glyphs are #cfd6dd at 0.96 where ascii-worlds are theme-tinted; ours are far
  // hotter, so the ceiling is low. Behind the transcript it still reads.
  defaultStrength: 0.18,
  maxStrength: 0.30
}

/** Remove layers, styles and the root flag left by an earlier load.
 *  A leaked fixed layer is a stuck screensaver over the whole app. */
export function sweepStrays(doc) {
  const d = doc || (typeof document !== 'undefined' ? document : null)
  if (!d) return
  // Only the elements we actually add. A bare [data-antemuse-bg] selector also
  // matches <html>, where the same attribute is the disposable flag — removing
  // that node would delete the document element itself.
  for (const node of Array.from(d.querySelectorAll(`div[${LAYER.attr}="layer"]`))) node.remove()
  for (const node of Array.from(d.querySelectorAll(`style[${LAYER.styleAttr}]`))) node.remove()
  if (d.documentElement) d.documentElement.removeAttribute(LAYER.attr)
}

/** What the layer must sit on, and therefore where it can sit.
 *
 *  "Behind" only works when the shell actually lets something through. The app
 *  paints an opaque surface, so a z-index -1 layer is invisible — measured, not
 *  assumed. ascii-worlds ships only its "in front" placement for the same
 *  reason. So the placement is decided from the surface, not hardcoded:
 *  an opaque host surface means in front at reduced strength; a transparent one
 *  means behind, where it costs the transcript nothing. */
function surface(doc, win) {
  try {
    const bg = win.getComputedStyle(doc.body).backgroundColor || ''
    const m = bg.match(/rgba?\(([^)]+)\)/)
    const parts = m ? m[1].split(/[,\s/]+/).filter(Boolean).map(Number) : []
    const alpha = parts.length >= 4 ? parts[3] : (bg === 'transparent' ? 0 : 1)
    return {
      colour: bg || 'transparent',
      opaque: alpha > 0.5,
      // rgb() channels are 0-255 here, not 0-1: compare against mid-grey.
      dark: parts.length >= 3 ? (parts[0] + parts[1] + parts[2]) / 3 < 128 : true
    }
  } catch (e) { return { colour: 'transparent', opaque: false, dark: true } }
}

function reducedMotion(win) {
  try { return Boolean(win.matchMedia && win.matchMedia('(prefers-reduced-motion: reduce)').matches) }
  catch (e) { return false }
}

/** The layer itself: one div, one pre, one version-stamped style element. */
export function createLayer(doc, win, { strength = LAYER.defaultStrength } = {}) {
  sweepStrays(doc)
  const surf = surface(doc, win)
  const placement = surf.opaque ? 'front' : 'behind'
  const strengthUsed = placement === 'front'
    ? Math.min(LAYER.maxStrength, strength * 0.66)   // over text: fainter still
    : strength
  const layer = doc.createElement('div')
  layer.setAttribute(LAYER.attr, 'layer')
  layer.setAttribute(LAYER.attr + '-version', LAYER.version)
  layer.setAttribute(LAYER.attr + '-placement', placement)
  layer.setAttribute('aria-hidden', 'true')
  // Behind: z-index -1, base colour is the surface's own, shows through gaps.
  // In front: nearly the highest z-index, no base colour, glyphs only, fainter,
  // and still click-through — the only placement an opaque shell permits.
  layer.style.cssText =
    'position:fixed;inset:0;pointer-events:none;user-select:none;overflow:hidden;' +
    'contain:strict;z-index:' +
      (placement === 'behind' ? '-1' : '2147483646') + ';background:' +
      (placement === 'behind' ? surf.colour : 'transparent') + ';'

  const pre = doc.createElement('pre')
  pre.setAttribute(LAYER.attr, 'glyphs')
  pre.style.cssText =
    'margin:0;padding:0;line-height:1;white-space:pre;overflow:hidden;' +
    'font-family:ui-monospace,SFMono-Regular,Menlo,monospace;' +
    'color:' + (surf.dark ? '#cfd6dd' : '#3a4650') + ';opacity:' +
      Math.min(LAYER.maxStrength, Math.max(0.04, strengthUsed)) + ';'
  layer.appendChild(pre)

  const style = doc.createElement('style')
  style.setAttribute(LAYER.styleAttr, '')
  style.setAttribute(LAYER.attr + '-version', LAYER.version)
  style.textContent = '';

  // Same guards ascii-worlds uses: a document without a head (or a body that is
  // replaced mid-flight) must not throw and strand a half-built layer.
  (doc.head || doc.documentElement).appendChild(style);
  (doc.body || doc.documentElement).appendChild(layer)
  doc.documentElement.setAttribute(LAYER.attr, 'on')
  return { layer, pre, style, strength: strengthUsed, placement }
}

export function removeLayer(doc, handle) {
  if (!handle) return
  try { handle.layer.remove() } catch (e) { /* already gone */ }
  try { handle.style.remove() } catch (e) { /* already gone */ }
  try { doc.documentElement.removeAttribute(LAYER.attr) } catch (e) { /* already gone */ }
}

/** Size the glyph grid to the layer's own box, capped like a sane canvas. */
function gridFor(handle) {
  // clientWidth is 0 before the layer is laid out (and in a headless mount), so
  // fall back to the viewport rather than painting nothing at all.
  const w = handle.layer.clientWidth || window.innerWidth || 0
  const h = handle.layer.clientHeight || window.innerHeight || 0
  if (!w || !h) return null
  // 10px probe, same cell model as the pane: 0.6 advances wide, 1 line tall.
  const cols = Math.max(1, Math.min(220, Math.floor(w / (10 * CELL_W))))
  const rows = Math.max(1, Math.min(150, Math.floor(h / (10 * CELL_H))))
  return { cols, rows }
}

function ChatBackdrop({ ctx }) {
  const handleRef = useRef(null)
  const stopRef = useRef(null)

  useEffect(() => {
    const doc = document
    const win = window
    const handle = createLayer(doc, win, { strength: LAYER.defaultStrength })
    handleRef.current = handle

    let last = ''
    let stopped = false

    const paint = () => {
      if (stopped || !handleRef.current) return
      const grid = gridFor(handleRef.current)
      if (!grid) return
      const session = host && host.state && host.state.focusedSessionId
        ? host.state.focusedSessionId.get() : null
      const busy = host && host.state && host.state.busy
        ? Boolean(host.state.busy.get()) : false
      const q = `?cols=${grid.cols}&rows=${grid.rows}&fit=cover` +
                `&busy=${busy ? 1 : 0}` +
                (session ? `&session=${encodeURIComponent(session)}` : '')
      ctx.rest('/state' + q).then(
        (payload) => {
          if (stopped || !handleRef.current) return
          const lines = (payload && payload.frame && payload.frame.lines) || []
          const text = lines.join('\n')
          if (text && text !== last) {
            last = text
            handleRef.current.pre.textContent = text
            // Fill the box: derive the font from the grid that came back.
            const cols = Math.max(1, ...lines.map((l) => l.length))
            const rows = lines.length
            const w = handleRef.current.layer.clientWidth || 0
            const h = handleRef.current.layer.clientHeight || 0
            const size = Math.max(2, Math.min(w / (cols * CELL_W), h / (rows * CELL_H)))
            handleRef.current.pre.style.fontSize = size.toFixed(2) + 'px'
          }
        },
        () => { /* backend down: an empty layer, never a broken app */ }
      )
    }

    paint()
    // Reduced motion means a still picture, not a frozen timer: paint once.
    if (!reducedMotion(win)) {
      const id = ctx.setInterval ? ctx.setInterval(paint, POLL_MS) : setInterval(paint, POLL_MS)
      stopRef.current = () => { if (typeof id === 'function') id(); else clearInterval(id) }
    }

    const unsubs = []
    try {
      if (host && host.state && host.state.focusedSessionId && host.state.focusedSessionId.listen) {
        unsubs.push(host.state.focusedSessionId.listen(() => { last = ''; paint() }))
      }
      if (host && host.state && host.state.busy && host.state.busy.listen) {
        unsubs.push(host.state.busy.listen(() => { last = ''; paint() }))
      }
    } catch (e) { /* a host without atoms still gets the timer */ }

    return () => {
      stopped = true
      for (const off of unsubs) { try { off() } catch (e) { /* already off */ } }
      if (stopRef.current) stopRef.current()
      const h = handleRef.current
      handleRef.current = null
      removeLayer(doc, h)
    }
  }, [ctx])

  return null
}

export default {
  id: ID,
  name: 'Antemuse',
  register(ctx) {
    // The mount is invisible; the layer it starts is the picture. Title-bar
    // slots are permanent across chat <-> page navigation, so this runs once
    // per registration rather than once per route.
    ctx.register({
      id: 'backdrop',
      area: TITLEBAR_AREAS.right,
      render: () => jsx(ChatBackdrop, { ctx })
    })
    ctx.register({
      id: 'chip',
      area: STATUSBAR_AREAS.right,
      order: 20,
      render: () => jsx(StateChip, { ctx })
    })
    // A dock pane can sit in an inactive tab or a collapsed rail, so the same
    // view also gets its own route: a page is reachable even when the layout
    // has no room for the pane.
    ctx.register({
      id: 'page',
      area: ROUTES_AREA,
      data: { path: `/${ID}` },
      render: () => jsx(StateView, { ctx })
    })
    ctx.register({
      id: 'nav',
      area: SIDEBAR_NAV_AREA,
      order: 60,
      data: { codicon: 'pulse', label: copy.pane, path: `/${ID}` }
    })
    ctx.register({
      id: 'watch',
      area: PALETTE_AREA,
      title: copy.watch,
      run: () => { if (ctx.navigate) ctx.navigate(`/${ID}`) }
    })
    if (ctx.registerSettingsPage) {
      ctx.registerSettingsPage({
        id: ID,
        title: 'Antemuse',
        icon: 'Waves',
        render: () => jsx(StateView, { ctx })
      })
    }
  }
}
