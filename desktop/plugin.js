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

import { PANES_AREA, STATUSBAR_AREAS, PALETTE_AREA, pluginSettingsHref } from '@hermes/plugin-sdk'
import { useEffect, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'antemuse'
const POLL_MS = 2000

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

function useStatePayload(ctx) {
  const [payload, setPayload] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    let alive = true
    const read = () => {
      ctx.rest('/state').then(
        (data) => { if (alive) { setPayload(data); setError(null) } },
        (err) => { if (alive) setError(String((err && err.message) || err || 'unreachable')) }
      )
    }
    read()
    ctx.setInterval(read, POLL_MS)
    return () => { alive = false }
  }, [ctx])
  return { payload, error }
}

function Frame({ lines }) {
  if (!lines.length) return null
  return jsx('pre', {
    'aria-hidden': 'true',
    style: {
      margin: 0,
      padding: 0,
      lineHeight: 1,
      fontSize: '10px',
      letterSpacing: 0,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
      color: 'var(--ui-text-secondary, #8b8b8b)',
      opacity: 0.85,
      overflow: 'hidden'
    },
    children: lines.join('\n')
  })
}

function StateView({ ctx }) {
  const { payload, error } = useStatePayload(ctx)
  const vm = viewModel(payload, error)
  if (vm.situation === 'loading') {
    return jsx('div', { style: { padding: '10px 12px', opacity: 0.6 }, 'data-antemuse-state': 'loading', children: '…' })
  }
  return jsxs('div', {
    style: { padding: '10px 12px', height: '100%', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: '6px' },
    'data-antemuse-state': vm.situation,
    children: [
    jsx('div', { style: { fontSize: '11px', letterSpacing: '0.08em', fontWeight: 600 }, children: vm.label }),
    vm.note ? jsx('div', { style: { fontSize: '11px', opacity: 0.55 }, children: vm.note }) : null,
    jsx(Frame, { lines: vm.lines }),
    vm.counts ? jsx('div', { style: { fontSize: '11px', opacity: 0.75 }, children: vm.counts }) : null,
      vm.contract ? jsx('div', { style: { fontSize: '11px', opacity: 0.55 }, children: vm.contract }) : null
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
