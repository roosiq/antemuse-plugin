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
  PANES_AREA,
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
  pane: 'Antemuse',
  idle: 'no state',
  unavailable: 'backend unavailable',
  unreachable: 'the plugin backend is not mounted',
  signin: 'sign-in required',
  silent: 'the backend did not answer',
  watch: 'show antemuse'
}

/**
 * Why the poll failed, as far as the failure actually says.
 *
 * The pane used to answer every failed poll with "the plugin backend is not mounted", which is a
 * claim about a cause it had not established: an expired session, a slow server and a missing route
 * all looked identical. A 401 says sign in; a 404 says the route is not there; anything without a
 * status is the server not answering. Only a 404 is allowed to say "not mounted".
 */
export function whyFailed(err) {
  const text = String((err && (err.message || err.detail || err.error)) || err || '')
  const status = Number((err && (err.status || err.statusCode)) || (text.match(/\b(4\d\d|5\d\d)\b/) || [])[1] || 0)
  if (/no_cookie|unauthenticated|unauthorized|sign in|login/i.test(text)) return copy.signin
  if (status === 401 || status === 403) return copy.signin
  if (status === 404) return copy.unreachable
  if (status >= 500) return copy.silent
  if (/timeout|timed out|did not answer|ECONNREFUSED|Failed to fetch|network/i.test(text)) return copy.silent
  return copy.unavailable
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
    // One honest string, not a category plus a footnote: the label is what a person reads at
    // 11px in a corner, and "backend unavailable" for an expired session sends them looking at
    // the server instead of at their sign-in.
    label: error ? whyFailed(error) : active ? String(active.label || '') : copy.idle,
    note: '',
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



/**
 * The map as a space you can turn.
 *
 * The stills are a picture of the concept map; this is the map. Nodes are the labels the ledger
 * has actually served, placed at their real 3D coordinates from the stored projection; the warm
 * ones are what is firing right now. Drag to orbit, wheel to zoom, hover to read a concept, click
 * to pin it. Nothing is invented here — a label with no projection is simply absent, and nothing
 * is warm unless the backend says it fired.
 *
 * Raw WebGL, no library: this file is the whole plugin, so a vendored scene graph would be a
 * megabyte of someone else's code shipped for one canvas.
 */
let GRAPH3D_SEQ = 0

function createGraph3D(el, doc, ctx, host, win) {
  if (!ctx || typeof ctx.rest !== 'function') return null
  const INSTANCE = ++GRAPH3D_SEQ
  const boot = (v) => {
    try {
      win.__antemuse = win.__antemuse || {}
      win.__antemuse.g3boot = (win.__antemuse.g3boot || '') + '|' + v
    } catch (e) { /* diagnostics never break the pane */ }
  }
  boot('mount' + INSTANCE)
  const report = (patch) => {
    // The pane's diagnostics object is created by the /state poll, which may not have answered
    // yet — a report that waits for it was silently dropped on a cold start.
    if (!win.__antemuse) win.__antemuse = {}
    const box = win.__antemuse.g3s = win.__antemuse.g3s || {}
    box[INSTANCE] = Object.assign(box[INSTANCE] || {}, { instance: INSTANCE }, patch)
    if (INSTANCE === 1) win.__antemuse.g3 = box[INSTANCE]
  }
  const canvas = doc.createElement('canvas')
  canvas.setAttribute('data-antemuse-3d', 'pane')
  canvas.setAttribute('aria-hidden', 'true')
  canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;z-index:2;display:block;cursor:grab;touch-action:none;outline:none'
    // preserveDrawingBuffer: the frame must still be there when something wants to copy it —
  // a screenshot, a video capture, or a person pasting the pane into a bug report. Without it the
  // buffer is discarded on composite and every capture of this surface comes back blank.
  // Opaque, not transparent. This canvas has an additive blend into its own buffer, and a
  // transparent canvas is composited *again* by the browser, which multiplied every ground point
  // by its own alpha and left the cloud invisible — 1,373 points reading as two specks. An opaque
  // surface with its own dark clear colour composites exactly once.
  const gl = canvas.getContext('webgl', { antialias: true, alpha: false,
    preserveDrawingBuffer: true })
    || canvas.getContext('experimental-webgl')
  if (!gl) return null
  el.appendChild(canvas)

  const tip = doc.createElement('div')
  tip.style.cssText = 'position:absolute;z-index:3;pointer-events:none;padding:3px 7px;border-radius:6px;' +
    'background:rgba(8,10,14,0.86);color:#efe9d8;font:12px/1.35 ui-sans-serif,system-ui,sans-serif;' +
    'letter-spacing:0.01em;opacity:0;transition:opacity 120ms ease;white-space:nowrap'
  el.appendChild(tip)
  // Names for what is firing. Only the firing set — labelling 1,400 points would be a wall of
  // text, and the point of a label here is "which concept is that", not "name everything".
  const labelLayer = doc.createElement('div')
  labelLayer.style.cssText = 'position:absolute;inset:0;z-index:2;pointer-events:none;overflow:hidden'
  el.appendChild(labelLayer)
  const labelEls = []
  const makeLabel = () => {
    const d = doc.createElement('span')
    d.style.cssText = 'position:absolute;left:0;top:0;font:11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;' +
      'letter-spacing:0.02em;color:#f2cf8f;text-shadow:0 0 6px rgba(0,0,0,0.95),0 0 2px rgba(0,0,0,1);' +
      'white-space:nowrap;opacity:0;transition:opacity 120ms linear;will-change:transform'
    labelLayer.appendChild(d)
    labelEls.push(d)
    return d
  }

  const VS_POINT = 'attribute vec3 aPos; attribute float aW; uniform mat4 uMVP; uniform float uDpr;' +
    'uniform float uSize; varying float vW;' +
    'void main(){ vec4 p = uMVP * vec4(aPos,1.0); gl_Position = p;' +
    'gl_PointSize = (2.3 + 6.0*aW) * uDpr * uSize * (2.4 / max(0.45, p.w)); vW = aW; }'
  const FS_POINT = 'precision mediump float; varying float vW;' +
    'void main(){ vec2 d = gl_PointCoord - vec2(0.5); float r = length(d)*2.0;' +
    'if (r > 1.0) discard; float core = smoothstep(1.0, 0.18, r);' +
    'vec3 cool = vec3(0.60,0.64,0.78); vec3 warm = vec3(1.0,0.83,0.44);' +
    'vec3 c = mix(cool, warm, clamp(vW*2.2, 0.0, 1.0));' +
    'float a = mix(0.70, 1.0, clamp(vW, 0.0, 1.0)) * core;' +
    'gl_FragColor = vec4(c, a); }'
  const VS_LINE = 'attribute vec3 aPos; attribute float aA; uniform mat4 uMVP; varying float vA;' +
    'void main(){ gl_Position = uMVP * vec4(aPos,1.0); vA = aA; }'
  const FS_LINE = 'precision mediump float; varying float vA; uniform vec3 uColor;' +
    'void main(){ gl_FragColor = vec4(uColor, vA); }'

  const compile = (type, src) => {
    const s = gl.createShader(type)
    gl.shaderSource(s, src); gl.compileShader(s)
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      throw new Error('shader: ' + gl.getShaderInfoLog(s))
    }
    return s
  }
  const link = (vs, fs) => {
    const p = gl.createProgram()
    gl.attachShader(p, compile(gl.VERTEX_SHADER, vs))
    gl.attachShader(p, compile(gl.FRAGMENT_SHADER, fs))
    gl.linkProgram(p)
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error('link: ' + gl.getProgramInfoLog(p))
    return p
  }
  let pointProg, lineProg
  try {
    pointProg = link(VS_POINT, FS_POINT)
    lineProg = link(VS_LINE, FS_LINE)
  } catch (e) {
    el.removeChild(canvas); el.removeChild(tip); el.removeChild(labelLayer)
    return null
  }
  const loc = (prog, name) => gl.getAttribLocation(prog, name)
  const uni = (prog, name) => gl.getUniformLocation(prog, name)
  const pPos = loc(pointProg, 'aPos'), pW = loc(pointProg, 'aW')
  const pMVP = uni(pointProg, 'uMVP'), pDpr = uni(pointProg, 'uDpr'), pSize = uni(pointProg, 'uSize')
  const lPos = loc(lineProg, 'aPos'), lA = loc(lineProg, 'aA'), lMVP = uni(lineProg, 'uMVP')
  const lColor = uni(lineProg, 'uColor')

  // Thick segments. gl.LINES has no usable width — ANGLE/D3D pins it to one device pixel — so a
  // relation drawn as a line is a hairline that aliases in and out of existence as the camera
  // turns, and some of them simply do not appear. Each segment is expanded into a camera-facing
  // quad in clip space instead, at a width in device pixels we choose.
  const VS_QUAD = 'attribute vec2 aPos; attribute float aA; varying float vA;' +
    'void main(){ gl_Position = vec4(aPos, 0.0, 1.0); vA = aA; }'
  let quadProg = null
  try { quadProg = link(VS_QUAD, FS_LINE) } catch (e) { quadProg = null }
  const qPos = quadProg ? loc(quadProg, 'aPos') : null
  const qA = quadProg ? loc(quadProg, 'aA') : null
  const qColor = quadProg ? uni(quadProg, 'uColor') : null
  const quadBuf = gl.createBuffer(), quadABuf = gl.createBuffer()

  const pointBuf = gl.createBuffer(), lineBuf = gl.createBuffer(), pathBuf = gl.createBuffer(),
    liveBuf = gl.createBuffer(), liveABuf = gl.createBuffer()
  let nodes = [], nodePos = new Float32Array(0), nodeW = new Float32Array(0), edges = []
  let edgePos = new Float32Array(0), edgeA = new Float32Array(0)
  let pathPos = new Float32Array(0), pathA = new Float32Array(0)
  let livePos = new Float32Array(0), liveA = new Float32Array(0)
  let sig = ''
  let pinned = null, hovered = null
  let yaw = 0.55, pitch = 0.22, dist = 2.35
  let dragging = false, lastX = 0, lastY = 0, idleAt = 0, frames = 0, stopped = false
  // The camera goes to what just fired: a firing is an event, and an event you have to hunt for
  // in a 1,400-point cloud is not an event. `focus` is where the camera is looking, `distTo` how
  // close, `dwell` until when — then it drifts back out to the whole space.
  let focus = new Float32Array([0, 0, 0]), focusTo = new Float32Array([0, 0, 0])
  let distTo = 2.35, dwell = 0, wasLit = {}
  let pathLabels = []   // the walk's own order, as labels
  let pathFocus = new Float32Array([0, 0, 0])   // where the whole path sits
  let pathDist = 2.35                            // how far back it needs the camera
  // Navigation. The automatic camera answers "what just fired"; these answer "what is that, and
  // what is it attached to", which a point cloud will not answer by spinning on its own.
  let navLock = false          // the camera is being held by a person, not by an event
  let pressX = 0, pressY = 0, pressMoved = false

  const norm = (raw) => {
    // Centre and scale once, so the camera only ever has to frame a unit cloud.
    let cx = 0, cy = 0, cz = 0
    for (const n of raw) { cx += n.x; cy += n.y; cz += n.z }
    const m = raw.length || 1
    cx /= m; cy /= m; cz /= m
    let r = 0
    for (const n of raw) {
      const d = Math.hypot(n.x - cx, n.y - cy, n.z - cz)
      if (d > r) r = d
    }
    const s = r ? 1 / r : 1
    return raw.map((n) => ({ l: n.l, w: n.w, x: (n.x - cx) * s, y: (n.y - cy) * s, z: (n.z - cz) * s }))
  }

  // k-nearest edges in the same space the stills draw in: an edge means "these two are near here".
  const buildEdges = (ns) => {
    const out = []
    const seen = new Set()
    for (let i = 0; i < ns.length; i++) {
      const a = ns[i]
      let b1 = -1, d1 = Infinity, b2 = -1, d2 = Infinity
      for (let j = 0; j < ns.length; j++) {
        if (j === i) continue
        const b = ns[j]
        const d = (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2
        if (d < d1) { d2 = d1; b2 = b1; d1 = d; b1 = j }
        else if (d < d2) { d2 = d; b2 = j }
      }
      for (const j of [b1, b2]) {
        if (j < 0) continue
        const key = i < j ? i + ':' + j : j + ':' + i
        if (seen.has(key)) continue
        seen.add(key)
        out.push([i, j])
      }
    }
    return out
  }

  const upload = (raw, trail, links) => {
    const next = norm(raw)
    // Label -> index for this upload: the path branch and the camera both need it.
    upload.byLabel = {}
    next.forEach((n, i) => { upload.byLabel[String(n.l).toLowerCase()] = i })
    pathLabels = trail || []
    const id = raw.length + '|' + (raw[0] ? raw[0].l : '') + '|' + (raw[raw.length - 1] ? raw[raw.length - 1].l : '')
    // The walk's own order. The firings are a set; the path is a sequence, and drawing it needs
    // the sequence, so it is rebuilt whenever either the ground or the trail changes.
    const pathKey = (trail || []).join('>')
    if (id !== sig || pathKey !== (upload.pathKey || '')) {
      upload.pathKey = pathKey
      const idx = (trail || []).map((l) => upload.byLabel[String(l).toLowerCase()]).filter((i) => i !== undefined)
      pathPos = new Float32Array(Math.max(0, idx.length - 1) * 6)
      pathA = new Float32Array(Math.max(0, idx.length - 1) * 2)
      for (let k = 0; k + 1 < idx.length; k++) {
        const A = next[idx[k]], B = next[idx[k + 1]]
        pathPos.set([A.x, A.y, A.z, B.x, B.y, B.z], k * 6)
        // Older hops fade; the newest segment is the brightest thing on the surface.
        const v = 0.25 + 0.75 * ((k + 1) / Math.max(1, idx.length - 1))
        pathA[k * 2] = v; pathA[k * 2 + 1] = v
      }
      if (pathPos.length) {
        gl.bindBuffer(gl.ARRAY_BUFFER, pathBuf)
        gl.bufferData(gl.ARRAY_BUFFER, pathPos, gl.STATIC_DRAW)
        // Where the camera should sit so the walk — every hop so far — is in frame.
        let cx = 0, cy = 0, cz = 0
        for (const i of idx) { cx += next[i].x; cy += next[i].y; cz += next[i].z }
        cx /= idx.length; cy /= idx.length; cz /= idx.length
        let r = 0
        for (const i of idx) {
          r = Math.max(r, Math.hypot(next[i].x - cx, next[i].y - cy, next[i].z - cz))
        }
        pathFocus = new Float32Array([cx, cy, cz])
        pathDist = Math.max(1.3, Math.min(2.6, r * 3.0))
      } else {
        pathFocus = new Float32Array([0, 0, 0])
        pathDist = 2.35
      }
    }
    // Anything that was dark last time and is lit now is a firing worth going to look at.
    const fresh = []
    for (const n of next) {
      const key = String(n.l).toLowerCase()
      const lit = (n.w || 0) > 0.05
      if (lit && !wasLit[key]) fresh.push(n)
      wasLit[key] = lit
    }
    if (fresh.length && !dragging) {
      // Two beats, in this order. A hop lands: punch in on it, close, because that is the
      // event. The dwell expires: pull back to the *path*, not to the default wide shot,
      // because a walk is the sequence and a camera that stays punched in never shows it.
      const go = fresh.reduce((a, b) => ((b.w || 0) > (a.w || 0) ? b : a), fresh[0])
      focusTo = new Float32Array([go.x, go.y, go.z])
      distTo = 0.95
      dwell = (win.performance && performance.now ? performance.now() : Date.now()) + 1800
    }
    if (id !== sig || (links || []).length !== (upload.linkN || -1)) {
      sig = id
      nodes = next
      upload.linkN = (links || []).length
      edges = buildEdges(nodes)
      nodePos = new Float32Array(nodes.length * 3)
      edgePos = new Float32Array(edges.length * 6)
      edgeA = new Float32Array(edges.length * 2).fill(0.11)
      // Real relations replace the geometric ones when the route supplies them, and they carry
      // their own strength: an edge that the ledger has seen a hundred times is not the same
      // edge as one seen once.
      const at = {}
      next.forEach((n, i) => { at[String(n.l).toLowerCase()] = i })
      const real = (links || []).map((k) => [at[String(k.a).toLowerCase()], at[String(k.b).toLowerCase()], k.w || 1])
        .filter((e) => e[0] !== undefined && e[1] !== undefined && e[0] !== e[1])
      let maxW = 1
      for (const e of real) if (e[2] > maxW) maxW = e[2]
      if (real.length) {
        edges = real.map((e) => [e[0], e[1]])
        edgePos = new Float32Array(edges.length * 6)
        edgeA = new Float32Array(edges.length * 2)
        real.forEach(([a, b, w], k) => {
          const A = nodes[a], B = nodes[b]
          edgePos.set([A.x, A.y, A.z, B.x, B.y, B.z], k * 6)
          // sqrt so the top edge is bright without flattening every weak one to invisible
          const v = 0.06 + 0.24 * Math.sqrt(w / maxW)
          edgeA[k * 2] = v; edgeA[k * 2 + 1] = v
        })
        // What is firing, and what it is connected to.
        //  - a recorded relation with both ends lit: the strongest statement the picture can make
        //  - a recorded relation with one end lit: activation crossing that relation
        //  - a walk's own hops serve one concept per message, so they rarely have a recorded
        //    partner; their connection is proximity in the projection, which is the same space
        //    the walk searches. Those are drawn dimmer, because proximity is not provenance.
        const live = []
        real.forEach(([a, b]) => {
          const wa = nodes[a].w || 0, wb = nodes[b].w || 0
          if (wa > 0.05 && wb > 0.05) live.push([nodes[a], nodes[b], Math.min(wa, wb) + 0.25])
          else if ((wa > 0.05) !== (wb > 0.05)) live.push([nodes[a], nodes[b], Math.max(wa, wb) * 0.45])
        })
        const near = (i, k2) => {
          const a = nodes[i], out = []
          let b1 = -1, d1 = Infinity, b2 = -1, d2 = Infinity
          for (let j = 0; j < nodes.length; j++) {
            if (j === i) continue
            const b = nodes[j]
            const d = (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2
            if (d < d1) { d2 = d1; b2 = b1; d1 = d; b1 = j } else if (d < d2) { d2 = d; b2 = j }
          }
          if (b1 >= 0) out.push([b1, d1])
          if (k2 > 1 && b2 >= 0) out.push([b2, d2])
          return out
        }
        for (let i = 0; i < nodes.length; i++) {
          const w = nodes[i].w || 0
          if (w <= 0.05) continue
          for (const [j, d2] of near(i, 2)) {
            const fade = 1 / (1 + 9 * Math.sqrt(d2))
            live.push([nodes[i], nodes[j], 0.10 + 0.30 * w * fade])
          }
        }
        upload.liveN = live.length
        livePos = new Float32Array(live.length * 6)
        liveA = new Float32Array(live.length * 2)
        live.forEach(([A, B, v], k) => {
          if (k >= 900) return
          livePos.set([A.x, A.y, A.z, B.x, B.y, B.z], k * 6)
          liveA[k * 2] = v; liveA[k * 2 + 1] = v
        })
        if (livePos.length) {
          gl.bindBuffer(gl.ARRAY_BUFFER, liveBuf)
          gl.bufferData(gl.ARRAY_BUFFER, livePos, gl.STATIC_DRAW)
          gl.bindBuffer(gl.ARRAY_BUFFER, liveABuf)
          gl.bufferData(gl.ARRAY_BUFFER, liveA, gl.STATIC_DRAW)
        }
      }
      nodes.forEach((n, i) => { nodePos[i * 3] = n.x; nodePos[i * 3 + 1] = n.y; nodePos[i * 3 + 2] = n.z })
      edges.forEach(([a, b], e) => {
        const A = nodes[a], B = nodes[b]
        edgePos.set([A.x, A.y, A.z, B.x, B.y, B.z], e * 6)
      })
      gl.bindBuffer(gl.ARRAY_BUFFER, lineBuf)
      gl.bufferData(gl.ARRAY_BUFFER, edgePos, gl.STATIC_DRAW)
    }
    nodeW = new Float32Array(nodes.length)
    nodes.forEach((n, i) => {
      const live = raw.length === nodes.length ? raw[i] : null
      const w = live && live.w ? live.w : n.w
      n.w = w
      nodeW[i] = w
    })
    gl.bindBuffer(gl.ARRAY_BUFFER, pointBuf)
    gl.bufferData(gl.ARRAY_BUFFER, nodePos, gl.STATIC_DRAW)
    const wBuf = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, wBuf)
    gl.bufferData(gl.ARRAY_BUFFER, nodeW, gl.STATIC_DRAW)
    upload.wBuf = wBuf
    report({ nodes: nodes.length, edges: edges.length,
      lit: nodeW.reduce((a, b) => a + (b > 0.05 ? 1 : 0), 0) })
  }

  const perspective = (fovy, aspect, near, far) => {
    const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far)
    return new Float32Array([f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0])
  }
  const mul = (a, b) => {
    const o = new Float32Array(16)
    for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) {
      o[c * 4 + r] = a[r] * b[c * 4] + a[4 + r] * b[c * 4 + 1] + a[8 + r] * b[c * 4 + 2] + a[12 + r] * b[c * 4 + 3]
    }
    return o
  }
  const mvpNow = () => {
    const w = canvas.width || 1, h = canvas.height || 1
    const P = perspective(0.78, w / h, 0.05, 12)
    const cy = Math.cos(pitch), sy = Math.sin(pitch)
    const cx = Math.cos(yaw), sx = Math.sin(yaw)
    const Rx = new Float32Array([1, 0, 0, 0, 0, cy, sy, 0, 0, -sy, cy, 0, 0, 0, 0, 1])
    const Ry = new Float32Array([cx, 0, -sx, 0, 0, 1, 0, 0, sx, 0, cx, 0, 0, 0, 0, 1])
    const T = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, -dist, 1])
    const F = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -focus[0], -focus[1], -focus[2], 1])
    return mul(P, mul(T, mul(Rx, mul(Ry, F))))
  }

  const resize = () => {
    const dpr = win.devicePixelRatio || 1
    const w = Math.max(1, Math.round((el.clientWidth || 640) * dpr))
    const h = Math.max(1, Math.round((el.clientHeight || 480) * dpr))
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h }
  }

  // One segment -> two triangles, in pixels, then back to clip space.
  const segQuads = (posArr, alphaArr, flatA, widthPx, MVP) => {
    const n = posArr.length / 6
    const W = canvas.width, H = canvas.height
    const px = new Float32Array(n * 12), pa = new Float32Array(n * 6)
    let k = 0, ka = 0
    for (let i = 0; i < n; i++) {
      const o = i * 6
      const ax = posArr[o], ay = posArr[o + 1], az = posArr[o + 2]
      const bx = posArr[o + 3], by = posArr[o + 4], bz = posArr[o + 5]
      const cwA = MVP[3] * ax + MVP[7] * ay + MVP[11] * az + MVP[15]
      const cwB = MVP[3] * bx + MVP[7] * by + MVP[11] * bz + MVP[15]
      if (cwA <= 0.02 || cwB <= 0.02) continue
      const cxA = MVP[0] * ax + MVP[4] * ay + MVP[8] * az + MVP[12]
      const cyA = MVP[1] * ax + MVP[5] * ay + MVP[9] * az + MVP[13]
      const cxB = MVP[0] * bx + MVP[4] * by + MVP[8] * bz + MVP[12]
      const cyB = MVP[1] * bx + MVP[5] * by + MVP[9] * bz + MVP[13]
      const x0 = ((cxA / cwA) * 0.5 + 0.5) * W, y0 = (1 - ((cyA / cwA) * 0.5 + 0.5)) * H
      const x1 = ((cxB / cwB) * 0.5 + 0.5) * W, y1 = (1 - ((cyB / cwB) * 0.5 + 0.5)) * H
      const dx = x1 - x0, dy = y1 - y0
      const len = Math.hypot(dx, dy)
      if (len < 0.35) continue
      const hw = Math.max(0.55, widthPx * 0.5)
      const nx = (-dy / len) * hw, ny = (dx / len) * hw
      const a = alphaArr ? alphaArr[i * 2] : flatA
      const v = [x0 + nx, y0 + ny, x0 - nx, y0 - ny, x1 + nx, y1 + ny,
                 x0 - nx, y0 - ny, x1 - nx, y1 - ny, x1 + nx, y1 + ny]
      for (let j = 0; j < 12; j += 2) {
        px[k++] = ((v[j] / W) * 2) - 1
        px[k++] = 1 - ((v[j + 1] / H) * 2)
      }
      for (let j = 0; j < 6; j++) pa[ka++] = a
    }
    if (!k) return 0
    gl.useProgram(quadProg)
    gl.bindBuffer(gl.ARRAY_BUFFER, quadBuf)
    gl.bufferData(gl.ARRAY_BUFFER, px.subarray(0, k), gl.DYNAMIC_DRAW)
    gl.enableVertexAttribArray(qPos)
    gl.vertexAttribPointer(qPos, 2, gl.FLOAT, false, 0, 0)
    gl.bindBuffer(gl.ARRAY_BUFFER, quadABuf)
    gl.bufferData(gl.ARRAY_BUFFER, pa.subarray(0, ka), gl.DYNAMIC_DRAW)
    gl.enableVertexAttribArray(qA)
    gl.vertexAttribPointer(qA, 1, gl.FLOAT, false, 0, 0)
    gl.drawArrays(gl.TRIANGLES, 0, k / 2)
    return k / 2
  }

  const draw = () => {
    if (stopped) return
    resize()
    gl.viewport(0, 0, canvas.width, canvas.height)
    gl.clearColor(0.027, 0.031, 0.043, 1)
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT)
    gl.enable(gl.DEPTH_TEST)
    gl.enable(gl.BLEND)
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE)
    const MVP = mvpNow()
    const dpr = win.devicePixelRatio || 1
    // Edges are quads, not lines: a hairline is not a relation you can see.
    if (quadProg && edgePos.length) {
      gl.uniform3f(qColor, 0.58, 0.62, 0.80)
      segQuads(edgePos, null, 0.26, 1.5 * dpr, MVP)
    }
    // Connections carrying activation, then the trail on top of them.
    if (quadProg && livePos.length) {
      gl.uniform3f(qColor, 1.0, 0.66, 0.34)
      segQuads(livePos, liveA, 0.3, 2.0 * dpr, MVP)
    }
    if (quadProg && pathPos.length) {
      gl.uniform3f(qColor, 1.0, 0.80, 0.42)
      segQuads(pathPos, pathA, 0.8, 2.4 * dpr, MVP)
    }
    gl.useProgram(pointProg)
    gl.uniformMatrix4fv(pMVP, false, MVP)
    gl.uniform1f(pDpr, win.devicePixelRatio || 1)
    gl.uniform1f(pSize, 1.0)
    gl.bindBuffer(gl.ARRAY_BUFFER, pointBuf)
    gl.enableVertexAttribArray(pPos); gl.vertexAttribPointer(pPos, 3, gl.FLOAT, false, 0, 0)
    gl.bindBuffer(gl.ARRAY_BUFFER, upload.wBuf || pointBuf)
    gl.enableVertexAttribArray(pW); gl.vertexAttribPointer(pW, 1, gl.FLOAT, false, 0, 0)
    gl.drawArrays(gl.POINTS, 0, nodePos.length / 3)
    frames++
    placeLabels(MVP)
    report({ frames, yaw: +yaw.toFixed(3), pitch: +pitch.toFixed(3), dist: +dist.toFixed(3),
      hover: hovered, pinned, labels: placeLabels.k || 0, litN: placeLabels.lit || 0, liveN: upload.liveN || 0, linksN: upload.linkN || 0 })
  }

  let rafId = 0
  const loop = (ts) => {
    if (stopped) return
    rafId = win.requestAnimationFrame ? win.requestAnimationFrame(loop) : win.setTimeout(() => loop(Date.now()), 16)
    if (!dragging && !navLock && ts && idleAt && ts - idleAt > 2600) yaw += 0.00022 * (ts - (loop.lastTs || ts))
    if (dwell && ts && ts > dwell) {
      dwell = 0
      // Back out to the whole walk when there is one; the origin only when there is not.
      distTo = pathDist
      focusTo = new Float32Array([pathFocus[0], pathFocus[1], pathFocus[2]])
    }
    // Ease toward the target rather than cutting: the cloud should carry you there.
    for (let i = 0; i < 3; i++) focus[i] += (focusTo[i] - focus[i]) * 0.08
    dist += (distTo - dist) * 0.07
    loop.lastTs = ts
    // A pane that is not on screen draws nothing: the shell mounts a surface per route, and an
    // off-screen instance would otherwise burn frames on a cloud nobody is looking at.
    const visible = (el.clientWidth || 0) > 0 && (el.clientHeight || 0) > 0
    if (nodes.length && visible) draw()
  }

  // ---- interaction ------------------------------------------------------------
  const project = (MVP) => {
    // Screen-space positions, so hover can be decided in pixels rather than in the cloud.
    const out = []
    const w = canvas.width, h = canvas.height
    for (let i = 0; i < nodes.length; i++) {
      const x = nodePos[i * 3], y = nodePos[i * 3 + 1], z = nodePos[i * 3 + 2]
      const cx = MVP[0] * x + MVP[4] * y + MVP[8] * z + MVP[12]
      const cy = MVP[1] * x + MVP[5] * y + MVP[9] * z + MVP[13]
      const cw = MVP[3] * x + MVP[7] * y + MVP[11] * z + MVP[15]
      if (cw <= 0.001) { out.push(null); continue }
      out.push([(cx / cw * 0.5 + 0.5) * w, (1 - (cy / cw * 0.5 + 0.5)) * h])
    }
    return out
  }
  const placeLabels = (MVP) => {
    const dpr = win.devicePixelRatio || 1
    const w = canvas.width / dpr, h = canvas.height / dpr
    const pts = project(MVP)
    const lit = []
    for (let i = 0; i < nodes.length; i++) {
      if ((nodes[i].w || 0) > 0.05 && pts[i]) lit.push([i, nodes[i].w || 0])
    }
    lit.sort((a, b) => b[1] - a[1])
    const boxes = []
    let k = 0
    for (const [i, wt] of lit) {
      if (k >= 9) break
      const x = pts[i][0] / dpr, y = pts[i][1] / dpr
      if (x < -40 || y < -20 || x > w + 40 || y > h + 20) continue
      const text = String(nodes[i].l)
      const tw = text.length * 6.1 + 6
      // Two names on top of each other are one unreadable name: the strongest wins the space.
      let clash = false
      for (const b of boxes) {
        if (Math.abs(b[0] - x) < (b[2] + tw) / 2 + 4 && Math.abs(b[1] - y) < 14) { clash = true; break }
      }
      if (clash) continue
      boxes.push([x, y, tw])
      const node = labelEls[k] || makeLabel()
      k++
      node.textContent = text
      node.style.transform = 'translate(' + Math.round(x + 7) + 'px,' + Math.round(y - 8) + 'px)'
      node.style.opacity = wt > 0.2 ? '0.95' : '0.6'
    }
    for (let j = k; j < labelEls.length; j++) labelEls[j].style.opacity = '0'
    placeLabels.k = k
    placeLabels.lit = lit.length
    placeLabels.has = nodes.length ? typeof nodes[0].w : 'no nodes'
  }

  const pick = (px, py) => {
    const pts = project(mvpNow())
    let best = null, bestD = 18 * (win.devicePixelRatio || 1)
    for (let i = 0; i < pts.length; i++) {
      const p = pts[i]
      if (!p) continue
      const d = Math.hypot(p[0] - px, p[1] - py)
      if (d < bestD) { bestD = d; best = i }
    }
    return best
  }
  const showTip = (i, cx, cy) => {
    if (i == null || !nodes[i]) { tip.style.opacity = '0'; return }
    const n = nodes[i]
    tip.textContent = n.w > 0.05 ? n.l + ' · firing' : n.l
    tip.style.left = Math.max(6, cx + 12) + 'px'
    tip.style.top = Math.max(6, cy + 12) + 'px'
    tip.style.opacity = '1'
  }
  const bump = (what) => {
    const g = (win.__antemuse && win.__antemuse.g3s && win.__antemuse.g3s[INSTANCE]) || {}
    const ev = Object.assign({}, g.ev || {})
    ev[what] = (ev[what] || 0) + 1
    report({ ev })
  }
  const now = () => (win.performance && performance.now ? performance.now() : Date.now())
  const at = (i) => {
    if (i == null || !nodes[i]) return null
    return new Float32Array([nodePos[i * 3], nodePos[i * 3 + 1], nodePos[i * 3 + 2]])
  }
  // Go to a node and stay there. This is the navigation the graph was missing: the cloud has one
  // camera and it was owned entirely by whatever fired last.
  const gotoNode = (i) => {
    const f = at(i)
    if (!f) return false
    focusTo = f
    distTo = 0.95
    navLock = true
    dwell = now() + 1e9          // held until the person lets go of it
    pinned = nodes[i].l
    idleAt = now()
    report({ pinned, nav: 'node' })
    return true
  }
  // Back to the whole walk, which is the view the pane is for.
  const fit = () => {
    dwell = 0
    navLock = false
    distTo = pathDist
    focusTo = new Float32Array([pathFocus[0], pathFocus[1], pathFocus[2]])
    pinned = null
    tip.style.opacity = '0'
    idleAt = now()
    report({ pinned, nav: 'fit' })
  }
  const onDown = (e) => {
    bump('down')
    dragging = true; lastX = e.clientX; lastY = e.clientY
    pressX = e.clientX; pressY = e.clientY; pressMoved = false
    canvas.style.cursor = 'grabbing'; idleAt = 0
    if (canvas.focus) canvas.focus()
  }
  const onMove = (e) => {
    bump('move')
    if (dragging) {
      if (Math.hypot(e.clientX - pressX, e.clientY - pressY) > 4) pressMoved = true
      yaw -= (e.clientX - lastX) * 0.006
      pitch = Math.max(-1.35, Math.min(1.35, pitch - (e.clientY - lastY) * 0.006))
      lastX = e.clientX; lastY = e.clientY
      idleAt = now()
      return
    }
    const r = canvas.getBoundingClientRect()
    const i = pick((e.clientX - r.left) * (win.devicePixelRatio || 1), (e.clientY - r.top) * (win.devicePixelRatio || 1))
    hovered = i == null ? null : nodes[i].l
    showTip(i, e.clientX - r.left, e.clientY - r.top)
    canvas.style.cursor = i == null ? 'grab' : 'pointer'
  }
  const onUp = (e) => {
    dragging = false; canvas.style.cursor = 'grab'; idleAt = now()
    if (pressMoved) { pressMoved = false; return }   // that was an orbit, not a click
    const r = canvas.getBoundingClientRect()
    const i = pick((e.clientX - r.left) * (win.devicePixelRatio || 1),
                   (e.clientY - r.top) * (win.devicePixelRatio || 1))
    if (i == null) { fit(); return }                  // empty space means "show me the walk"
    if (gotoNode(i)) showTip(i, e.clientX - r.left, e.clientY - r.top)
  }

  // Keys, because a pane you can only navigate by dragging is a pane you cannot navigate.
  const onKey = (e) => {
    const k = String(e.key || '').toLowerCase()
    idleAt = now()
    if (k === 'arrowleft') { yaw += 0.12; navLock = true } else if (k === 'arrowright') { yaw -= 0.12; navLock = true }
    else if (k === 'arrowup') { pitch = Math.max(-1.35, pitch - 0.08); navLock = true } else if (k === 'arrowdown') { pitch = Math.min(1.35, pitch + 0.08); navLock = true }
    else if (k === '+' || k === '=') { dist = Math.max(1.15, dist * 0.88) }
    else if (k === '-' || k === '_') { dist = Math.min(7.5, dist * 1.12) }
    else if (k === 'f') { fit() }
    else if (k === 'escape') { fit() }
    else return
    e.preventDefault()
    report({ yaw: +yaw.toFixed(3), pitch: +pitch.toFixed(3), dist: +dist.toFixed(3) })
  }
  const onWheel = (e) => {
    bump('wheel')
    e.preventDefault()
    dist = Math.max(1.15, Math.min(7.5, dist * (1 + Math.sign(e.deltaY) * 0.08)))
  }
  const onLeave = () => { hovered = null; if (!pinned) tip.style.opacity = '0' }

  // Capture phase on the document, filtered to this pane: the shell puts its own listeners on the
  // way down the tree, and a pointerdown that stops propagating never reaches a listener on the
  // canvas — which made drag look broken while wheel kept working.
  const mine = (e) => !!(e.target && (e.target === canvas || el.contains(e.target)))
  const guard = (fn) => (e) => { if (mine(e)) fn(e) }
  const gDown = guard(onDown), gMove = guard(onMove), gUp = guard(onUp)
  const gWheel = guard(onWheel), gLeave = guard(onLeave)
  doc.addEventListener('pointerdown', gDown, true)
  doc.addEventListener('pointermove', gMove, true)
  doc.addEventListener('pointerup', gUp, true)
  doc.addEventListener('pointerleave', gLeave, true)
  doc.addEventListener('wheel', gWheel, { capture: true, passive: false })
  canvas.tabIndex = 0
  canvas.setAttribute('aria-label', 'concept map: drag to orbit, click a node to go to it, f to fit')
  canvas.addEventListener('keydown', onKey)

  // ---- data -------------------------------------------------------------------
  // Preview aids, same convention as `antemuse:scene`, never on by themselves: a pasted
  // `antemuse:graph3d-json` payload, or a fixed synthetic cloud for `antemuse:graph3d-demo`.
  const demo = (() => {
    try { return win.localStorage.getItem('antemuse:graph3d-demo') === '1' } catch (e) { return false }
  })()
  // A real `/graph` payload pasted into `antemuse:graph3d-json` is drawn instead, so the surface
  // can be looked at (or filmed) on a machine whose gateway predates the route. The nodes are
  // whatever was pasted; nothing is synthesised here.
  const pasted = () => {
    try {
      const raw = win.localStorage.getItem('antemuse:graph3d-json')
      if (!raw) return null
      const box = JSON.parse(raw)
      return box && box.nodes && box.nodes.length ? box : null
    } catch (e) { return null }
  }
  const demoCloud = () => {
    let seed = 7
    const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648 }
    const out = []
    for (let i = 0; i < 620; i++) {
      const t2 = rnd() * Math.PI * 2, ph = Math.acos(2 * rnd() - 1), r = Math.cbrt(rnd())
      out.push({ l: 'n' + i, w: i % 97 === 0 ? 0.6 + rnd() * 0.4 : 0,
        x: r * Math.sin(ph) * Math.cos(t2), y: r * Math.cos(ph) * 0.62, z: r * Math.sin(ph) * Math.sin(t2) })
    }
    return out
  }
  const pull = () => {
    if (stopped || typeof ctx.rest !== 'function') return
    if (!(el.clientWidth || 0) || !(el.clientHeight || 0)) return
    const session = host && host.state && host.state.focusedSessionId
      ? host.state.focusedSessionId.get() : ''
    // One route, asked for one more thing. `/graph` is a separate path, and a path is only mounted
    // when the host process boots — which is why this pane spent hours polling a route its backend
    // did not have. The map now rides on `/state`, the one route every backend has had for months,
    // so new data never again waits on a host restart.
    const q = '/state?graph=1&stills=0' + (session ? '&session=' + encodeURIComponent(session) : '')
    const askedAt = performance.now()
    const slow = new Promise((_, reject) => setTimeout(() => reject(new Error('graph timeout')), 12000))
    Promise.race([Promise.resolve(ctx.rest(q)), slow]).then((seed) => {
      if (stopped) return
      const g = seed && seed.graph ? seed.graph : (seed && seed.nodes ? seed : null)
      report({ routeMs: Math.round(performance.now() - askedAt), fails: 0, session: session || '' })
      boot('graph:' + (g ? (g.nodes ? g.nodes.length : 'nonodes') : 'none'))
      if (!g || !g.nodes || !g.nodes.length) {
        const local = pasted()
        if (local) upload(local.nodes, local.path || [], local.links || [])
        else if (demo) upload(demoCloud())
        return
      }
      // An explicitly pasted payload wins over the live route. It is only ever there because
      // someone put it there to look at something specific; silently replacing it with whatever
      // the host happens to be serving makes the hook useless the moment the route works.
      const pastedBox = pasted()
      if (pastedBox) {
        upload(pastedBox.nodes, pastedBox.path || [], pastedBox.links || [])
        boot('pasted:' + pastedBox.nodes.length + (pastedBox.path && pastedBox.path.length ? ' path:' + pastedBox.path.length : ''))
        el.querySelectorAll('[data-antemuse-bake], img, canvas:not([data-antemuse-3d])').forEach((im) => {
          if (im.style.opacity !== '0') im.style.opacity = '0'
        })
        return
      }
      const changed = sig !== g.nodes.length + '|' + g.nodes[0].l + '|' + g.nodes[g.nodes.length - 1].l
      upload(g.nodes, g.path || [], g.links || [])
      // Hide the still layers on every good poll, not only when the map itself changed. The stills
      // are re-created as the state advances, so a new bake image arrives at full opacity and ghosts
      // through the cloud as a pair of translucent bands — which is what the pane was serving.
      el.querySelectorAll('[data-antemuse-bake], img').forEach((im) => { im.style.opacity = '0' })
    }, (e) => {
      // A timeout is a number, not a mood: keep how long the route took to not answer.
      report({ routeMs: Math.round(performance.now() - askedAt), lastErr: String(e && e.message || e).slice(0, 60),
        fails: (((win.__antemuse || {}).g3s || {})[INSTANCE] || {}).fails ? (((win.__antemuse || {}).g3s || {})[INSTANCE] || {}).fails + 1 : 1 })
      boot('grapherr:' + (e && e.message ? e.message : e))
      const local = pasted()
      if (local) upload(local.nodes, local.path || [], local.links || [])
      else if (demo) upload(demoCloud())
    })
  }
  const hideStills = () => {
    // From the moment this surface can draw, the stills behind it are not the picture.
    // Three kinds of layer can sit behind this surface: the baked JPEGs, a plain <img>, and the
    // art canvas itself. The canvas mattered most — the 3D surface has an alpha channel, so the
    // art canvas underneath showed through its empty rows as two translucent bands across the map.
    el.querySelectorAll('[data-antemuse-bake], img, canvas:not([data-antemuse-3d])').forEach((im) => {
      // Only write when it differs, or this observer would wake itself forever.
      if (im.style.opacity !== '0') im.style.opacity = '0'
    })
  }
  hideStills()
  // A polling loop is the wrong shape for this: the stills are inserted fresh every time a state
  // advances, so between sweeps a new image sits at full opacity and paints a translucent band
  // across the cloud. Hide each one as it arrives, and on any style change that would show it.
  const stillsGuard = new win.MutationObserver(hideStills)
  stillsGuard.observe(el, { childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class', 'src'] })
  if (typeof ctx.onDispose === 'function') ctx.onDispose(() => stillsGuard.disconnect())

  // Draw what is already known first: a pasted payload must not wait on a gateway that may never
  // answer, and neither should the pane wait for its first poll to have a shape.
  try {
    const early = pasted()
    boot(early ? 'pasted:' + early.nodes.length : 'nopaste')
    if (early) upload(early.nodes, early.path || [], early.links || [])
    else if (demo) upload(demoCloud())
  } catch (e) {
    boot('early:' + (e && e.message ? e.message : e))
  }
  pull()
  const timer = typeof ctx.setInterval === 'function' ? ctx.setInterval(pull, 4000) : setInterval(pull, 4000)
  rafId = win.requestAnimationFrame ? win.requestAnimationFrame(loop) : win.setTimeout(() => loop(Date.now()), 16)

  return {
    dispose: () => {
      stopped = true
      try { if (win.cancelAnimationFrame) win.cancelAnimationFrame(rafId); else win.clearTimeout(rafId) } catch (e) {}
      try { if (typeof ctx.clearInterval === 'function' && typeof ctx.setInterval === 'function') ctx.clearInterval(timer); else clearInterval(timer) } catch (e) {}
      doc.removeEventListener('pointerdown', gDown, true)
      doc.removeEventListener('pointermove', gMove, true)
      doc.removeEventListener('pointerup', gUp, true)
      doc.removeEventListener('pointerleave', gLeave, true)
      doc.removeEventListener('wheel', gWheel, { capture: true })
      if (canvas.parentNode) canvas.parentNode.removeChild(canvas)
      if (tip.parentNode) tip.parentNode.removeChild(tip)
      const lose = gl.getExtension('WEBGL_lose_context')
      if (lose) lose.loseContext()
    }
  }
}


/**
 * The picture, filling whatever box it is given — a dock pane or a route page.
 * This is where the art belongs: its own surface, no transcript underneath, so
 * ink can run at full strength instead of the wash a fixed overlay needed.
 */
function ArtSurface({ ctx }) {
  const box = useRef(null)

  useEffect(() => {
    const el = box.current
    if (!el) return
    const doc = el.ownerDocument
    const canvas = doc.createElement('canvas')
    canvas.setAttribute('data-antemuse-art', 'pane')
    canvas.setAttribute('aria-hidden', 'true')
    canvas.style.cssText = 'display:block;width:100%;height:100%'
    el.appendChild(canvas)

    // Full ink: nothing is read through this surface, so the ceiling that
    // exists for the chat overlay does not apply here.
    const art = createArt(canvas, { dark: true, strength: LAYER.defaultStrength * 2.8, front: false })

    // Stills, not a loop: three frames of a state, held and dissolved into the
    // next. Two stacked <img> layers make the dissolve a cross-fade, so a state
    // change (or the next still) is never a cut and never flashes an unloaded
    // frame. The canvas underneath keeps painting the live kit as a fallback.
    const mkStill = () => {
      const im = doc.createElement('img')
      im.setAttribute('data-antemuse-bake', 'still')
      im.setAttribute('aria-hidden', 'true')
      im.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity ' + FADE_MS + 'ms ease;display:block'
      el.appendChild(im)
      return im
    }
    const layers = [mkStill(), mkStill()]
    let front = 0
    let stills = []
    let stillIdx = 0
    let bake = null

    // A frame is only revealed once its bytes are in. Setting opacity before the load lands
    // showed the browser's broken-image glyph at full size whenever a URL did not resolve —
    // which is exactly what a remote desktop sees when the picture lives on another machine.
    const show = (url) => new Promise((resolve) => {
      const back = layers[1 - front]
      let settled = false
      const done = (ok) => {
        if (settled) return
        settled = true
        back.onload = null
        back.onerror = null
        if (!ok) { resolve(false); return }
        back.style.opacity = '1'
        layers[front].style.opacity = '0'
        front = 1 - front
        resolve(true)
      }
      back.onload = () => done(true)
      back.onerror = () => done(false)
      back.src = url
      // A cached frame may already be complete and never fire onload.
      if (back.complete) done(back.naturalWidth > 0)
    })

    // Activation stills, when the backend sends them: the live concept map for the state that
    // is running. Absent or empty means nothing is firing, and the baked scene draws instead.
    const applyActivation = async (urls) => {
      if (!urls || !urls.length) return false
      const sig = 'activation:' + urls.join('|')
      if (bake === sig) return true
      const ok = await show(urls[0])
      if (!ok) return false
      bake = sig
      stills = urls.slice()
      stillIdx = 0
      if (win.__antemuse) win.__antemuse.bake = 'activation'
      return true
    }

    // The one path that works when the pane is on another computer: the bytes come back over the
    // same gateway RPC the status already uses, so no cookie and no host path is needed. Three
    // frames, fetched once per still set, carried as data URLs.
    const fromB64 = async (paths) => {
      if (!paths || !paths.length || !ctx || typeof ctx.rest !== 'function') return false
      const sig = 'b64:' + paths.join('|')
      if (bake === sig) return true
      try {
        const urls = []
        for (const q of paths) {
          const body = await Promise.resolve(ctx.rest(q))
          if (!body || !body.data) return false
          urls.push('data:' + (body.type || 'image/jpeg') + ';base64,' + body.data)
        }
        const ok = await show(urls[0])
        if (!ok) return false
        bake = sig
        stills = urls
        stillIdx = 0
        if (win.__antemuse) win.__antemuse.bake = 'activation'
        return true
      } catch (e) {
        return false
      }
    }

    // Live stills the backend baked for this state. plugin-data sits beside the plugin
    // directory, so the path is derivable from this module's own URL; the pane is a file:// page
    // and can only ask for a path it can predict, never a listing. A missing file falls back.
    const liveStills = (key) => {
      // Same two-step the baked stills use: a real module URL when there is one, and the installed
      // path when the module is bundled and import.meta.url is not a file. plugin-data is the
      // sibling directory of the plugin install.
      const names = [0, 1, 2].map((i) => 'f' + i + '.jpg')
      try {
        const base = new URL('../../plugin-data/antemuse/activation/' + key + '/', import.meta.url)
        return names.map((n) => new URL(n, base).href)
      } catch (e) {
        return names.map((n) => 'file:///home/ryan/.hermes/plugin-data/antemuse/activation/' + key + '/' + n)
      }
    }

    const tryLive = (key) => {
      const urls = liveStills(key)
      if (!urls.length) return false
      const probe = new win.Image()
      let settled = false
      probe.onload = () => { if (!settled) { settled = true; applyActivation(urls) } }
      probe.onerror = () => { if (!settled) { settled = true; clearLayers() } }
      probe.src = urls[0]
      return true
    }

    // Nothing firing means nothing drawn. The layers are emptied rather than filled with
    // something that is not the activation.
    const clearLayers = () => {
      bake = null
      stills = []
      stillIdx = 0
      layers.forEach((l) => {
        l.style.opacity = '0'
        l.removeAttribute('src')
      })
      if (win.__antemuse) win.__antemuse.bake = null
    }

    const win = doc.defaultView || window
    const hasRaf = typeof win.requestAnimationFrame === 'function'
    const raf = hasRaf
      ? (cb) => win.requestAnimationFrame(cb)
      : (cb) => win.setTimeout(() => cb(Date.now()), 16)
    // Without a real rAF (a headless mount) the timer fallback is bounded: a
    // pane that cannot be seen does not need a clock that never stops.
    let budget = hasRaf ? Infinity : 8
    const cancel = typeof win.cancelAnimationFrame === 'function'
      ? (id) => win.cancelAnimationFrame(id)
      : (id) => win.clearTimeout(id)

    let stopped = false
    let rafId = 0
    let last = 0
    let lastPaint = 0
    const MIN_MS = 1000 / 30

    const fit = () => {
      const w = el.clientWidth || 420
      const h = el.clientHeight || 640
      art.resize(w, h, win.devicePixelRatio || 1)
    }
    fit()

    const tick = (ts) => {
      if (stopped || budget-- <= 0) return
      rafId = raf(tick)
      if (bake) return   // stills are advanced by the hold timer, not the frame clock
      if (!last) last = ts
      if (ts - lastPaint < MIN_MS) return
      const dt = Math.min(0.12, (ts - last) / 1000)
      last = ts
      lastPaint = ts
      art.render(dt)
      if (win.__antemuse) win.__antemuse.paneFrame = art.stats().frames
    }
    raf(tick)

    const say = () => {
      if (stopped || !ctx || typeof ctx.rest !== 'function') return
      const busy = host.state.busy.get() ? 1 : 0
      const session = host.state.focusedSessionId.get()
      const q = '/state?cols=48&rows=24&fit=cover&busy=' + busy + (session ? '&session=' + encodeURIComponent(session) : '')
      Promise.resolve(ctx.rest(q)).then((p) => {
        try {
          win.__antemuse = Object.assign(win.__antemuse || {}, {
            asked: q,
            got: p === undefined ? 'undefined' : p === null ? 'null' : typeof p,
            keys: p && typeof p === 'object' ? Object.keys(p) : String(p).slice(0, 120),
            stills: p && p.stills ? p.stills.length : -1,
            b64: p && p.stills_b64 ? p.stills_b64.length : -1,
            note: p && p.still_note,
            plugin: p && p.plugin,
            server: p && p.server
          })
        } catch (e) { /* diagnostics never break the pane */ }
        const key = (p && p.active && p.active.key) || (busy ? 'work' : 'idle')
        if (stopped) return
        // The canvas is a neutral ground now: the only picture is the activation itself.
        art.setScene('idle')
        // A remote desktop shows this pane on a different computer: the stills live on the host,
        // so only an absolute URL reaches them. On the host itself the file:// paths are cheaper
        // and work without a token. The probe covers a backend too old to say either.
        // Every leg is offered, in order of how likely the surface is to reach the bytes: an
        // absolute URL (a remote desktop), the file:// paths (a desktop on the host), the same
        // bytes over the gateway RPC, and finally a probe at the local data dir. Picking one leg
        // up front is how a 404 on the first one used to hide the leg that would have worked.
        const legs = []
        if (p && p.files_http && p.files_http.length) legs.push(p.files_http)
        if (p && p.files && p.files.length) legs.push(p.files)
        if (p && p.stills && p.stills.length) legs.push(p.stills)
        const paint = async () => {
          // In order of how likely the surface is to reach the bytes: an absolute URL, the same
          // bytes over the gateway RPC (a remote desktop), a file on this machine, then baked art.
          for (const leg of legs) {
            if (stopped) return
            if (await applyActivation(leg)) return
          }
          if (await fromB64(p && p.stills_b64)) return
          if (!tryLive(key)) clearLayers()
        }
        void paint()
      }, (e) => {
        try { win.__antemuse = Object.assign(win.__antemuse || {}, { error: String(e && e.message || e).slice(0, 200) }) } catch (_e) {}
      })
    }
    // Preview aid: `localStorage['antemuse:scene'] = 'walk'` pins one scene, so a
    // composition can be looked at without driving the agent into that state.
    let preview = null
    try { preview = win.localStorage.getItem('antemuse:scene') } catch (e) { /* no storage */ }
    if (preview) art.setScene(preview)

    // The space, above the stills: the same map, turnable. The JPEG cross-fade stays underneath as
    // the fallback for a pane with no WebGL or a backend that cannot serve /graph.
    let graph3d = null
    try {
      graph3d = createGraph3D(el, doc, ctx, host, win)
    } catch (e) {
      graph3d = null
      // Named, not silent: a surface that fails to build must say why, or the pane just looks
      // like it has nothing to draw.
      try {
        win.__antemuse = win.__antemuse || {}
        win.__antemuse.g3boot = (win.__antemuse.g3boot || '') + '|throw:' + (e && e.message ? e.message : e)
      } catch (_e) {}
    }

    if (!preview) say()
    // Host-managed timer where the SDK provides one, so disposal is the host's
    // job too and a pane close cannot leave a poll running.
    // The stills hold on their own clock, so the picture breathes even when the
    // state has not changed; the 4 s poll only decides which state's stills.
    const advance = () => {
      if (bake && stills.length) {
        stillIdx = (stillIdx + 1) % stills.length
        show(stills[stillIdx])
      }
    }
    const hold = typeof ctx.setInterval === 'function'
      ? ctx.setInterval(advance, HOLD_MS)
      : win.setInterval(advance, HOLD_MS)
    const poll = preview ? () => {} : (typeof ctx.setInterval === 'function'
      ? ctx.setInterval(say, 4000)
      : win.setInterval(say, 4000))

    const ro = typeof win.ResizeObserver === 'function' ? new win.ResizeObserver(fit) : null
    if (ro) ro.observe(el)
    else win.addEventListener('resize', fit)

    return () => {
      stopped = true
      if (typeof poll === 'function') poll()
      else win.clearInterval(poll)
      if (typeof hold === 'function') hold()
      else win.clearInterval(hold)
      if (ro) ro.dispose ? ro.dispose() : ro.disconnect()
      else win.removeEventListener('resize', fit)
      cancel(rafId)
      if (graph3d) { try { graph3d.dispose() } catch (e) { /* gone */ } }
      if (canvas.parentNode) canvas.parentNode.removeChild(canvas)
    }
  }, [ctx])

  return jsx('div', { ref: box, style: { position: 'absolute', inset: 0, overflow: 'hidden' } })
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
      jsx(ArtSurface, { ctx }),
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

// Baked scenes: rendered by a real renderer offline, shipped as frame loops,
// because a runtime plugin cannot import three. Only the states that earn it get
// a bake; the rest fall through to the live kit.
// There are no baked scenes any more. The activation of the concept graph is the only
// visualization: what a state looks like IS which concepts are firing while it runs. A state
// with nothing firing has no picture, and the surface stays bare rather than showing stand-in
// art for a moment that did not happen.
const HOLD_MS = 6000
const FADE_MS = 900

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


// ---------------------------------------------------------------------------
// A solid, in-file. The host forbids importing three, so this is the smallest
// honest 3D that still looks machined: a chamfered slab and a ring, rotated,
// projected, flat-shaded by two lights, then handed to the same glyph sampler.
// AsciiEffect's contract is kept (evaluate luminance, pick a ramp character,
// carry per-character colour) — only the source of the pixels changed.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// The kit. A scene is data: parts, each a mesh plus where it sits, how it turns
// and which light owns it. three would give a scene graph and a material
// system; the host forbids importing it, so this is the subset that actually
// carries the look — meshes, transforms, two lights, a depth sort — and the
// animation comes from turning parts, not from a player.
// ---------------------------------------------------------------------------

function norm3(x, y, z) {
  const l = Math.hypot(x, y, z) || 1
  return [x / l, y / l, z / l]
}

/** A box with chamfered top and bottom faces — a machined slab, not a cube. */
function chamferedBox(w, t, d, c) {
  const rings = [
    [t, w - c, d - c],
    [t - c * 0.62, w, d],
    [-t + c * 0.62, w, d],
    [-t, w - c, d - c]
  ]
  const V = []
  for (const [y, sx, sz] of rings) {
    V.push([-sx, y, -sz], [sx, y, -sz], [sx, y, sz], [-sx, y, sz])
  }
  const F = []
  const quad = (a, b, c2, d2) => F.push([a, b, c2], [a, c2, d2])
  for (let r = 0; r < rings.length - 1; r++) {
    for (let i = 0; i < 4; i++) {
      const j = (i + 1) % 4
      quad(r * 4 + i, r * 4 + j, (r + 1) * 4 + j, (r + 1) * 4 + i)
    }
  }
  quad(0, 1, 2, 3)
  const b = (rings.length - 1) * 4
  quad(b + 3, b + 2, b + 1, b + 0)
  return { V, F }
}

/** A long thin slab: the bar of a gantry or the tooth of a grille. */
function bar(len, thick, chamfer) {
  const m = chamferedBox(thick, thick, len, chamfer)
  return m
}

function buildPart(part) {
  if (part._mesh) return part._mesh
  if (part.kind === 'bar') part._mesh = bar(part.len, part.thick, part.thick * 0.45)
  else part._mesh = chamferedBox(part.w, part.t, part.d, part.c)
  return part._mesh
}

// Composition per state. These are different objects, not the same object at
// different speeds: `walk` is a receding corridor, `doomscroll` a grille the
// camera is stuck behind, `dream` one tall prism with a ring going round it.
const COMPOSITIONS = {
  idle: [
    { kind: 'box', w: 3.0, t: 0.62, d: 2.0, c: 0.42, pos: [0, 0, 0], warm: 0.35, cold: 0.55 },
    { kind: 'ring', r: 2.05, pos: [0, 0, 0], rot: [1.05, 0, 0], cold: 0.8, spin: 0.10 }
  ],
  work: [
    { kind: 'box', w: 1.9, t: 0.32, d: 1.3, c: 0.28, pos: [0, -0.42, 0], warm: 0.5, cold: 0.4 },
    { kind: 'bar', len: 3.4, thick: 0.14, pos: [0, 0.42, 0], rot: [0, 0, 0.22], warm: 0.9, cold: 0.2, spin: 0.05 },
    { kind: 'bar', len: 3.4, thick: 0.14, pos: [0, 0.42, 0], rot: [0, 0, -0.22], warm: 0.2, cold: 0.9, spin: -0.05 }
  ],
  walk: [
    { kind: 'box', w: 1.5, t: 0.5, d: 1.0, c: 0.26, pos: [0, 0, 1.6], warm: 0.5, cold: 0.3 },
    { kind: 'box', w: 1.9, t: 0.5, d: 1.2, c: 0.30, pos: [-1.5, -0.3, 0.2], warm: 0.3, cold: 0.6 },
    { kind: 'box', w: 2.3, t: 0.5, d: 1.4, c: 0.34, pos: [1.7, 0.25, -1.5], warm: 0.7, cold: 0.2 }
  ],
  daydream: [
    { kind: 'box', w: 1.9, t: 0.44, d: 1.3, c: 0.34, pos: [0, 0, 0], warm: 0.25, cold: 0.5 },
    { kind: 'ring', r: 2.2, pos: [0, 0, 0], rot: [1.4, 0.3, 0], cold: 0.9, spin: 0.14 },
    { kind: 'ring', r: 1.6, pos: [0, 0, 0], rot: [-0.9, 0.6, 0.4], warm: 0.8, spin: -0.2 }
  ],
  dream: [
    { kind: 'box', w: 0.78, t: 1.5, d: 0.78, c: 0.18, pos: [0, 0, 0], warm: 0.45, cold: 0.5 },
    { kind: 'ring', r: 1.62, pos: [0, 0.1, 0], rot: [1.35, 0, 0.15], cold: 0.95, spin: 0.06 }
  ],
  doomscroll: [
    { kind: 'bar', len: 5.4, thick: 0.22, pos: [0, 0.95, 0], warm: 0.7, cold: 0.2 },
    { kind: 'bar', len: 5.4, thick: 0.22, pos: [0, 0.35, 0.15], warm: 0.2, cold: 0.8 },
    { kind: 'bar', len: 5.4, thick: 0.22, pos: [0, -0.25, 0], warm: 0.3, cold: 0.6 },
    { kind: 'bar', len: 5.4, thick: 0.22, pos: [0, -0.85, 0.1], warm: 0.8, cold: 0.15 }
  ]
}

const CAMERA = { fov: 38, dist: 4.6, pitch: 0.30 }

/** Rotate, project, shade one frame of a composition into the field context. */
function drawScene(ctx, w, h, time, comp, spec, dark) {
  const yaw = time * (spec.speed || 0.1) * 0.55
  const pitch = CAMERA.pitch + Math.sin(time * 0.23) * 0.10
  const cf = Math.cos(yaw), sf = Math.sin(yaw)
  const cp = Math.cos(pitch), sp = Math.sin(pitch)
  const f = 1 / Math.tan((CAMERA.fov * Math.PI / 180) / 2)
  const aspect = w / h

  const project = (v) => {
    let x = v[0] * cf - v[2] * sf
    let z = v[0] * sf + v[2] * cf
    let y = v[1]
    const y2 = y * cp - z * sp
    const z2 = y * sp + z * cp
    z = z2 + CAMERA.dist
    y = y2
    const ndcX = (x * f / aspect) / z
    const ndcY = (y * f) / z
    return [(ndcX + 1) * w * 0.5, (1 - ndcY) * h * 0.5, z]
  }

  const spinOf = (part) => (part.spin ? time * part.spin : 0)
  const place = (v, part) => {
    const a = spinOf(part)
    const ca = Math.cos(a), sa = Math.sin(a)
    let x = v[0] * ca - v[2] * sa
    let z = v[0] * sa + v[2] * ca
    let y = v[1]
    const [rx, ry, rz] = part.rot || [0, 0, 0]
    // y, then x, then z — enough for the tilts these parts use
    const cy = Math.cos(ry), sy = Math.sin(ry)
    let x2 = x * cy + z * sy
    let z2 = -x * sy + z * cy
    const cx = Math.cos(rx), sx = Math.sin(rx)
    const y2 = y * cx - z2 * sx
    z2 = y * sx + z2 * cx
    if (rz) {
      const cz = Math.cos(rz), sz = Math.sin(rz)
      const x3 = x2 * cz - y2 * sz
      y = x2 * sz + y2 * cz
      x2 = x3
    } else {
      y = y2
    }
    const [px, py, pz] = part.pos || [0, 0, 0]
    return project([x2 + px, y + py, z2 + pz])
  }

  const Lkey = norm3(-0.55, 0.66, 0.52)
  const Lrim = norm3(0.62, -0.28, -0.74)
  const faces = []

  for (const part of comp) {
    if (part.kind === 'ring') continue
    const mesh = buildPart(part)
    const pts = mesh.V.map((v) => place(v, part))
    for (const tri of mesh.F) {
      const [a, b, c] = tri
      const p0 = pts[a], p1 = pts[b], p2 = pts[c]
      if (!p0 || !p1 || !p2) continue
      const area = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
      if (area >= 0) continue                       // back face
      faces.push({
        p0, p1, p2,
        z: (p0[2] + p1[2] + p2[2]) / 3,
        part,
        n: norm3(
          mesh.V[b][0] + mesh.V[c][0] - 2 * mesh.V[a][0],
          mesh.V[b][1] + mesh.V[c][1] - 2 * mesh.V[a][1],
          mesh.V[b][2] + mesh.V[c][2] - 2 * mesh.V[a][2]
        )
      })
    }
  }

  faces.sort((A, B) => B.z - A.z)

  for (const face of faces) {
    const n = face.n
    const spin = spinOf(face.part)
    const cs = Math.cos(spin), ss = Math.sin(spin)
    const nx0 = n[0] * cs - n[2] * ss
    const nz0 = n[0] * ss + n[2] * cs
    const nx = nx0 * cf - nz0 * sf
    const nz1 = nx0 * sf + nz0 * cf
    const ny = n[1] * cp - nz1 * sp
    const nz = n[1] * sp + nz1 * cp
    const kd = Math.max(0, nx * Lkey[0] + ny * Lkey[1] + nz * Lkey[2])
    const rd = Math.max(0, nx * Lrim[0] + ny * Lrim[1] + nz * Lrim[2])
    const warm = kd * (face.part.warm != null ? face.part.warm : 0.4) * (0.65 + (spec.head || 0) * 0.35)
    const cold = rd * (face.part.cold != null ? face.part.cold : 0.5)
    const base = 24
    const r = Math.min(235, base + warm * 170 + cold * 40)
    const g = Math.min(235, base + warm * 150 + cold * 140)
    const bl = Math.min(235, base + warm * 100 + cold * 150)
    ctx.fillStyle = `rgb(${r | 0},${g | 0},${bl | 0})`
    ctx.beginPath()
    ctx.moveTo(face.p0[0], face.p0[1])
    ctx.lineTo(face.p1[0], face.p1[1])
    ctx.lineTo(face.p2[0], face.p2[1])
    ctx.closePath()
    ctx.fill()
  }

  // Rings: a thin circle stroke, depth-faded, so they read as drawn rather than
  // cast. Cheap, and the only part that survives at very low resolution.
  ctx.lineWidth = Math.max(1, w / 720)
  for (const part of comp) {
    if (part.kind !== 'ring') continue
    const SEG = 96
    for (let i = 0; i < SEG; i++) {
      const a0 = (i / SEG) * Math.PI * 2
      const a1 = ((i + 1) / SEG) * Math.PI * 2
      const q = (a) => place([Math.cos(a) * part.r, Math.sin(a) * part.r * 0.38, Math.sin(a) * part.r * 0.62], part)
      const p0 = q(a0), p1 = q(a1)
      const near = Math.max(0, 1 - (p0[2] - 2.6) / 3.4)
      const warm = (part.warm || 0) * (0.4 + near * 0.9)
      const cold = (part.cold || 0) * (0.4 + near * 0.9)
      ctx.strokeStyle = dark
        ? `rgba(${126 + warm * 90 | 0},${205 - warm * 40 | 0},${196 - cold * 30 | 0},${(0.22 + near * 0.66).toFixed(3)})`
        : `rgba(${52 + warm * 60 | 0},${96 + warm * 40 | 0},${94 - cold * 10 | 0},${(0.22 + near * 0.66).toFixed(3)})`
      ctx.beginPath()
      ctx.moveTo(p0[0], p0[1])
      ctx.lineTo(p1[0], p1[1])
      ctx.stroke()
    }
  }
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

export function createArt(canvas, { dark = true, strength = 0.12, front = false } = {}) {
  const ctx = canvas.getContext('2d', { alpha: true })
  const field = canvas.ownerDocument.createElement('canvas')
  const sample = field.getContext('2d', { willReadFrequently: true })
  // Reading the field back at full size is enormous (SS^2 x pixels every frame);
  // draw it *down* into a cols x rows scratch canvas instead and read one pixel
  // per cell. The browser's downscale is the area average that sampling wanted.
  const bloom = canvas.ownerDocument.createElement('canvas')
  const blur = canvas.ownerDocument.createElement('canvas')

  // Ink is NOT the object's contrast control. The object carries its own tonal
  // range; this number only decides how present it is against the surface. Set
  // it too low and every face collapses into the same dim grey.
  const inkAlpha = front
    ? Math.min(0.55, Math.max(0.18, strength * 3.4))   // a wash over text
    : Math.min(0.95, Math.max(0.20, strength * 3.0))   // under the transcript

  // A document without canvas support (a headless mount, a policy-disabled
  // renderer) must leave a working layer with nothing in it, not throw.
  if (!ctx || !sample || typeof ctx.getImageData !== 'function') {
    return {
      resize() {}, render() {}, setScene() {},
      stats: () => ({ frames: 0, cols: 0, rows: 0, scene: 'idle', w: 0, h: 0, dpr: 1, mode: 'none' })
    }
  }
  const ink = inkFor(dark)
  const SS = 2                        // supersample: a 1px strand must survive
  let w = 1, h = 1, dpr = 1, cols = 1, rows = 1, scene = 'idle'
  let strands = [], t = 0, frames = 0

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

  // The pass chain — the transplantable part of three's postprocessing example.
  // Scene → buffer → blur pass → additive composite → quantise. EffectComposer
  // itself is three-only and unreachable from a plugin; the order of operations
  // is not, and it is the order that fixes the hard edge over text.
  function drawField(time) {
    if (field.width !== w * SS || field.height !== h * SS) {
      field.width = w * SS
      field.height = h * SS
      bloom.width = Math.max(2, (field.width / 4) | 0)
      bloom.height = Math.max(2, (field.height / 4) | 0)
      blur.width = bloom.width
      blur.height = bloom.height
    }
    sample.setTransform(1, 0, 0, 1, 0, 0)
    sample.clearRect(0, 0, field.width, field.height)
    sample.setTransform(SS, 0, 0, SS, 0, 0)
    sample.lineJoin = 'round'
    sample.lineCap = 'round'
    const comp = COMPOSITIONS[scene] || COMPOSITIONS.idle
    drawScene(sample, w, h, time, comp, spec(), dark)

    // Pass 1: the scene, at quarter resolution. The downscale is the threshold —
    // it keeps lit geometry and drops the near-black field to nothing.
    const bctx = bloom.getContext('2d')
    bctx.setTransform(1, 0, 0, 1, 0, 0)
    bctx.clearRect(0, 0, bloom.width, bloom.height)
    bctx.drawImage(field, 0, 0, bloom.width, bloom.height)

    // Pass 2: blur, twice at a radius scaled to the buffer, which is what turns
    // a rim into a gradient. Two passes beat one wide pass — same cost, less
    // banding, because the kernel composes as a tent.
    const kctx = blur.getContext('2d')
    kctx.clearRect(0, 0, blur.width, blur.height)
    kctx.filter = 'blur(4px)'
    kctx.drawImage(bloom, 0, 0)
    kctx.filter = 'none'
    bctx.clearRect(0, 0, bloom.width, bloom.height)
    bctx.filter = 'blur(4px)'
    bctx.drawImage(blur, 0, 0)
    bctx.filter = 'none'

    // Pass 3: additive composite over the sharp scene. Bright cells bleed into
    // their neighbours, so the silhouette ends in dust instead of a cut line.
    sample.setTransform(1, 0, 0, 1, 0, 0)
    sample.globalCompositeOperation = 'lighter'
    sample.globalAlpha = 0.85
    sample.drawImage(bloom, 0, 0, field.width, field.height)
    sample.globalAlpha = 1
    sample.globalCompositeOperation = 'source-over'
    sample.setTransform(SS, 0, 0, SS, 0, 0)
  }

  function render(dt) {
    t += dt
    drawField(t)
    // Post only. What goes to the screen is the processed buffer as an image:
    // no ramp, no glyph grid, no per-cell ink. The bloom gradient is the
    // picture, so opacity stops being a per-character decision and becomes one
    // number over a continuous tone — which is exactly what stops it reading as
    // characters stamped on top of text.
    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.imageSmoothingEnabled = true
    if ('imageSmoothingQuality' in ctx) ctx.imageSmoothingQuality = 'high'
    ctx.globalAlpha = inkAlpha
    ctx.drawImage(field, 0, 0, canvas.width, canvas.height)
    ctx.globalAlpha = 1
    frames++
  }

  return {
    resize, render, setScene,
    stats: () => ({ frames, cols, rows, scene, w, h, dpr, mode: 'image', ink: inkAlpha })
  }
}

/** The layer itself: one div, one pre, one version-stamped style element. */
export function createLayer(doc, win, { strength = LAYER.defaultStrength } = {}) {
  sweepStrays(doc)
  const surf = surface(doc, win)
  const placement = surf.opaque ? 'front' : 'behind'
  // Over text the layer is a wash, not a picture: the ceiling matters more than
  // the multiplier, because a single bright cell over a word is what reads as
  // damage. Front is therefore capped hard; behind has room.
  const strengthUsed = placement === 'front'
    ? Math.min(0.16, strength * 0.42)
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

  // A slot, not a canvas: either the 3D family (three + AsciiEffect) or the
  // Canvas2D strands fill it, and the layer does not care which.
  const art = doc.createElement('div')
  art.setAttribute(LAYER.attr, 'art')
  art.style.cssText = 'position:absolute;inset:0;overflow:hidden;'
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
    // Start on the 2D family so there is always something to draw, then hand
    // over to three if this document can give us a WebGL context.
    const canvas = doc.createElement('canvas')
    canvas.setAttribute(LAYER.attr, 'glyphs')
    canvas.setAttribute('aria-hidden', 'true')
    canvas.style.cssText = 'display:block;margin:0;padding:0;'
    handle.art.appendChild(canvas)
    const art = createArt(canvas, { dark: handle.dark, strength: handle.strength, front: handle.placement === 'front' })
    let scene3d = null
    let art3dError = null
    // Bounded diagnostics for the app's own devtools. Nothing here grows.
    const probe = (window.__antemuse = { frames: 0, glyphs: 0, errors: [], scene: null, mode: 'strands' })

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
      if (scene3d) {
        scene3d.render(dt, ts / 1000)
        probe.frames += 1
        const s3 = scene3d.stats()
        probe.threeFrames = s3.frames
        return
      }
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

    // NOTE: a runtime desktop plugin may only import @hermes/plugin-sdk and
    // react — the host rejects any other specifier ("unsupported import"). three
    // is therefore not importable here, vendored or not, and the 3D is done in
    // this file with plain projection maths instead. This block is kept as the
    // seam where a host-provided three would go.
    Promise.reject(new Error('3d runs in-file')).then((m) => {
      if (stopped) return
      try {
        scene3d = m.createScene3D({
          width: handle.layer.clientWidth || win.innerWidth || 960,
          height: handle.layer.clientHeight || win.innerHeight || 800,
          dark: handle.dark
        })
        handle.art.replaceChildren(scene3d.domElement)
        scene3d.render(0.016, 0)
        probe.mode = 'ascii3d'
      } catch (e) {
        art3dError = String((e && e.message) || e)
        probe.mode = 'strands'
        probe.errors = probe.errors.concat('3d: ' + art3dError).slice(-3)
      }
    }, () => { probe.mode = 'solid' })

    if (reducedMotion(win)) {
      // A still picture, not a frozen timer.
      art.render(0)
    } else {
      rafId = raf(tick)
    }
    poll()

    const onResize = () => {
      fit()
      if (scene3d) scene3d.resize(handle.layer.clientWidth || win.innerWidth, handle.layer.clientHeight || win.innerHeight)
      else art.render(0)
    }
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
      if (scene3d) { try { scene3d.dispose() } catch (e) { /* gone */ } }
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
    // The picture is NOT over the chat. A dock pane has its own surface, so the
    // art stops competing with the transcript for contrast; the fixed-overlay
    // machinery is kept for hosts that expose a real chat backdrop, but it is
    // not mounted by default.
    ctx.register({
      id: 'pane',
      area: PANES_AREA,
      title: copy.pane,
      data: { placement: 'right', collapsible: true, width: '420px', minWidth: '320px', maxWidth: '560px' },
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
    // Settings are NOT a bespoke page: the host renders this plugin's manifest
    // `config_schema` as a form under Settings ▸ Plugins and saves it to
    // plugins.entries.antemuse.settings. Registering our own page here would shadow
    // that form with a second, divergent copy of the same controls.

  }
}
