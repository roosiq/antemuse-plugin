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
  // Now that every cell carries its own alpha, strength is a budget over the
  // whole field rather than one opacity on a text block, so it can sit higher
  // than the flat version ever could.
  defaultStrength: 0.34,
  maxStrength: 0.60
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

// ---------------------------------------------------------------------------
// The drawing. A <pre> of characters is a text block pretending to be a picture:
// one colour, one opacity, eight ramp steps, whatever rate the poll allows.
// ascii-worlds reads well because of what happens *per cell* — a soft square for
// body, a seated glyph for edge, a level picked from luminance with a stable
// dither, and the colour taken from the pixel rather than set once for the whole
// layer. That is the model copied here; the geometry is ours.
// ---------------------------------------------------------------------------

const RAMP = '.:;-=+*ox%#@'

/** FNV-ish stable per-cell noise: dither without frame-to-frame sparkle. */
function cellNoise(x, y) {
  let h = (x * 374761393 + y * 668265263) | 0
  h = (h ^ (h >> 13)) * 1274126177
  return ((h ^ (h >> 16)) >>> 0) / 4294967295
}

const SCENES = {
  idle:       { strands: 3, speed: 0.085, width: 2.4, head: 0.0 },
  work:       { strands: 6, speed: 0.330, width: 2.2, head: 0.0 },
  walk:       { strands: 4, speed: 0.240, width: 2.6, head: 0.9 },
  daydream:   { strands: 5, speed: 0.150, width: 2.4, head: 0.5 },
  dream:      { strands: 5, speed: 0.115, width: 2.8, head: 1.0 },
  doomscroll: { strands: 6, speed: 0.370, width: 2.2, head: 0.9 }
}

/** One Mystify strand: six points, each bouncing in its own direction. */
function makeStrand(i, seed) {
  const n = 8
  const pts = []
  for (let k = 0; k < n; k++) {
    const a = ((seed * 37 + k * 53 + i * 17) % 360) * Math.PI / 180
    pts.push({
      x: 0.08 + cellNoise(i * 31 + k, seed) * 0.84,
      y: 0.08 + cellNoise(i * 17 + k, seed + 7) * 0.84,
      vx: Math.cos(a) * (0.5 + cellNoise(i, k) * 0.7),
      vy: Math.sin(a) * (0.5 + cellNoise(k, i) * 0.7)
    })
  }
  return pts
}

function inkFor(dark) {
  // The brand's path colour: teal, with amber only at a strand head.
  return dark
    ? { path: 'rgba(126, 205, 196, 0.95)', glow: 'rgba(96, 168, 160, 0.22)',
        head: 'rgba(242, 178, 90, 0.95)' }
    : { path: 'rgba(52, 96, 94, 0.95)', glow: 'rgba(52, 96, 94, 0.20)',
        head: 'rgba(173, 116, 32, 0.95)' }
}

export function createArt(canvas, { dark = true, strength = 0.12 } = {}) {
  const ctx = canvas.getContext('2d', { alpha: true })
  const field = canvas.ownerDocument.createElement('canvas')
  const sample = field.getContext('2d', { willReadFrequently: true })
  // Reading the field back at full size is enormous (SS^2 x pixels every frame);
  // draw it *down* into a cols x rows scratch canvas instead and read one pixel
  // per cell. The browser's downscale is the area average that sampling wanted.
  const grid = canvas.ownerDocument.createElement('canvas')
  const cellCtx = grid.getContext('2d', { willReadFrequently: true })
  // A document without canvas support (a headless mount, a policy-disabled
  // renderer) must leave a working layer with nothing in it, not throw.
  if (!ctx || !sample || typeof ctx.getImageData !== 'function') {
    return {
      resize() {}, render() {}, setScene() {},
      stats: () => ({ frames: 0, glyphs: 0, cols: 0, rows: 0, scene: 'idle', w: 0, h: 0, dpr: 1 })
    }
  }
  const ink = inkFor(dark)
  const SS = 2                        // supersample: a 1px strand must survive
  let w = 1, h = 1, dpr = 1, cols = 1, rows = 1, scene = 'idle'
  let strands = [], t = 0, glyphs = 0, frames = 0, lastFieldLit = 0

  const spec = () => SCENES[scene] || SCENES.idle

  function resize(width, height, ratio = 1) {
    w = Math.max(1, Math.min(2200, Math.round(width)))
    h = Math.max(1, Math.min(1600, Math.round(height)))
    dpr = Math.max(1, Math.min(2, ratio || 1, Math.sqrt(4200000 / (w * h))))
    canvas.width = Math.round(w * dpr)
    canvas.height = Math.round(h * dpr)
    canvas.style.width = w + 'px'
    canvas.style.height = h + 'px'
    // A cell is one monospace glyph: 0.6 advances wide, one line tall.
    const cellH = 17
    rows = Math.max(1, Math.min(150, Math.round(h / cellH)))
    cols = Math.max(1, Math.min(260, Math.round(w / (cellH * 0.6))))
  }

  function setScene(name) {
    // `scene` starts at 'idle', so comparing names alone leaves the field empty
    // on the first call: the strands are the thing that has to be built, not the
    // name that has to change.
    if (name === scene && strands.length) return
    scene = name
    strands = []
    for (let i = 0; i < spec().strands; i++) strands.push(makeStrand(i, 11 + i * 7))
  }

  function step(dt) {
    const sp = spec().speed
    for (const pts of strands) for (const p of pts) {
      p.x += p.vx * sp * dt
      p.y += p.vy * sp * dt
      if (p.x < 0.02) { p.x = 0.02; p.vx = Math.abs(p.vx) }
      if (p.x > 0.98) { p.x = 0.98; p.vx = -Math.abs(p.vx) }
      if (p.y < 0.02) { p.y = 0.02; p.vy = Math.abs(p.vy) }
      if (p.y > 0.98) { p.y = 0.98; p.vy = -Math.abs(p.vy) }
    }
  }

  function drawField() {
    if (field.width !== w * SS || field.height !== h * SS) {
      field.width = w * SS
      field.height = h * SS
    }
    sample.setTransform(1, 0, 0, 1, 0, 0)
    sample.clearRect(0, 0, field.width, field.height)
    sample.setTransform(SS, 0, 0, SS, 0, 0)
    sample.lineJoin = 'round'
    sample.lineCap = 'round'
    for (const pts of strands) {
      // Glow first, core second. A single hairline converts to a row of lonely
      // dots; the wide, faint pass is what gives the strand body between cells —
      // the same job the soft square does in ascii-worlds, done in the field.
      // Mystify reads as a ribbon, not a zigzag, because the vertices are joined
      // by curves through their midpoints. Straight lines between bouncing points
      // is what made this look like noise.
      sample.beginPath()
      const px0 = pts[0].x * w, py0 = pts[0].y * h
      sample.moveTo(px0, py0)
      for (let i = 1; i < pts.length - 1; i++) {
        const a = pts[i], b = pts[i + 1]
        sample.quadraticCurveTo(a.x * w, a.y * h, ((a.x + b.x) / 2) * w, ((a.y + b.y) / 2) * h)
      }
      const lastPt = pts[pts.length - 1]
      sample.lineTo(lastPt.x * w, lastPt.y * h)
      sample.strokeStyle = ink.glow
      sample.lineWidth = spec().width * 3.4
      sample.stroke()
      sample.strokeStyle = ink.path
      sample.lineWidth = spec().width
      sample.stroke()
      // The lit end. Amber is the only warm thing in the frame.
      if (spec().head > 0.4) {
        const last = pts[pts.length - 1]
        sample.fillStyle = ink.head
        sample.beginPath()
        sample.arc(last.x * w, last.y * h, 3.2, 0, Math.PI * 2)
        sample.fill()
      }
    }
  }

  function render(dt) {
    if (!strands.length) setScene(scene)
    step(dt)
    drawField()
    if (grid.width !== cols || grid.height !== rows) {
      grid.width = cols
      grid.height = rows
    }
    cellCtx.clearRect(0, 0, cols, rows)
    cellCtx.imageSmoothingEnabled = true
    if ('imageSmoothingQuality' in cellCtx) cellCtx.imageSmoothingQuality = 'high'
    cellCtx.drawImage(field, 0, 0, cols, rows)
    const px = cellCtx.getImageData(0, 0, cols, rows).data
    let fieldLit = 0
    for (let i = 3; i < px.length; i += 4) if (px[i] > 0) fieldLit++
    lastFieldLit = fieldLit
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)
    const cellW = w / cols, cellH = h / rows
    ctx.font = `600 ${cellH * 0.94}px ui-monospace, SFMono-Regular, Consolas, monospace`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    glyphs = 0
    // Coverage per cell, then smoothed. A thin band is all-or-nothing cell by
    // cell, so quantising it raw gives a ragged dotted edge; smoothing first is
    // what turns the band into a ribbon with a falloff instead of a stencil.
    const raw = new Float32Array(cols * rows)
    for (let i = 0, cells = cols * rows; i < cells; i++) {
      const a = px[i * 4 + 3]
      raw[i] = a ? Math.min(1, (a / 255) * 2.1) : 0
    }
    const smooth = new Float32Array(cols * rows)
    const tmp = new Float32Array(cols * rows)
    const blur = (src, dst) => {
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          let acc = 0, n = 0
          for (let dy = -1; dy <= 1; dy++) {
            const yy = y + dy
            if (yy < 0 || yy >= rows) continue
            for (let dx = -1; dx <= 1; dx++) {
              const xx = x + dx
              if (xx < 0 || xx >= cols) continue
              acc += src[yy * cols + xx]; n++
            }
          }
          dst[y * cols + x] = acc / n
        }
      }
    }
    blur(raw, tmp)
    blur(tmp, smooth)

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const i = row * cols + col
        const cov = Math.max(raw[i], smooth[i] * 1.15)
        if (cov <= 0.05) { continue }
        const at = i * 4
        let r = px[at], g = px[at + 1], b = px[at + 2]
        if (!dark) { r *= 0.5; g *= 0.5; b *= 0.55 }
        const colour = `rgb(${r | 0},${g | 0},${b | 0})`
        const x = col * cellW, y = row * cellH
        if (cov < 0.16) {
          // Edge of the band: a dot, not a glyph.
          ctx.globalAlpha = Math.min(0.45, cov * 2.2) * (strength / 0.35)
          ctx.fillStyle = dark ? 'rgba(126,205,196,0.8)' : 'rgba(52,96,94,0.8)'
          ctx.fillText('.', x + cellW / 2, y + cellH / 2)
          continue
        }
        const k = strength / 0.35
        ctx.fillStyle = colour
        ctx.globalAlpha = Math.min(0.20, cov * 0.16) * k
        ctx.fillRect(x + 0.3, y + 0.3, cellW - 0.6, cellH - 0.6)
        // Level from the smoothed coverage, with a one-step dither: the dither
        // breaks banding, it does not decide the shape.
        const level = Math.min(
          RAMP.length - 1,
          Math.max(0, Math.round(cov * (RAMP.length - 1) - 0.5 + cellNoise(col, row)))
        )
        ctx.globalAlpha = Math.min(0.85, cov * 1.45 + 0.10) * k
        ctx.fillText(RAMP[level], x + cellW / 2, y + cellH / 2)
        glyphs++
      }
    }
    frames++
  }

  return {
    resize, render, setScene,
    stats: () => ({ frames, glyphs, cols, rows, scene, w, h, dpr, fieldLit: lastFieldLit, strands: strands.length })
  }
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

  const art = doc.createElement('canvas')
  art.setAttribute(LAYER.attr, 'glyphs')
  art.setAttribute('aria-hidden', 'true')
  art.style.cssText = 'display:block;margin:0;padding:0;'
  layer.appendChild(art)

  const style = doc.createElement('style')
  style.setAttribute(LAYER.styleAttr, '')
  style.setAttribute(LAYER.attr + '-version', LAYER.version)
  style.textContent = '';

  // Same guards ascii-worlds uses: a document without a head (or a body that is
  // replaced mid-flight) must not throw and strand a half-built layer.
  (doc.head || doc.documentElement).appendChild(style);
  (doc.body || doc.documentElement).appendChild(layer)
  doc.documentElement.setAttribute(LAYER.attr, 'on')
  return { layer, art, style, strength: strengthUsed, placement, dark: surf.dark }
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
    const art = createArt(handle.art, { dark: handle.dark, strength: handle.strength })
    // Bounded diagnostics for the app's own devtools. Nothing here grows.
    const probe = (window.__antemuse = { frames: 0, glyphs: 0, errors: [], scene: null })

    // rAF is the right clock, but not every document has one (a headless mount
    // does not). Fall back to a timer rather than throwing inside the effect.
    const raf =
      typeof win.requestAnimationFrame === 'function'
        ? (cb) => win.requestAnimationFrame(cb)
        : (cb) => win.setTimeout(() => cb(Date.now()), 16)
    const cancels =
      typeof win.cancelAnimationFrame === 'function' ? (id) => win.cancelAnimationFrame(id) : (id) => win.clearTimeout(id)

    let stopped = false
    let rafId = 0
    let lastTs = 0
    let lastPaint = 0
    const MIN_MS = 1000 / 30

    const fit = () => {
      const w = handle.layer.clientWidth || win.innerWidth || 0
      const h = handle.layer.clientHeight || win.innerHeight || 0
      if (w && h) art.resize(w, h, win.devicePixelRatio || 1)
    }
    fit()

    const tick = (ts) => {
      if (stopped) return
      rafId = raf(tick)
      if (!lastTs) lastTs = ts
      if (ts - lastPaint < MIN_MS) return
      const dt = Math.min(0.12, (ts - lastTs) / 1000)
      lastTs = ts
      lastPaint = ts
      art.render(dt)
      const st = art.stats()
      probe.frames = st.frames
      probe.glyphs = st.glyphs
      probe.size = st
    }

    // The state is slow (it changes when a turn starts, not every frame), so the
    // poll only chooses the scene. The picture itself never waits on HTTP.
    const poll = () => {
      if (stopped) return
      const st = art.stats()
      const session = host && host.state && host.state.focusedSessionId
        ? host.state.focusedSessionId.get() : null
      const busy = host && host.state && host.state.busy
        ? Boolean(host.state.busy.get()) : false
      const q = `?cols=${st.cols}&rows=${st.rows}&fit=cover&busy=${busy ? 1 : 0}` +
                (session ? `&session=${encodeURIComponent(session)}` : '')
      ctx.rest('/state' + q).then(
        (payload) => {
          if (stopped) return
          const active = payload && payload.active
          const name = (active && active.key) || (busy ? 'work' : 'idle')
          art.setScene(SCENES[name] ? name : 'idle')
          probe.scene = art.stats().scene
          probe.state = { active: Boolean(active), busy }
        },
        (err) => {
          probe.errors = probe.errors.concat(String((err && err.message) || err)).slice(-3)
        }
      )
    }

    if (reducedMotion(win)) {
      // A still picture, not a frozen timer.
      art.render(0)
    } else {
      rafId = raf(tick)
    }
    poll()

    const onResize = () => { fit(); art.render(0) }
    const onVisibility = () => {
      if (doc.hidden) { if (rafId) cancels(rafId); rafId = 0 }
      else if (!rafId && !reducedMotion(win)) { lastTs = 0; rafId = raf(tick) }
    }
    win.addEventListener('resize', onResize)
    doc.addEventListener('visibilitychange', onVisibility)

    const id = ctx.setInterval ? ctx.setInterval(poll, 4000) : setInterval(poll, 4000)
    stopRef.current = () => { if (typeof id === 'function') id(); else clearInterval(id) }

    const unsubs = []
    try {
      if (host && host.state && host.state.focusedSessionId && host.state.focusedSessionId.listen) {
        unsubs.push(host.state.focusedSessionId.listen(() => poll()))
      }
      if (host && host.state && host.state.busy && host.state.busy.listen) {
        unsubs.push(host.state.busy.listen(() => poll()))
      }
    } catch (e) { /* a host without atoms still gets the timer */ }

    return () => {
      stopped = true
      if (rafId) { try { cancels(rafId) } catch (e) { /* gone */ } }
      win.removeEventListener('resize', onResize)
      doc.removeEventListener('visibilitychange', onVisibility)
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
    // Settings are NOT a bespoke page: the host renders this plugin's manifest
    // `config_schema` as a form under Settings ▸ Plugins and saves it to
    // plugins.entries.antemuse.settings. Registering our own page here would shadow
    // that form with a second, divergent copy of the same controls.

  }
}
