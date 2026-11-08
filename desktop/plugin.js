// Antemuse — the state a turn is governed by, as glyphs and counts.
//
// Loaded from ~/.hermes/plugins/antemuse/desktop/plugin.js (the unified agent
// plugin's desktop half) or copies of it under desktop-plugins/. Everything it
// shows comes from `GET /api/plugins/antemuse/state`, served by this plugin's
// own Python backend, which renders the same luminance-ramp art the CLI draws.
// This file samples nothing and invents nothing: if the backend is not mounted,
// it says so instead of drawing an empty box.
//
// Two contributions, deliberately: a pane and a status chip. A plugin whose only
// surface is a pane disables itself when that pane is closed, so the chip keeps
// the plugin meaningful on its own.

import {
  PANES_AREA,
  ROUTES_AREA,
  SIDEBAR_NAV_AREA,
  STATUSBAR_AREAS,
  PALETTE_AREA,
  pluginSettingsHref
} from '@hermes/plugin-sdk'
import { useEffect, useRef, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'antemuse'
const POLL_MS = 2000

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
      color: 'var(--ui-text-secondary, #8b8b8b)',
      opacity: 0.9,
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
    style: { position: 'relative', height: '100%', width: '100%', overflow: 'hidden', margin: 0 },
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
          position: 'absolute', left: 10, bottom: 8, fontSize: '11px', lineHeight: 1.35,
          opacity: 0.55, pointerEvents: 'none', display: 'flex', flexDirection: 'column', gap: '1px'
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

export default {
  id: ID,
  name: 'Antemuse',
  register(ctx) {
    ctx.register({
      id: 'state',
      area: PANES_AREA,
      title: copy.pane,
      data: {
        placement: 'right',
        collapsible: true,
        width: '320px',
        minWidth: '260px',
        maxWidth: '420px'
      },
      render: () => jsx(StateView, { ctx })
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
