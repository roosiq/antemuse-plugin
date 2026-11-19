// Antemuse desktop plugin: state pane and concept cockpit.

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
// A run of misses before the pane says so: three polls, under three seconds. Short enough that a
// real outage is named almost at once, long enough that a gateway restart does not blank a state.
const MISSES_BEFORE_ERROR = 3

// A monospace glyph cell is about 0.6 advances wide by one line tall. Both the
// requested grid and the font that fills it come from these two numbers, so the
// art ends up exactly the size of the box instead of a thumbnail inside it.
const CELL_W = 0.6
const CELL_H = 1.0
const PROBE_FONT = 10

const copy = {
  pane: 'Antemuse',
  cockpit: 'Cockpit',
  cockpitOpen: 'Open concept cockpit',
  state: 'State',
  idle: 'nothing running',
  // The empty pane is a dead end without this: a person who opens it and finds a dark map has
  // nothing to act on. One command, not five — the label above this line already says there is
  // no state, so the note says how to get one.
  start: '/walk to start',
  // Written into the corner the moment a poll fails after a run of failures. Deliberately not
  // "backend unavailable": the backend did answer, it refused, and saying which is the whole
  // difference between looking at the plugin and looking at your session.
  reconnecting: 'reconnecting',
  unavailable: 'plugin unavailable',
  unreachable: 'the plugin is not loaded',
  signin: 'sign-in required',
  silent: 'the plugin went quiet',
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
/* A state has no clock, so the pane has none to format: the dose is the count. */

function doseLeft(active) {
  const dose = Number(active.dose || 0)
  const served = Number(active.served || 0)
  return Math.max(0, dose - served)
}

/** One line of counts under the frame — no prose, no adjectives. */
export function counts(payload) {
  const active = payload && payload.active
  if (!active) return ''
  const bits = [
    // the dose in the state's own unit (hops, pairs, items, recombinations), not "turns".
    // There is no clock: a state ends when its dose lands, so the count is the whole story.
    // An open-ended state (`/explore`) has no dose at all and says so rather than promising
    // "0 picks to go" on arrival, which reads as already finished.
    Number(active.dose || 0) > 0
      ? `${doseLeft(active)} ${active.unit || 'turn(s)'} to go`
      : `${Number(active.served || 0)} picked · you end it`
  ]
  const tools = active.tools || {}
  if (tools.mode === 'none') bits.push('no tools')
  else if (tools.mode === 'some') bits.push(`${tools.allowed.length} tool${tools.allowed.length === 1 ? '' : 's'}`)
  else bits.push('all tools')
  if (payload.residue && payload.residue.count) bits.push(`${payload.residue.count} carried`)
  return bits.join(' · ')
}

/** The ambient readout: the one fact a person should learn without opening anything.
 *
 * The status bar is occupied by a chip that used to carry a label and nothing else — a state
 * could be half spent and the corner still read "walking". A dose is the thing that changes, so
 * the dose is what the chip shows: `4/6 hops`, `0 picked` for an open-ended state, and nothing
 * at all when there is no state to describe (an empty chip is not a claim).
 */
export function chip(payload) {
  const active = payload && payload.active
  if (!active) return ''
  const dose = Number(active.dose || 0)
  const served = Math.max(0, Number(active.served || 0))
  if (!Number.isFinite(served) || !Number.isFinite(dose)) return ''
  if (!dose) return served ? `${served} picked` : ''
  return `${Math.min(served, dose)}/${dose} ${active.unit || 'turn(s)'}`
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
  // What an idle pane is actually looking at. "no state" alone left the corner saying nothing
  // about a map that was still drawing the last state's firings, and nothing about how to start
  // one; the note answers whichever of those applies.
  const last = (payload && payload.last) || null
  // A flight is work, and the pane that took it is the one place a person can see it landed.
  // The cockpit says nothing after it closes, so this is the receipt: what was flown, and how
  // much of it they kept.
  const flight = (payload && payload.flight) || null
  return {
    situation: situation(payload, error),
    // One honest string, not a category plus a footnote: the label is what a person reads at
    // 11px in a corner, and "backend unavailable" for an expired session sends them looking at
    // the server instead of at their sign-in. Before the first answer there is nothing to name —
    // the pane used to print "no state" for a question it had not asked yet.
    label: error ? whyFailed(error) : active ? String(active.label || '') : (payload ? copy.idle : ''),
    note: error || active
      ? ''
      : flight && flight.concepts
        ? `last flight \u00b7 ${flight.concepts} ${flight.concepts === 1 ? 'concept' : 'concepts'}` +
          (flight.kept && flight.kept.length ? ` \u00b7 kept ${flight.kept.length}` : '')
        : (last && last.state ? `${last.state} ended \u00b7 /walk again` : copy.start),
    // A count is a claim about now. Under a failed poll it is a claim about the last time the
    // pane could see, printed beside an error — the screenshot that says "the backend did not
    // answer · 1:31 left" is the pane contradicting itself. Nothing is counted when the answer
    // is missing.
    clock: '',
    counts: error ? '' : counts(payload),
    contract: active && !error ? String(active.contract || '') : '',
    lines: Array.isArray(frame.lines) ? frame.lines : [],
    residue: (payload && payload.residue && payload.residue.count) || 0
  }
}

// ---------------------------------------------------------------- the surface

function useStatePayload(ctx, cells) {
  const [payload, setPayload] = useState(null)
  const [error, setError] = useState(null)
  // One failed poll is not a broken backend. The gateway drops a request while it is restarting,
  // and the pane used to answer that single miss by throwing away the words and the counts of a
  // state that was still running — so a 3-second hiccup replaced a live walk with "the backend
  // did not answer". The error is only surfaced after a run of misses, and one answer clears it.
  const misses = useRef(0)
  // The grid is part of the request, so a resize must re-ask rather than stretch
  // an old frame: the server renders at the size it is told.
  const query = cells ? `?cols=${cells.cols}&rows=${cells.rows}&fit=cover` : ''
  useEffect(() => {
    let alive = true
    const read = () => {
      ctx.rest('/state' + query).then(
        (data) => {
          if (!alive) return
          misses.current = 0
          setPayload(data)
          setError(null)
        },
        (err) => {
          if (!alive) return
          misses.current += 1
          if (misses.current >= MISSES_BEFORE_ERROR) setError(String((err && err.message) || err || 'unreachable'))
        }
      )
    }
    read()
    const stop = ctx.setInterval(read, POLL_MS)
    return () => {
      alive = false
      if (typeof stop === 'function') stop()
    }
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

  // Size is how much has been said about a concept; colour is whether it is firing now. Two
  // questions, two channels: a dot you keep returning to stays big while quiet, and a dot that
  // fires without history glows instead of shouting.
  const VS_POINT = 'attribute vec3 aPos; attribute float aW; attribute float aV;' +
    'uniform mat4 uMVP; uniform float uDpr; uniform float uSize; varying float vW;' +
    'void main(){ vec4 p = uMVP * vec4(aPos,1.0); gl_Position = p;' +
    // The distance term is bounded: at the wide shot the old falloff crushed every dot to a
    // pixel or two, so volume had nothing to show itself in. Perspective still applies, but a dot
    // stays a dot.
    'gl_PointSize = (2.2 + 6.5*aV) * (1.0 + 0.7*aW) * uDpr * uSize * (9.0 / max(2.5, p.w));' +
    'vW = aW; }'
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
  const pPos = loc(pointProg, 'aPos'), pW = loc(pointProg, 'aW'), pV = loc(pointProg, 'aV')
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
  let nodes = [], nodePos = new Float32Array(0), nodeW = new Float32Array(0),
    nodeV = new Float32Array(0), edges = []
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
        // Strength first: at the wide view the picture shows the web's spine, not every strand.
        // 700 of 2,400 was the difference between a texture and a structure in the ink count.
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
    nodeV = new Float32Array(nodes.length)
    nodes.forEach((n, i) => {
      const live = raw.length === nodes.length ? raw[i] : null
      const w = live && live.w ? live.w : n.w
      n.w = w
      nodeW[i] = w
      const v = live && live.v !== undefined ? live.v : (n.v || 0)
      n.v = v
      nodeV[i] = Math.max(0, Math.min(1, v))
    })
    gl.bindBuffer(gl.ARRAY_BUFFER, pointBuf)
    gl.bufferData(gl.ARRAY_BUFFER, nodePos, gl.STATIC_DRAW)
    const wBuf = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, wBuf)
    gl.bufferData(gl.ARRAY_BUFFER, nodeW, gl.STATIC_DRAW)
    upload.wBuf = wBuf
    const vBuf = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, vBuf)
    gl.bufferData(gl.ARRAY_BUFFER, nodeV, gl.STATIC_DRAW)
    upload.vBuf = vBuf
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
  //
  // `trim` cuts a fraction off each end, so the ink stops short of the node instead of landing on
  // it. (Partial edge drawing — stubs at the ends — was the first attempt and made this worse:
  // it piles ink exactly where the dots are. Here the ends are the things being erased.)
  // `fade` dims a segment with its distance from the camera, so near structure reads first.
  const segQuads = (posArr, alphaArr, flatA, widthPx, MVP, trim, fade, cullPx) => {
    const n = posArr.length / 6
    const W = canvas.width, H = canvas.height
    const px = new Float32Array(n * 24), pa = new Float32Array(n * 12)
    let k = 0, ka = 0
    const put = (x0, y0, x1, y1, a) => {
      const dx = x1 - x0, dy = y1 - y0
      const len = Math.hypot(dx, dy)
      if (len < 0.35) return
      // A segment longer than this is a streak across the pane, not a readable relation: it
      // crosses everything and lands nowhere useful. Short segments are the local structure.
      const hw = Math.max(0.55, widthPx * 0.5)
      if (cullPx && len > cullPx) { segQuads.culled++; return }
      // Ink laid down, in square pixels of stroke: the number that says whether the web is
      // burying the dots, independent of how a screenshot happens to be classified.
      segQuads.ink += (len - (trim ? len * Math.min(0.42, trim) * 2 : 0)) * hw * 2
      const nx = (-dy / len) * hw, ny = (dx / len) * hw
      const v = [x0 + nx, y0 + ny, x0 - nx, y0 - ny, x1 + nx, y1 + ny,
                 x0 - nx, y0 - ny, x1 - nx, y1 - ny, x1 + nx, y1 + ny]
      for (let j = 0; j < 12; j += 2) {
        px[k++] = ((v[j] / W) * 2) - 1
        px[k++] = 1 - ((v[j + 1] / H) * 2)
      }
      for (let j = 0; j < 6; j++) pa[ka++] = a
    }
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
      let a = alphaArr ? alphaArr[i * 2] : flatA
      if (fade) {
        const depth = (cwA + cwB) * 0.5
        a *= Math.max(0.28, Math.min(1, 1.55 - depth * 0.42))
      }
      if (!trim || trim <= 0) { put(x0, y0, x1, y1, a); continue }
      const f = Math.min(0.42, trim)
      put(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f,
          x1 + (x0 - x1) * f, y1 + (y0 - y1) * f, a)
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
    // Edges are quads, not lines: a hairline is not a relation you can see. The web is drawn
    // trimmed, so no edge lands on a node, and only its strongest part is drawn at all — a full
    // 2,400-edge web is a picture of the web, not of the concepts. Zooming in restores untrimmed
    // edges and the full strength set for what you are looking at.
    segQuads.ink = 0; segQuads.culled = 0
    const trim = dist < 1.55 ? 0 : 0.10
    const cull = dist < 1.55 ? 520 : 210
    // The colour uniform belongs to the quad program, and the program bound at this point is
    // still the POINTS one from the previous frame — so every frame set a uniform the bound
    // program did not own, nine times per poll, in the console of every app that ran the pane.
    // Bind the program before speaking to it.
    if (quadProg) gl.useProgram(quadProg)
    if (quadProg && edgePos.length) {
      gl.uniform3f(qColor, 0.58, 0.62, 0.80)
      segQuads(edgePos, null, 0.22, 1.25 * dpr, MVP, trim, true, cull * dpr)
    }
    // Connections carrying activation, then the trail on top of them. These stay whole: they are
    // the answer, not the texture.
    if (quadProg && livePos.length) {
      gl.uniform3f(qColor, 1.0, 0.66, 0.34)
      segQuads(livePos, liveA, 0.3, 1.9 * dpr, MVP, 0, true)
    }
    if (quadProg && pathPos.length) {
      gl.uniform3f(qColor, 1.0, 0.80, 0.42)
      segQuads(pathPos, pathA, 0.8, 2.4 * dpr, MVP, 0, false)
    }
    gl.useProgram(pointProg)
    gl.uniformMatrix4fv(pMVP, false, MVP)
    gl.uniform1f(pDpr, win.devicePixelRatio || 1)
    // Never hidden behind an edge: a picture whose dots cannot be found has failed at the one
    // thing it is for.
    gl.uniform1f(pSize, 1.35)
    gl.depthMask(false)
    gl.bindBuffer(gl.ARRAY_BUFFER, pointBuf)
    gl.enableVertexAttribArray(pPos); gl.vertexAttribPointer(pPos, 3, gl.FLOAT, false, 0, 0)
    gl.bindBuffer(gl.ARRAY_BUFFER, upload.wBuf || pointBuf)
    gl.enableVertexAttribArray(pW); gl.vertexAttribPointer(pW, 1, gl.FLOAT, false, 0, 0)
    gl.bindBuffer(gl.ARRAY_BUFFER, upload.vBuf || pointBuf)
    gl.enableVertexAttribArray(pV); gl.vertexAttribPointer(pV, 1, gl.FLOAT, false, 0, 0)
    gl.drawArrays(gl.POINTS, 0, nodePos.length / 3)
    gl.depthMask(true)
    frames++
    placeLabels(MVP)
    report({ frames, yaw: +yaw.toFixed(3), pitch: +pitch.toFixed(3), dist: +dist.toFixed(3),
      hover: hovered, pinned, labels: placeLabels.k || 0, litN: placeLabels.lit || 0,
      liveN: upload.liveN || 0, linksN: upload.linkN || 0,
      ink: Math.round(segQuads.ink || 0), culled: segQuads.culled || 0 })
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
  // The picture is a live view, so the poll should follow the state rather than a fixed beat.
  // At four seconds a walk that lands a hop a second arrived as one jump and then stillness —
  // the same reading as a frozen pane. A second apart while a state runs, four when idle.
  let pollDelay = 350
  // One request at a time. At a second apart, a poll that takes four seconds would otherwise
  // stack three builds on the gateway and each would be slower than the one before — the pane
  // asking for a picture faster than one can be drawn is how a timeout storm starts.
  let inFlight = false
  const pull = () => {
    if (stopped || inFlight || typeof ctx.rest !== 'function') return
    inFlight = true
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
      inFlight = false
      if (stopped) return
      // A live state serves one unit per delivery call, so polling fast is what makes each
      // hop its own frame. There is no clock in the dose to race.
      pollDelay = (seed && seed.active) ? 350 : 4000
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
      inFlight = false
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
  let timer = null
  const schedule = () => {
    if (stopped) return
    const at = typeof ctx.setTimeout === 'function' ? ctx.setTimeout : win.setTimeout.bind(win)
    timer = at(() => { pull(); schedule() }, pollDelay)
  }
  schedule()
  rafId = win.requestAnimationFrame ? win.requestAnimationFrame(loop) : win.setTimeout(() => loop(Date.now()), 16)

  return {
    dispose: () => {
      stopped = true
      try { if (win.cancelAnimationFrame) win.cancelAnimationFrame(rafId); else win.clearTimeout(rafId) } catch (e) {}
      try { if (typeof ctx.clearTimeout === 'function' && timer !== null) ctx.clearTimeout(timer); else if (timer !== null) win.clearTimeout(timer) } catch (e) {}
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
        // No module URL to derive from (a bundled module): say so with an empty list. A hardcoded
        // home directory here was a leg that could only ever work on the author's machine.
        return []
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

/** Reach a route: the router is `host.navigate`, never `ctx`. Hash is the last resort. */
function goto(ctx, path) {
  // `host.navigate` is the SDK's router; `ctx` never carried one.
  if (host && typeof host.navigate === 'function') { host.navigate(path); return }
  if (ctx && typeof ctx.navigate === 'function') { ctx.navigate(path); return }
  try {
    if (typeof location !== 'undefined') location.hash = `#${path}`
  } catch (e) { /* no window: nothing to route */ }
}

function StateView({ ctx, onOpenCockpit }) {
  const { ref, cells } = useCells()
  const { payload, error } = useStatePayload(ctx, cells)
  const vm = viewModel(payload, error)
  const frame = (payload && payload.frame) || {}
  // `/explore` is a state with a surface, and the surface is another pane. A state whose
  // whole point is the cockpit is useless if the person has to find it in the nav first.
  const exploring = Boolean(payload && payload.active && payload.active.key === 'explore')

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
          // Behind a running state these words are furniture and stay faint. With nothing
          // running — or nothing answering — they are the only thing on the pane, so they have
          // to be readable: an empty pane that whispers "no state" is indistinguishable from a
          // pane that failed to load.
          opacity: vm.situation === 'active' ? 0.5 : 0.78,
          pointerEvents: 'none', display: 'flex', flexDirection: 'column', gap: '2px',
          color: 'var(--ui-text-secondary, inherit)'
        },
        children: [
          // The label is the instrument's readout line: tracked, uppercase, and
          // first, the way the site sets its own navigation.
          jsx('div', { style: { ...LABEL, opacity: 0.95 }, children: vm.label }),
          vm.note ? jsx('div', { style: { ...DATA, opacity: 0.8 }, children: vm.note }) : null,
          vm.counts ? jsx('div', { style: { ...DATA, color: 'var(--ui-text-secondary, inherit)' }, children: vm.counts }) : null,
          vm.contract ? jsx('div', { style: { ...DATA, color: 'var(--ui-text-secondary, inherit)' }, children: vm.contract }) : null
        ]
      }),
      exploring
        ? jsx('button', {
            type: 'button',
            // Flip the tab in place; the host may have no router call at all.
            onClick: () => { if (onOpenCockpit) onOpenCockpit(); else goto(ctx, `/${ID}/cockpit`) },
            style: {
              position: 'absolute', left: 12, bottom: 66, zIndex: 2,
              background: 'transparent',
              border: '1px solid var(--ui-stroke-secondary, currentColor)',
              borderRadius: '2px', padding: '4px 9px', cursor: 'pointer',
              color: 'var(--ui-accent, currentColor)',
              font: `600 10px ${FONT.label}`, letterSpacing: '0.14em', textTransform: 'uppercase'
            },
            children: 'open the cockpit'
          })
        : null
    ]
  })
}

// A status chip: one glance, no prose. Present whether or not the pane is open.
function StateChip({ ctx }) {
  const { payload, error } = useStatePayload(ctx)
  const vm = viewModel(payload, error)
  // A count is a claim about now. Under a failed poll it would describe the last time the pane
  // could see, printed next to an error — the pane contradicting itself.
  const dose = error ? '' : chip(payload)
  const label = [vm.label, dose].filter(Boolean).join(' · ')
  // While exploring, the chip is the way into the map rather than into settings: the state
  // exists to be flown, and this is the one control on screen at all times.
  const exploring = Boolean(payload && payload.active && payload.active.key === 'explore')
  return jsx('button', {
    type: 'button',
    title: exploring ? 'open the concept cockpit' : label,
    onClick: () => {
      goto(ctx, exploring ? `/${ID}/cockpit` : pluginSettingsHref(ID))
    },
    style: {
      background: 'transparent',
      border: 0,
      padding: '0 6px',
      cursor: 'pointer',
      font: `600 10px ${FONT.label}`,
      letterSpacing: '0.16em',
      textTransform: 'uppercase',
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

// `bare` is "nothing fired yet"; a state missing here drew `idle` — how unstuck vanished.
const SCENES = {
  bare:       { strands: 0, speed: 0.0,   width: 0.0, head: 0.0 },
  idle:       { strands: 3, speed: 0.085, width: 2.4, head: 0.0 },
  work:       { strands: 6, speed: 0.330, width: 2.2, head: 0.0 },
  walk:       { strands: 4, speed: 0.240, width: 2.6, head: 0.9 },
  daydream:   { strands: 5, speed: 0.150, width: 2.4, head: 0.5 },
  dream:      { strands: 5, speed: 0.115, width: 2.8, head: 1.0 },
  unstuck:    { strands: 2, speed: 0.190, width: 2.9, head: 0.6 }
}

// Which picture a state asks for — one rule, assertable: idle | work | bare | its field.
// Feed text is untrusted and never persisted, so doomscroll has no field even after serving:
// the strip carries the count, the canvas stays empty.
const NO_FIELD = new Set(['doomscroll'])

// A finished state keeps its picture for two polls (the residue's count), so a one-dose state
// is visible at all.
export function holdScene(held, active, busy) {
  if (active && active.key) return { scene: sceneFor(active, busy), held: { key: active.key, polls: 0 } }
  if (held && held.polls < 2) return { scene: sceneFor({ key: held.key, served: 1 }, busy), held: { key: held.key, polls: held.polls + 1 } }
  return { scene: sceneFor(active, busy), held: null }
}

export function sceneFor(active, busy) {
  const key = active && active.key ? String(active.key) : ''
  if (!key) return busy ? 'work' : 'idle'
  if (NO_FIELD.has(key)) return 'bare'
  const served = Number((active && active.served) || 0)
  if (served <= 0) return 'bare'
  return SCENES[key] && SCENES[key].strands > 0 ? key : 'idle'
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

// Composition per state: different objects, not one object at different speeds.
const COMPOSITIONS = {
  // Nothing fired is an answer, not a missing value: hence ?? below.
  bare: [],
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
    const comp = COMPOSITIONS[scene] ?? COMPOSITIONS.idle
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

  // A slot, not a canvas: the 3D family or the Canvas2D strands fill it.
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
    let held = null
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
          const step = holdScene(held, payload && payload.active, busy)
          held = step.held
          art.setScene(step.scene)
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
    // The 3D kit is unreachable by design: a runtime plugin may only import the SDK and
    // react, so this file's own projection draws. `scene3d` stays null for the day a host
    // exposes a renderer; the branch that used to sit here could never run (it hung off a
    // rejected promise) and only looked live.
    probe.mode = 'strands'

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

// ---------------------------------------------------------------- the cockpit
//
// One first-person view of the same `/graph` payload.

// ---------------------------------------------------------------- brand
// Theme colours are resolved from the host; tube-only literals are neutral.
const THEME_VARS = {
  // Ground tracks the host background across arbitrary themes.
  ground: ['--ui-background', '--background', '--ui-panel-background', '--sidebar'],
  glass: ['--ui-panel-background', '--ui-background', '--background', '--sidebar'],
  text: ['--ui-text', '--foreground', '--color-foreground', '--ui-text-secondary'],
  dim: ['--ui-text-secondary', '--muted-foreground', '--color-muted-foreground', '--ui-text'],
  stroke: ['--ui-stroke-secondary', '--ui-stroke', '--border', '--color-border'],
  accent: ['--ui-accent', '--color-primary', '--primary'],
  ink: ['--ui-panel-background', '--ui-background', '--background', '--sidebar']
}

// Instrument type: monospace for readouts and labels, one weight each. The app's
// own faces stay on the DOM panels, which inherit them.
const FONT = {
  display: '700 1em ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace',
  label: '600 1em ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace',
  data: '500 1em ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace'
}

// Panel chrome for the cockpit's DOM, in the app's own variables so the panes
// match the rest of the desktop instead of sitting on their own surface.
const PANEL = {
  background: 'var(--ui-panel-background, var(--background, rgba(0, 0, 0, 0.72)))',
  border: '1px solid var(--ui-stroke-secondary, var(--border, rgba(255, 255, 255, 0.14)))',
  borderRadius: '2px',
  color: 'var(--ui-text, var(--foreground, inherit))'
}
const LABEL = {
  font: `600 9px/1.7 ${FONT.label}`,
  letterSpacing: '0.22em',
  textTransform: 'uppercase',
  color: 'var(--ui-text-secondary, var(--muted-foreground, var(--color-muted-foreground, inherit)))',
  opacity: 0.85
}
const DATA = {
  font: `500 11px/1.55 ${FONT.data}`,
  fontVariantNumeric: 'tabular-nums',
  color: 'var(--ui-text, var(--foreground, inherit))'
}

const COCKPIT_POLL_MS = 4000
const COCKPIT_MEET = 0.16        // world units: close enough to count as met
const COCKPIT_GLASS_FRACTION = 0.15
// Asteroids, not a sniper rifle: hold the trigger and a stream of shots walks
// across the field. Bullets are objects with a position and a life, so a shot
// can miss, and a miss is visible.
const FIRE_INTERVAL = 0.16       // seconds between shots while held
const BULLET_SPEED = 0.45        // world units per second: the cloud is ~1 unit
                                 // across, so a bullet at 1.0 crossed the glass in
                                 // a couple of frames and was never seen
const BULLET_LIFE = 3.2          // seconds before a shot is spent
const BULLET_R = 0.055           // world-unit hit radius
const CONVERGE = 1.4             // world units where both barrels agree on the aim
const MUZZLE_REACH = 0.12        // world units from the eye to the muzzle: the cloud
                                 // is only about a unit across, so a long reach would
                                 // start every shot inside a neighbour and swallow it
const GUN_X = 92                 // px each cannon sits off the centreline
const GUN_LEN = 30               // px of barrel above the dash
const GUN_KICK = 0.09           // seconds of recoil after a shot
const MAX_BULLETS = 64
// The edge of the navigable map: the cloud lives inside about one unit, and the
// boundary is drawn here and used as the soft stop in the flight model, so what
// you see is what turns you around.
const MAP_RADIUS = 1.9

/** Screen-space scale for the ship's furniture and the shot marks.
 *
 *  Everything here was sized for a 1280px pane. A maximised window is 2140px,
 *  where a 4px dot is a speck and a 92px cannon offset is a rounding error, so
 *  the instruments and the shots scale with the glass. */
const uiScale = (glassWidth) => Math.max(1, Math.min(2.4, glassWidth / 1280))

function cockpitTheme(el, doc, win) {
  // Resolve CSS variables through a probe.
  const SENTINEL = 'rgb(1, 1, 1)'
  let probe = null
  if (typeof doc !== 'undefined' && doc.body) {
    probe = doc.createElement('span')
    probe.style.cssText = 'position:absolute;left:-9999px;top:0;width:0;height:0;pointer-events:none'
    doc.body.appendChild(probe)
  }
  const read = (names) => {
    if (!probe || !win.getComputedStyle) return ''
    for (const name of names) {
      probe.style.color = `var(${name}, ${SENTINEL})`
      const v = win.getComputedStyle(probe).color
      if (v && v.trim() && v.trim() !== SENTINEL) return v.trim()
    }
    return ''
  }
  const text = read(THEME_VARS.text) || '#ffffff'
  const glass = read(THEME_VARS.glass) || '#000000'
  const ground = read(THEME_VARS.ground)
  const stroke = read(THEME_VARS.stroke)
  const accent = read(THEME_VARS.accent)
  const ink = read(THEME_VARS.ink)
  if (probe && probe.parentNode) probe.parentNode.removeChild(probe)
  return {
    // Background, not theme-name sniffing: preserves the app's light/dark ground.
    ground: ground || glass,
    glass: glass,
    ink: ink || glass,
    text: text,
    phosphor: text,
    paper: text,
    dim: withAlpha(text, 0.6),
    stroke: stroke || withAlpha(text, 0.35),
    accent: accent || text,
    // the tube is physical: its raster and its falloff are black, not themed
    tubeClear: 'rgba(0, 0, 0, 0)',
    tubeEdge: 'rgba(0, 0, 0, 0.5)',
    frameEdge: withAlpha(text, 0.12)
  }
}

/** Any CSS colour → rgba() at an alpha. The theme hands us hex or rgb(); canvas
 *  wants a concrete string, and appending "55" to a var() would be a guess. */
function withAlpha(color, a) {
  const c = String(color || '').trim()
  let r = 235, g = 235, b = 235
  const hex = c.match(/^#([0-9a-f]{3,8})$/i)
  if (hex) {
    const h = hex[1]
    if (h.length === 3 || h.length === 4) {
      r = parseInt(h[0] + h[0], 16); g = parseInt(h[1] + h[1], 16); b = parseInt(h[2] + h[2], 16)
    } else if (h.length >= 6) {
      r = parseInt(h.slice(0, 2), 16); g = parseInt(h.slice(2, 4), 16); b = parseInt(h.slice(4, 6), 16)
    }
  } else {
    const rgb = c.match(/-?[\d.]+/g)
    if (rgb && rgb.length >= 3) {
      r = Math.round(parseFloat(rgb[0])); g = Math.round(parseFloat(rgb[1])); b = Math.round(parseFloat(rgb[2]))
    }
  }
  return `rgba(${r}, ${g}, ${b}, ${a})`
}

/**
 * Mount the cockpit on a canvas. Returns a handle with `destroy()` and
 * `stats()` so the pane can verify itself and a harness can drive it without
 * React.
 */
function createCockpit({ ctx, el, callbacks }) {
  const doc = el.ownerDocument
  const win = doc.defaultView
  const c2d = el.getContext('2d')
  const onCatch = callbacks && callbacks.onCatch ? callbacks.onCatch : () => {}
  const onTarget = callbacks && callbacks.onTarget ? callbacks.onTarget : () => {}
  const onPicks = callbacks && callbacks.onPicks ? callbacks.onPicks : () => {}
  // A counter alone cannot say what the person acted on. These names are an
  // interaction readout for the pane; a failed verdict route must never affect flight.
  const onName = callbacks && callbacks.onName ? callbacks.onName : () => {}
  const onExit = callbacks && callbacks.onExit ? callbacks.onExit : () => {}
  const onTouchFirst = callbacks && callbacks.onTouchFirst ? callbacks.onTouchFirst : () => {}
  let lastNamed = ''
  const nameNode = (node, source) => {
    if (!node || !node.l) return
    const label = String(node.l)
    const key = `${source}:${label}`
    if ((source !== 'hit' && key === lastNamed) || (source === 'target' && lastNamed === `hit:${label}`)) return
    lastNamed = key
    onName(label, source)
  }

  // /explore's only material, filed rather than dying here. Only the delta goes over: the
  // whole cumulative list would multiply-count the same concept.
  const posted = Object.create(null)
  let pickTimer = 0
  function flushPicks() {
    const batch = []
    for (const label of Object.keys(state.hits)) {
      const n = state.hits[label]
      for (let i = posted[label] || 0; i < n; i++) batch.push(label)
      posted[label] = n
    }
    if (!batch.length) return
    try {
      // Same rule as a verdict: the packaged app cannot reach the gateway with a
      // relative fetch from a file:// origin, so the host's REST door posts it.
      // A pick is the owner's choice, so it travels named; an unnamed one is refused.
      const sid = host && host.state && host.state.focusedSessionId
      const payload = { picks: batch, session: String((sid && sid.get ? sid.get() : sid) || '') }
      if (ctx && typeof ctx.rest === 'function') {
        Promise.resolve(ctx.rest('/picks', { method: 'POST', body: payload })).catch(() => {})
      } else if (typeof win.fetch === 'function') {
        win.fetch(`/api/plugins/${ID}/picks`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(payload)
        }).catch(() => {})
      }
    } catch (e) { /* a pick that cannot be filed is not worth breaking the flight */ }
  }
  function queuePicks() {
    if (pickTimer) return
    pickTimer = win.setTimeout(() => { pickTimer = 0; flushPicks() }, 500)
  }

  const theme = cockpitTheme(el, doc, win)
  const reduced = (() => {
    try { return Boolean(win.matchMedia && win.matchMedia('(prefers-reduced-motion: reduce)').matches) }
    catch (e) { return false }
  })()

  const state = {
    nodes: [],            // { l, w, v, x, y, z } in unit space
    path: [],
    links: [],
    lit: 0,
    key: '',
    payloadAt: 0,
    error: '',
    cam: { x: 0, y: 0, z: 0, yaw: 0, pitch: 0, roll: 0, speed: 0, vx: 0, vy: 0, vz: 0 },
    target: null,
    catchList: [],
    // Shooting picks concepts: every hit adds interest, and interest is what
    // orders the pick list. A concept hit five times is wanted five times.
    hits: Object.create(null),
    bullets: [],
    bursts: [],
    firing: false,
    cool: 0,
    kick: { l: 0, r: 0 },
    barrel: 1,
    shotsFired: 0,
    net: { active: false, t: 0, landed: false, reach: 1.25 },
    frames: 0
  }
  const view = { w: 1, h: 1, cx: 0, cy: 0, f: 400, dpr: 1 }
  const home = { x: 0, y: 0, z: 0 }

  // dust gives the empty sky a scale; wrapped around the ship so it never runs out
  const DUST = 200
  const DUST_BOX = 6
  const dust = []
  for (let i = 0; i < DUST; i++) {
    const r = (n) => {
      const s = Math.sin(i * 12.9898 + n * 78.233) * 43758.5453
      return s - Math.floor(s)
    }
    dust.push([r(1) * DUST_BOX * 2 - DUST_BOX, r(2) * DUST_BOX * 2 - DUST_BOX, r(3) * DUST_BOX * 2 - DUST_BOX])
  }

  // ---------------- geometry ----------------
  const basis = () => {
    const cy = Math.cos(state.cam.yaw), sy = Math.sin(state.cam.yaw)
    const cp = Math.cos(state.cam.pitch), sp = Math.sin(state.cam.pitch)
    const cr = Math.cos(state.cam.roll), sr = Math.sin(state.cam.roll)
    // level right/up, then banked around the forward axis: roll is what makes
    // a turn read as flying rather than as panning a camera
    const rx = cy, ry = 0, rz = -sy
    const ux = -sy * sp, uy = cp, uz = -cy * sp
    return {
      fwd: [sy * cp, sp, cy * cp],
      right: [rx * cr + ux * sr, ry * cr + uy * sr, rz * cr + uz * sr],
      up: [ux * cr - rx * sr, uy * cr - ry * sr, uz * cr - rz * sr]
    }
  }

  const toCam = (p, b) => {
    const dx = p.x - state.cam.x, dy = p.y - state.cam.y, dz = p.z - state.cam.z
    return {
      x: dx * b.right[0] + dy * b.right[1] + dz * b.right[2],
      y: dx * b.up[0] + dy * b.up[1] + dz * b.up[2],
      z: dx * b.fwd[0] + dy * b.fwd[1] + dz * b.fwd[2]
    }
  }

  const project = (c) => ({
    x: view.cx + (view.f * c.x) / c.z,
    y: view.cy - (view.f * c.y) / c.z,
    scale: view.f / c.z
  })

  // ---------------- payload ----------------
  const normalize = (raw) => {
    if (!Array.isArray(raw)) throw new Error('invalid graph payload: nodes must be an array')
    const rows = raw.filter((n) => n && typeof n.l === 'string'
      && Number.isFinite(n.x) && Number.isFinite(n.y) && Number.isFinite(n.z))
    if (!rows.length) return { nodes: [], home: { x: 0, y: 0, z: 0 } }
    let cx = 0, cy = 0, cz = 0
    for (const n of rows) { cx += n.x; cy += n.y; cz += n.z }
    cx /= rows.length; cy /= rows.length; cz /= rows.length
    // Scale by a robust radius, not the furthest node. One outlier pins the
    // scale and collapses the entire cloud into a speck around the origin, which
    // is exactly what an empty-looking cockpit turned out to be.
    const dists = rows.map((n) => Math.hypot(n.x - cx, n.y - cy, n.z - cz)).sort((a, b) => a - b)
    const radius = Math.max(1e-6, dists[Math.floor(dists.length * 0.9)] || dists[dists.length - 1] || 1)
    const clip = (v) => Math.max(-1.25, Math.min(1.25, v))
    const nodes = rows.map((n) => ({
      l: n.l,
      w: Math.max(0, Math.min(1, Number(n.w) || 0)),
      v: Math.max(0, Math.min(1, Number(n.v) || 0)),
      x: clip((n.x - cx) / radius),
      y: clip((n.y - cy) / radius),
      z: clip((n.z - cz) / radius)
    }))
    // The busiest knot, so a session starts inside the structure rather than in
    // the empty shell a projection always has at its edge.
    let best = nodes[0], bestScore = -1
    const MID = 0.22
    for (const n of nodes) {
      let near = 0
      for (const m of nodes) if (m !== n && Math.hypot(m.x - n.x, m.y - n.y, m.z - n.z) < MID) near++
      const score = near + n.w * 2
      if (score > bestScore) { bestScore = score; best = n }
    }
    return { nodes, home: { x: best.x, y: best.y, z: best.z } }
  }

  const apply = (payload) => {
    const first = !state.nodes.length
    const norm = normalize(payload && payload.nodes)
    state.nodes = norm.nodes
    state.path = Array.isArray(payload && payload.path) ? payload.path.slice(0, 64) : []
    state.links = Array.isArray(payload && payload.links) ? payload.links.slice(0, 600) : []
    state.lit = Number(payload && payload.lit) || 0
    state.key = String((payload && payload.key) || '')
    state.payloadAt = Date.now()
    state.error = ''
    home.x = norm.home.x; home.y = norm.home.y; home.z = norm.home.z
    if (first) {
      state.cam.x = home.x; state.cam.y = home.y; state.cam.z = home.z
      state.cam.yaw = 0; state.cam.pitch = 0; state.cam.speed = 0
    }
    draw()
  }

  const poll = () => {
    const reportError = (err) => {
      state.error = String((err && err.message) || err || 'unreachable')
      draw()
    }
    const session = (() => {
      try {
        const atom = host && host.state && host.state.focusedSessionId
        return atom && atom.get ? atom.get() : null
      } catch (e) { return null }
    })()
    const q = '/graph?limit=1400' + (session ? '&session=' + encodeURIComponent(session) : '')
    try {
      Promise.resolve(ctx.rest(q)).then((payload) => { apply(payload) }).catch(reportError)
    } catch (e) {
      reportError(e)
    }
  }

  // ---------------- rendering ----------------
  const alpha = (a) => { c2d.globalAlpha = Math.max(0, Math.min(1, a)) }
  const REDUCED_LIFE = 380

  // A deterministic grain tile, built once: scattered ink specks, not noise that
  // boils between frames. Printed, not televised.
  let grainTile = null
  function drawGrain(w, h) {
    if (!grainTile) {
      const size = 96
      const tile = doc.createElement('canvas')
      tile.width = size; tile.height = size
      const g = tile.getContext('2d')
      let seed = 0x9e3779b9
      const rnd = () => {
        seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5
        return ((seed >>> 0) % 10000) / 10000
      }
      g.fillStyle = theme.phosphor
      for (let i = 0; i < 900; i++) {
        const x = rnd() * size, y = rnd() * size
        const a = 0.04 + rnd() * 0.10
        g.globalAlpha = a
        g.fillRect(x, y, 1, rnd() > 0.85 ? 2 : 1)
      }
      g.globalAlpha = 1
      // the raster itself: one dark line every third row, the arcade tell
      g.fillStyle = '#000000'   // the raster is the tube, not the theme
      g.globalAlpha = 0.08
      for (let y = 0; y < size; y += 3) g.fillRect(0, y, size, 1)
      g.globalAlpha = 1
      grainTile = tile
    }
    const pat = c2d.createPattern(grainTile, 'repeat')
    if (!pat) return
    c2d.save()
    c2d.globalAlpha = 0.5
    c2d.fillStyle = pat
    c2d.fillRect(0, 0, w, h)
    c2d.restore()
  }

  function fit() {
    const host = el.parentElement || el
    const w = host.clientWidth || el.clientWidth || 640
    const h = host.clientHeight || el.clientHeight || 420
    view.dpr = Math.min(win.devicePixelRatio || 1, 2)
    view.w = w
    view.h = h
    // Width/height ATTRIBUTES, not just CSS: the pane is resized constantly by
    // sash drags and a CSS-only size is a blurred stretch.
    el.width = Math.max(1, Math.round(w * view.dpr))
    el.height = Math.max(1, Math.round(h * view.dpr))
    c2d.setTransform(view.dpr, 0, 0, view.dpr, 0, 0)
    view.cx = w / 2
    view.cy = h * 0.46
    view.f = Math.min(w, h) * 0.92
  }

  const dashTop = () => view.h - Math.max(74, view.h * COCKPIT_GLASS_FRACTION)

  /** The tube: darkened corners and a hairline inner edge. A CRT is never a
   *  rectangle of flat light — the beam falls off at the rim. */
  function drawTube(w, h) {
    const g = c2d.createRadialGradient(
      w / 2, h / 2, Math.min(w, h) * 0.35,
      w / 2, h / 2, Math.hypot(w, h) * 0.62
    )
    g.addColorStop(0, theme.tubeClear)
    g.addColorStop(1, theme.tubeEdge)
    c2d.save()
    c2d.fillStyle = g
    c2d.fillRect(0, 0, w, h)
    c2d.strokeStyle = theme.frameEdge
    c2d.lineWidth = 1
    c2d.strokeRect(0.5, 0.5, w - 1, h - 1)
    c2d.restore()
  }

  function draw() {
    if (!view.w) fit()
    const b = basis()
    const w = view.w, h = view.h
    c2d.setTransform(view.dpr, 0, 0, view.dpr, 0, 0)
    c2d.clearRect(0, 0, w, h)

    // A tube, not a brand surface. Flat green-black ground, phosphor speckle,
    // and scanlines: the beam is a raster and it shows.
    c2d.save()
    // Host background under the tube keeps a light app light; chrome still uses panel glass.
    c2d.fillStyle = theme.ground
    c2d.fillRect(0, 0, w, h)
    drawGrain(w, h)
    c2d.restore()

    // The horizon has to bank with the ship: a level line under a rolled view
    // is the one cue that betrays a panning camera dressed as a cockpit.
    const horizon = view.cy + view.f * Math.tan(state.cam.pitch) * 0.55
    c2d.save()
    c2d.translate(view.cx, horizon)
    c2d.rotate(-state.cam.roll)
    c2d.strokeStyle = theme.stroke
    alpha(0.35)
    c2d.lineWidth = 1
    const span = Math.hypot(w, h) * 1.2
    c2d.beginPath(); c2d.moveTo(-span, 0); c2d.lineTo(span, 0); c2d.stroke()
    c2d.restore()

    // dust
    c2d.save()
    c2d.fillStyle = theme.dim
    for (const d of dust) {
      const wrap = (v, p) => p + ((((v - p) % (DUST_BOX * 2)) + DUST_BOX * 3) % (DUST_BOX * 2)) - DUST_BOX
      const p = { x: wrap(d[0], state.cam.x), y: wrap(d[1], state.cam.y), z: wrap(d[2], state.cam.z) }
      const c = toCam(p, b)
      if (c.z < 0.2 || c.z > 8) continue
      const s = project(c)
      if (s.x < 0 || s.y < 0 || s.x > w || s.y > h) continue
      alpha(Math.max(0.04, 0.34 - c.z / 22))
      c2d.fillRect(s.x, s.y, 1.3, 1.3)
    }
    c2d.restore()

    // the walked trail, in the order it was walked
    if (state.path.length > 1) {
      const byLabel = new Map(state.nodes.map((n) => [n.l, n]))
      c2d.save()
      c2d.strokeStyle = theme.accent
      c2d.lineWidth = 1.4
      alpha(0.5)
      c2d.beginPath()
      let started = false
      for (const label of state.path) {
        const n = byLabel.get(label)
        if (!n) continue
        const c = toCam(n, b)
        if (c.z < 0.05) { started = false; continue }
        const s = project(c)
        if (!started) { c2d.moveTo(s.x, s.y); started = true } else c2d.lineTo(s.x, s.y)
      }
      c2d.stroke()
      c2d.restore()
    }

    // nodes, clipped to the glass so nothing labels itself behind the dash
    c2d.save()
    c2d.beginPath(); c2d.rect(0, 0, w, Math.max(1, dashTop() - 4)); c2d.clip()
    const drawn = []
    for (const n of state.nodes) {
      const c = toCam(n, b)
      if (c.z < 0.04) continue
      const s = project(c)
      if (s.x < -60 || s.y < -60 || s.x > w + 60 || s.y > h + 60) continue
      drawn.push({ n, s, dist: Math.hypot(c.x, c.y, c.z), r: Math.max(1.1, Math.min(14, 0.0055 * s.scale * (0.7 + n.v * 0.9))) })
    }
    drawn.sort((a, z) => z.dist - a.dist)
    const caught = new Set(state.catchList.map((n) => n.l))
    let labels = 0
    for (const d of drawn) {
      const lit = d.n.w > 0.05
      const isCaught = caught.has(d.n.l)
      const isTarget = state.target === d.n.l
      const a = Math.max(0.16, Math.min(1, 1.2 - d.dist / 3.2))
      // Ink marks, not lamps. A firing concept is a filled rule; a cold one is
      // a hairline ring. No shadow blur: glow is a screen, and this surface is
      // meant to be printed.
      c2d.save()
      if (lit || isCaught || isTarget) {
        alpha(isCaught || isTarget ? 1 : a)
        c2d.fillStyle = theme.phosphor
        c2d.beginPath(); c2d.arc(d.s.x, d.s.y, Math.max(1.6, d.r), 0, Math.PI * 2); c2d.fill()
        c2d.strokeStyle = theme.phosphor
        c2d.lineWidth = 1
        alpha(0.55)
        c2d.beginPath(); c2d.arc(d.s.x, d.s.y, Math.max(1.6, d.r) + 3.5, 0, Math.PI * 2); c2d.stroke()
      } else {
        alpha(a * 0.45)
        c2d.strokeStyle = theme.phosphor
        c2d.lineWidth = 1
        c2d.beginPath(); c2d.arc(d.s.x, d.s.y, Math.max(1.2, d.r * 0.8), 0, Math.PI * 2); c2d.stroke()
      }
      c2d.restore()

      if (isTarget) {
        c2d.save()
        c2d.strokeStyle = theme.phosphor
        c2d.lineWidth = 1.5
        alpha(0.95)
        const r = d.r + 7
        for (const [sx, sy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
          c2d.beginPath()
          c2d.moveTo(d.s.x + sx * r, d.s.y + sy * r - sy * 5)
          c2d.lineTo(d.s.x + sx * r, d.s.y + sy * r)
          c2d.lineTo(d.s.x + sx * r - sx * 5, d.s.y + sy * r)
          c2d.stroke()
        }
        c2d.restore()
      }

      const hits = state.hits[d.n.l] || 0
      if (hits) {
        // interest is drawn on the concept: a ring plus one pip per hit
        c2d.save()
        c2d.strokeStyle = theme.accent
        alpha(0.9)
        c2d.lineWidth = 1.2
        // pips sit outside the target brackets so interest is not hidden by them
        const rr = d.r + 11
        c2d.beginPath(); c2d.arc(d.s.x, d.s.y, rr, 0, Math.PI * 2); c2d.stroke()
        const pips = Math.min(6, hits)
        for (let i = 0; i < pips; i++) {
          const a = -Math.PI / 2 + (i - (pips - 1) / 2) * 0.30
          c2d.beginPath()
          c2d.arc(d.s.x + Math.cos(a) * rr, d.s.y + Math.sin(a) * rr, 2.3, 0, Math.PI * 2)
          c2d.fillStyle = theme.accent
          c2d.fill()
        }
        if (hits > 1) {
          c2d.font = `600 10px ${FONT.data}`
          c2d.fillStyle = theme.accent
          c2d.fillText(`x${hits}`, d.s.x + rr + 4, d.s.y - rr + 2)
        }
        c2d.restore()
      }

      if ((d.dist < 0.34 && labels < 40) || isTarget || isCaught || hits) {
        labels += 1
        c2d.save()
        alpha(isTarget || isCaught ? 0.95 : Math.min(0.75, a))
        c2d.fillStyle = isTarget || isCaught ? theme.text : theme.dim
        c2d.font = `${isTarget ? 600 : 400} 11px ${FONT.data}`
        // A label that runs off the glass is a bug, not a style: flip it to the
        // other side of the point, and drop it if it will not fit either way.
        const lw = c2d.measureText(d.n.l).width
        const edge = Math.max(16, w * 0.045)
        let lx = d.s.x + d.r + 6
        if (lx + lw > w - edge) lx = d.s.x - d.r - 6 - lw
        if (lx >= edge && lx + lw <= w - edge) c2d.fillText(d.n.l, lx, d.s.y + 3.5)
        c2d.restore()
      }
    }
    c2d.restore()

    drawMapEdge(b)
    drawBullets(b)
    drawNet(b)
    drawChrome(b, hdg())
    drawNotes()
    drawTube(w, h)
  }

  const hdg = () => ((state.cam.yaw * 180 / Math.PI) % 360 + 360) % 360

  /**
   * The edge of the map.
   *
   * The concept cloud is a place with a boundary, but from the seat it had none:
   * fly far enough and the last concept slides behind you into featureless glass
   * with nothing to say whether you had left the map or whether it had emptied.
   * This draws that boundary as a ring on the cloud's own plane, with ticks every
   * thirty degrees, brightening as you approach it.
   */
  function drawMapEdge(b) {
    // drawn a touch inside the soft stop, so the boundary stays a thing you can
    // see from outside rather than a shell you are pinned against
    const R = MAP_RADIUS * 0.9
    const camDist = Math.hypot(state.cam.x, state.cam.y, state.cam.z)
    // only speak up near the boundary: at the centre this is background texture
    const near = Math.max(0, Math.min(1, (camDist - R * 0.55) / (R * 0.45)))
    const base = 0.16 + near * 0.42
    const SEG = 96
    c2d.save()
    c2d.lineCap = 'butt'

    // A survey grid on the cloud's floor, inside the boundary. From the seat this
    // is what says "there is a place here": without it the edge ring floats in
    // nothing and the glass has no ground at all.
    const ringAt = (r, a) => {
      c2d.beginPath()
      let prev = null
      for (let i = 0; i <= SEG; i++) {
        const th = (i / SEG) * Math.PI * 2
        const p = { x: Math.cos(th) * r, y: 0, z: Math.sin(th) * r }
        const c = toCam(p, b)
        if (c.z > 0.05) {
          const s = project(c)
          if (prev) c2d.lineTo(s.x, s.y)
          else c2d.moveTo(s.x, s.y)
          prev = s
        } else prev = null
      }
      // theme.stroke is already a translucent mix: multiplying alpha onto it
      // vanishes on this ground. The grid is painted in text at low opacity.
      c2d.strokeStyle = theme.text
      alpha(a)
      c2d.lineWidth = 1
      c2d.stroke()
    }
    const onPlane = Math.abs(state.cam.y) < R * 0.45
    if (onPlane) {
      ringAt(R * 0.34, 0.1 + near * 0.16)
      ringAt(R * 0.67, 0.14 + near * 0.18)
    }
    c2d.beginPath()
    for (let i = 0; onPlane && i < 12; i++) {
      const th = (i / 12) * Math.PI * 2
      let prev = null
      for (let j = 0; j <= 24; j++) {
        const r = (j / 24) * R
        const p = { x: Math.cos(th) * r, y: 0, z: Math.sin(th) * r }
        const c = toCam(p, b)
        if (c.z > 0.05) {
          const s = project(c)
          if (prev) c2d.lineTo(s.x, s.y)
          else c2d.moveTo(s.x, s.y)
          prev = s
        } else prev = null
      }
    }
    c2d.strokeStyle = theme.text
    alpha(0.09 + near * 0.13)
    c2d.lineWidth = 1
    c2d.stroke()

    // The boundary is a sphere, not a ring on the floor: from below the plane, or
    // nose-up at the edge, a single flat circle is invisible exactly when you need
    // it. Three great circles always put the limit somewhere on the glass.
    c2d.strokeStyle = near > 0.65 ? theme.accent : theme.text
    c2d.lineWidth = 1.4 + near * 0.8
    alpha(0.45 + near * 0.4)
    const planes = [
      (a) => ({ x: Math.cos(a) * R, y: Math.sin(a) * R, z: 0 }),
      (a) => ({ x: Math.cos(a) * R, y: 0, z: Math.sin(a) * R }),
      (a) => ({ x: 0, y: Math.cos(a) * R, z: Math.sin(a) * R })
    ]
    for (const ofPlane of planes) {
      c2d.beginPath()
      let prev = null
      for (let i = 0; i <= SEG; i++) {
        const a = (i / SEG) * Math.PI * 2
        const c = toCam(ofPlane(a), b)
        if (c.z > 0.05) {
          const s = project(c)
          if (prev) c2d.lineTo(s.x, s.y)
          else c2d.moveTo(s.x, s.y)
          prev = s
        } else prev = null
      }
      c2d.stroke()
    }

    // ticks: a bare circle reads as a lens flare; ticks read as a surveyed edge
    c2d.strokeStyle = near > 0.65 ? theme.accent : theme.text
    alpha(0.42 + near * 0.35)
    c2d.lineWidth = 1.3
    c2d.beginPath()
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2
      const foot = { x: Math.cos(a) * R, y: 0, z: Math.sin(a) * R }
      const head = { x: Math.cos(a) * R, y: 0.14, z: Math.sin(a) * R }
      const cf = toCam(foot, b)
      const ch = toCam(head, b)
      if (cf.z <= 0.05 || ch.z <= 0.05) continue
      const f = project(cf)
      const h = project(ch)
      c2d.moveTo(f.x, f.y)
      c2d.lineTo(h.x, h.y)
    }
    c2d.stroke()

    // and say it once, on the boundary nearest the nose
    if (near > 0.5) {
      const a = state.cam.yaw
      const p = { x: Math.cos(a) * R, y: 0, z: Math.sin(a) * R }
      const c = toCam(p, b)
      if (c.z > 0.2) {
        const s = project(c)
        if (s.x > 20 && s.x < view.w - 20 && s.y > 20 && s.y < dashTop()) {
          c2d.fillStyle = theme.accent
          alpha(Math.min(0.9, near))
          c2d.font = `600 ${Math.round(9 * uiScale(view.w))}px ${FONT.label}`
          tracked('0.18em')
          const label = 'edge'
          const lw = c2d.measureText(label).width
          c2d.fillText(label, s.x - lw / 2, s.y - 6 * uiScale(view.w))
        }
      }
    }
    c2d.restore()

    // At the wall, nose out, the boundary is behind you: the only honest cue left is on the
    // glass. It appears when the number is small enough to mean anything, so a person who
    // holds the stick in is told why nothing is happening.
    if (near > 0.85) {
      const px = Math.max(11, Math.min(16, Math.round(view.w / 140)))
      const y = view.cy - Math.max(28, view.h * 0.055)
      c2d.save()
      c2d.textAlign = 'center'
      c2d.fillStyle = theme.accent
      alpha(0.9)
      c2d.font = `700 ${px}px ${FONT.label}`
      tracked('0.34em')
      c2d.fillText('EDGE', view.cx, y)
      c2d.strokeStyle = theme.accent
      alpha(0.45)
      c2d.lineWidth = 1
      const half = Math.max(30, view.w * 0.035)
      c2d.beginPath()
      c2d.moveTo(view.cx - half, y + px * 0.75)
      c2d.lineTo(view.cx - half * 0.32, y + px * 0.75)
      c2d.moveTo(view.cx + half * 0.32, y + px * 0.75)
      c2d.lineTo(view.cx + half, y + px * 0.75)
      c2d.stroke()
      c2d.restore()
    }
  }

  /** Two cannons on the dash. A shot has to leave something the eye can see,
   *  or the stream reads as appearing out of the air.
   *
   *  Each is a solid barrel, canted outward, with a dark bore and a bright rim —
   *  silhouette first, because a pair of hairlines reads as a gauge stand. */
  function drawCannons() {
    c2d.save()
    c2d.lineJoin = 'miter'
    for (const side of [-1, 1]) {
      const g = gunScreen(side)
      const ui = uiScale(view.w)
      const base = dashTop() + 4
      const halfW = 10 * ui
      const cant = side * 22 * ui    // barrels splay hard outward: nose guns, not posts
      const tipY = g.y
      c2d.beginPath()
      c2d.moveTo(g.x - halfW, base)
      c2d.lineTo(g.x - halfW * 0.72 + cant, tipY)
      c2d.lineTo(g.x + halfW * 0.72 + cant, tipY)
      c2d.lineTo(g.x + halfW, base)
      c2d.closePath()
      c2d.fillStyle = theme.ink
      alpha(0.98)
      c2d.fill()
      c2d.strokeStyle = theme.text
      alpha(0.8)
      c2d.lineWidth = 1.6
      c2d.stroke()

      // the bore: a dark mouth with a bright lip, so the muzzle faces you
      const mx = g.x + cant
      const kick = state.kick[side < 0 ? 'l' : 'r'] / GUN_KICK
      if (kick > 0.55) {
        // a short flash for the first frames after a shot: the cannon is firing
        c2d.save()
        c2d.fillStyle = theme.text
        alpha(0.85 * kick)
        c2d.beginPath()
        c2d.arc(mx, tipY - 2 * ui, (4 + 5 * kick) * ui, 0, Math.PI * 2)
        c2d.fill()
        c2d.restore()
      }
      c2d.beginPath()
      c2d.ellipse(mx, tipY, halfW * 0.5, 3.1 * ui, 0, 0, Math.PI * 2)
      c2d.fillStyle = theme.glass
      alpha(1)
      c2d.fill()
      c2d.strokeStyle = theme.text
      alpha(0.9)
      c2d.lineWidth = 1.3
      c2d.stroke()

      // a mount plate tying it to the dash
      c2d.beginPath()
      c2d.moveTo(g.x - halfW - 4, base)
      c2d.lineTo(g.x + halfW + 4, base)
      c2d.strokeStyle = theme.stroke
      alpha(0.5)
      c2d.lineWidth = 1
      c2d.stroke()
    }
    c2d.restore()
  }

  function drawBullets(b) {
    if (!state.bullets.length && !state.bursts.length) return
    c2d.save()
    c2d.lineCap = 'round'
    const ui = uiScale(view.w)
    for (const shot of state.bullets) {
      const c = toCam(shot, b)
      if (c.z <= 0.05) continue
      const s = project(c)
      // Asteroids: a dot. No tail — the movement is the effect. On a phosphor
      // tube a bright dot blooms, so the glow is the medium, not decoration.
      c2d.save()
      c2d.shadowColor = theme.phosphor
      c2d.shadowBlur = 10
      c2d.fillStyle = theme.phosphor
      alpha(0.98)
      c2d.beginPath(); c2d.arc(s.x, s.y, 4 * ui, 0, Math.PI * 2); c2d.fill()
      c2d.restore()
    }
    for (const burst of state.bursts) {
      const c = toCam(burst, b)
      if (c.z <= 0.05) continue
      const s = project(c)
      const k = 1 - burst.t / 0.34
      c2d.strokeStyle = theme.accent
      c2d.lineWidth = 1.5 * ui
      alpha(0.9 * k)
      c2d.beginPath(); c2d.arc(s.x, s.y, (4 + (1 - k) * 12) * ui, 0, Math.PI * 2); c2d.stroke()
    }
    c2d.restore()
  }



  function drawNet(b) {
    if (!state.net.active) return
    const reach = state.net.landed ? state.net.reach : 0.5 + state.net.t * (state.net.reach - 0.5)
    const apex = { x: state.cam.x + b.fwd[0] * reach, y: state.cam.y + b.fwd[1] * reach, z: state.cam.z + b.fwd[2] * reach }
    const c = toCam(apex, b)
    if (c.z <= 0.05) return
    const s = project(c)
    const r = Math.max(8, 0.05 * s.scale)
    c2d.save()
    c2d.strokeStyle = theme.accent
    alpha(state.net.landed ? 0.9 : 0.7)
    c2d.lineWidth = state.net.landed ? 1.8 : 1.2
    if (!state.net.landed) c2d.setLineDash([5, 6])
    c2d.beginPath(); c2d.arc(s.x, s.y, r, 0, Math.PI * 2); c2d.stroke()
    c2d.setLineDash([])
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2 + (reduced ? 0 : state.net.t * 2)
      c2d.beginPath()
      c2d.moveTo(s.x + Math.cos(a) * r * 0.28, s.y + Math.sin(a) * r * 0.28)
      c2d.lineTo(s.x + Math.cos(a) * r, s.y + Math.sin(a) * r)
      c2d.stroke()
    }
    c2d.restore()
  }

  /** Canvas has letterSpacing in Chromium; setting an unknown property is inert. */
  const tracked = (spacing) => { try { c2d.letterSpacing = spacing } catch (e) { /* older canvas */ } }

  function drawChrome(b, heading) {
    const w = view.w, h = view.h
    const panel = theme.ink
    // canopy: the arch and two pillars, so the view has a frame it sits inside
    c2d.save()
    c2d.fillStyle = panel
    alpha(0.72)
    const arch = Math.max(26, h * 0.09)
    c2d.beginPath()
    c2d.moveTo(0, 0); c2d.lineTo(w, 0); c2d.lineTo(w, arch * 0.5)
    c2d.quadraticCurveTo(w * 0.5, arch, 0, arch * 0.5)
    c2d.closePath(); c2d.fill()
    const pillar = Math.max(14, w * 0.028)
    c2d.fillRect(0, 0, pillar, h)
    c2d.fillRect(w - pillar, 0, pillar, h)
    // dash
    const top = dashTop()
    c2d.beginPath()
    c2d.moveTo(0, top + 14)
    c2d.quadraticCurveTo(w * 0.5, top - 18, w, top + 14)
    c2d.lineTo(w, h); c2d.lineTo(0, h); c2d.closePath()
    alpha(0.96)
    c2d.fill()
    c2d.restore()

    // Frame edges as line work as well as fill: a panel colour close to the
    // surface would otherwise make the canopy invisible, and the cockpit
    // metaphor is the whole point of this surface.
    c2d.save()
    c2d.strokeStyle = theme.stroke
    alpha(0.55)
    c2d.lineWidth = 1
    c2d.beginPath()
    c2d.moveTo(0, arch * 0.52)
    c2d.quadraticCurveTo(w * 0.5, arch * 1.02, w, arch * 0.52)
    c2d.stroke()
    c2d.beginPath()
    c2d.moveTo(0, top + 14)
    c2d.quadraticCurveTo(w * 0.5, top - 18, w, top + 14)
    c2d.stroke()
    c2d.restore()

    // Wordmark: the mark and the name, small and quiet, the way the site sets
    // its own navigation. It is the only place the display face appears.
    c2d.save()
    c2d.textBaseline = 'alphabetic'
    c2d.textAlign = 'left'
    c2d.fillStyle = theme.text
    alpha(0.92)
    // String.fromCodePoint keeps the mark explicit without a literal glyph in
    // the source: PSI is the mark, and an escape survives every re-encode.
    const PSI = String.fromCodePoint(0x3A8)
    c2d.textAlign = 'left'
    c2d.font = `400 ${Math.max(15, Math.min(21, h * 0.031))}px ${FONT.display}`
    c2d.fillStyle = theme.text
    alpha(0.95)
    c2d.fillText(PSI, 18, arch0(arch) + 5)
    const markW = c2d.measureText(PSI + ' ').width
    // Cabinet marquee: caps, wide tracking. A vector display drew clean strokes,
    // so the type stays crisp — retro is the tube, not a coarse raster.
    const nameSize = Math.max(13, Math.min(18, h * 0.027))
    c2d.font = `700 ${nameSize}px ${FONT.display}`
    tracked('0.2em')
    c2d.fillText('ANTEMUSE', 18 + markW + 4, arch0(arch) + 5)
    const nameW = c2d.measureText('ANTEMUSE').width
    tracked('0.26em')
    c2d.font = `600 ${Math.max(8, Math.min(9, h * 0.013))}px ${FONT.label}`
    alpha(0.7)
    c2d.textAlign = 'right'
    c2d.fillStyle = theme.dim
    c2d.fillText('CONCEPT COCKPIT', w - 18, arch0(arch) + 2)
    // the plate rule: one hairline under the masthead, the way a chart is titled
    c2d.strokeStyle = theme.phosphor
    alpha(0.32)
    c2d.lineWidth = 1
    c2d.beginPath()
    c2d.moveTo(18, arch0(arch) + 9)
    c2d.lineTo(18 + markW + nameW + 12, arch0(arch) + 9)
    c2d.stroke()
    tracked('0')
    c2d.restore()

    // Corner ticks: four hairlines, the frame the site puts around its stage.
    c2d.save()
    c2d.strokeStyle = theme.stroke
    alpha(0.42)
    c2d.lineWidth = 1
    const tick = Math.max(10, Math.min(18, w * 0.016))
    const inset = 7
    for (const [x, y, dx, dy] of [[inset, inset, 1, 1], [w - inset, inset, -1, 1], [inset, h - inset, 1, -1], [w - inset, h - inset, -1, -1]]) {
      c2d.beginPath()
      c2d.moveTo(x, y + dy * tick); c2d.lineTo(x, y); c2d.lineTo(x + dx * tick, y)
      c2d.stroke()
    }
    c2d.restore()

    drawCannons()

    // reticle
    c2d.save()
    c2d.strokeStyle = theme.text
    alpha(0.6)
    c2d.lineWidth = 1
    const r = 14, g = 5
    c2d.beginPath()
    for (const [sx, sy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
      c2d.moveTo(view.cx + sx * r, view.cy + sy * r - sy * g)
      c2d.lineTo(view.cx + sx * r, view.cy + sy * r)
      c2d.lineTo(view.cx + sx * r - sx * g, view.cy + sy * r)
    }
    c2d.stroke()
    c2d.restore()

    // heading tape
    const tapeW = Math.min(w * 0.6, 420)
    const tapeY = Math.max(h * 0.1, arch0(arch) + 16)
    c2d.save()
    c2d.beginPath(); c2d.rect(view.cx - tapeW / 2, tapeY - 13, tapeW, 26); c2d.clip()
    c2d.textAlign = 'center'
    c2d.fillStyle = theme.dim
    c2d.strokeStyle = theme.stroke
    for (let d = -60; d <= 60; d += 5) {
      const deg = Math.round((heading + d) / 5) * 5
      const x = view.cx + (deg - heading) * (tapeW / 120)
      const major = deg % 30 === 0
      alpha(major ? 0.7 : 0.28)
      c2d.beginPath(); c2d.moveTo(x, tapeY + 7); c2d.lineTo(x, tapeY + (major ? -1 : 3)); c2d.stroke()
      if (major) {
        const label = String(((deg % 360) + 360) % 360).padStart(3, '0')
        // a half-cut number reads as a broken instrument, so it is not drawn
        const half = (tapeW / 2) - 20
        if (Math.abs(x - view.cx) <= half) {
          c2d.font = `500 11px ${FONT.data}`
          tracked('0.08em')
          c2d.fillText(label, x, tapeY - 5)
        }
      }
    }
    c2d.restore()
    c2d.save()
    c2d.strokeStyle = theme.accent
    alpha(0.95)
    tracked('0')
    c2d.beginPath(); c2d.moveTo(view.cx, tapeY + 7); c2d.lineTo(view.cx, tapeY - 5); c2d.stroke()
    c2d.restore()

    // readouts
    let nearest = null, nd = Infinity
    for (const n of state.nodes) {
      const d = Math.hypot(n.x - state.cam.x, n.y - state.cam.y, n.z - state.cam.z)
      if (d < nd) { nd = d; nearest = n }
    }
    if (state.target) nameNode({ l: state.target }, 'target')
    else if (nearest) nameNode(nearest, 'nearest')
    const airspeed = Math.hypot(state.cam.vx, state.cam.vy, state.cam.vz)
    const cells = [
      ['HDG', String(Math.round(heading)).padStart(3, '0')],
      ['PITCH', `${(state.cam.pitch * 180 / Math.PI).toFixed(0)}°`],
      ['ROLL', `${(state.cam.roll * 180 / Math.PI).toFixed(0)}°`],
      ['SPD', airspeed.toFixed(2)],
      ['NEAR', nearest ? nearest.l : '—'],
      ['PICK', String(pickList().length)],
      // How much map is left between the nose and the edge: the boundary is a
      // sphere you have to turn around to see, so it also has to be a number.
      ['EDGE', (() => {
        const d = MAP_RADIUS - Math.hypot(state.cam.x, state.cam.y, state.cam.z)
        return d >= 0 ? d.toFixed(2) : '-' + Math.abs(d).toFixed(2)
      })()],
      ['LIT', `${state.lit}/${state.nodes.length}`]
    ]
    const cellW = Math.min(150, (w - 60) / cells.length)
    const x0 = view.cx - (cellW * cells.length) / 2 + cellW / 2
    const y0 = h - Math.max(30, h * 0.045)
    c2d.save()
    c2d.textAlign = 'center'
    cells.forEach(([k, v], i) => {
      const x = x0 + i * cellW
      // Amber is interest, not decoration: only the pick and firing counts earn
      // it. Numbers that describe the ship stay phosphor.
      const hot = k === 'PICK' || k === 'FIRING' ||
        (k === 'EDGE' && parseFloat(String(v)) < 0.25)
      const maxW = cellW - 10
      c2d.textAlign = 'left'
      // The HUD is read at a glance from a sofa, not a desk: 9px labels were legible on a
      // laptop pane and unreadable full-screen, so the type scales with the glass.
      const labelPx = Math.max(10, Math.min(13, Math.round(w / 150)))
      c2d.fillStyle = theme.dim
      c2d.font = `600 ${labelPx}px ${FONT.label}`
      tracked('0.24em')
      alpha(0.85)
      c2d.fillText(k, x, y0 - labelPx + 3)
      c2d.font = `600 ${Math.max(13, Math.min(18, Math.round(w / 105)))}px ${FONT.data}`
      tracked('0.02em')
      // never let a readout run into its neighbour: trim, then draw
      let text = String(v)
      while (text.length > 3 && c2d.measureText(text).width > maxW) {
        text = text.slice(0, -2) + '.'
      }
      c2d.fillStyle = hot ? theme.accent : theme.text
      alpha(0.97)
      c2d.fillText(text, x, y0 + 10)
    })
    // throttle bar
    const barW = Math.min(w * 0.28, 200)
    const barX = view.cx - barW / 2
    const barY = h - Math.max(14, h * 0.022)
    c2d.strokeStyle = theme.stroke
    alpha(0.35)
    c2d.strokeRect(barX, barY, barW, 4)
    const t = Math.min(1, airspeed / 2.6)
    c2d.fillStyle = theme.accent
    alpha(0.9)
    c2d.fillRect(barX, barY, barW * t, 4)
    c2d.restore()
  }

  const arch0 = (arch) => arch * 0.5

  function drawNotes() {
    if (state.error) {
      c2d.save()
      c2d.fillStyle = theme.dim
      alpha(0.9)
      c2d.font = `400 11px ${FONT.data}`
      tracked('0.02em')
      c2d.fillText(`map unavailable · ${state.error}`.slice(0, 90), 18, view.h * 0.2)
      c2d.restore()
      return
    }
    if (!state.nodes.length) {
      c2d.save()
      c2d.fillStyle = theme.dim
      alpha(0.9)
      c2d.font = `400 11px ${FONT.data}`
      tracked('0.02em')
      c2d.fillText('nothing on the map yet · /walk puts some there', 18, view.h * 0.2)
      c2d.restore()
    }
  }

  // ---------------- flight ----------------
  let raf = 0, last = 0
  let stopped = false
  const keys = new Set()

  function tick(ts) {
    raf = 0
    if (stopped) return
    const dt = last ? Math.min(0.05, (ts - last) / 1000) : 0.016
    last = ts

    const turn = 1.6 * dt
    // A/D bank the ship (roll); the keyboard's yaw lives on the arrows so a
    // keyboard-only pilot still has every axis.
    if (keys.has('a')) state.cam.roll -= turn * 1.5
    if (keys.has('d')) state.cam.roll += turn * 1.5
    if (keys.has('q')) state.cam.pitch -= turn * 0.7
    if (keys.has('e')) state.cam.pitch += turn * 0.7
    if (keys.has('arrowleft')) state.cam.yaw -= turn
    if (keys.has('arrowright')) state.cam.yaw += turn
    let want = 0
    if (keys.has('w') || keys.has('arrowup')) want = 1
    if (keys.has('s') || keys.has('arrowdown')) want = -0.55
    if (keys.has('shift')) want *= 2.2
    // Throttle spools up, so the ship has weight instead of teleporting.
    state.cam.speed += (want - state.cam.speed) * Math.min(1, dt * 3.2)

    const b = basis()
    // Travel, don't teleport. The cloud is about two units across: at 0.2 the ship
    // still left it in about four seconds, so the throttle is slower than walking
    // pace and the shift key is the way to cross the map.
    const THRUST = 0.09
    state.cam.vx += b.fwd[0] * state.cam.speed * THRUST * dt
    state.cam.vy += b.fwd[1] * state.cam.speed * THRUST * dt
    state.cam.vz += b.fwd[2] * state.cam.speed * THRUST * dt
    // Momentum, not a leash: cut the throttle and the ship keeps gliding, so a
    // turn slides through the cloud instead of stopping to face it.
    const drag = Math.exp(-dt * (keys.has('s') ? 1.6 : 0.55))
    state.cam.vx *= drag
    state.cam.vy *= drag
    state.cam.vz *= drag
    const vmax = 0.16
    const speed = Math.hypot(state.cam.vx, state.cam.vy, state.cam.vz)
    if (speed > vmax) {
      const k = vmax / speed
      state.cam.vx *= k; state.cam.vy *= k; state.cam.vz *= k
    }
    state.cam.x += state.cam.vx * dt
    state.cam.y += state.cam.vy * dt
    state.cam.z += state.cam.vz * dt
    // The edge is a wall, and a wall stops the ship. It does not spring it back
    // and it does not let the throttle win: the position is clamped to the
    // boundary and the outward part of the velocity is cancelled, so flying
    // straight at it brings you to a dead stop with the map in front of you.
    // Tangential motion survives, which is what lets you slide along it under
    // thrust instead of sticking like glue.
    const radius = Math.hypot(state.cam.x, state.cam.y, state.cam.z)
    if (radius > MAP_RADIUS) {
      const nx = state.cam.x / radius
      const ny = state.cam.y / radius
      const nz = state.cam.z / radius
      // A dead stop, every time. Cancelling only the outward part left a measured ~0.002 u/s
      // creep along the shell — seven thousandths of a unit over twenty-four seconds with the
      // stick held in, which is small but visible as "the ship is still moving at the wall".
      // Contact is contact.
      state.cam.vx = 0
      state.cam.vy = 0
      state.cam.vz = 0
      state.cam.x = nx * MAP_RADIUS
      state.cam.y = ny * MAP_RADIUS
      state.cam.z = nz * MAP_RADIUS
    }
    state.cam.pitch = Math.max(-1.15, Math.min(1.15, state.cam.pitch))
    if (state.cam.yaw > Math.PI) state.cam.yaw -= Math.PI * 2
    if (state.cam.yaw < -Math.PI) state.cam.yaw += Math.PI * 2
    if (state.cam.roll > Math.PI) state.cam.roll -= Math.PI * 2
    if (state.cam.roll < -Math.PI) state.cam.roll += Math.PI * 2

    // Recoil settles whether or not the trigger is held.
    if (state.kick.l > 0) state.kick.l = Math.max(0, state.kick.l - dt)
    if (state.kick.r > 0) state.kick.r = Math.max(0, state.kick.r - dt)

    // The trigger is a held state: fire at the cadence, not once per press.
    state.cool -= dt
    if (state.firing && state.cool <= 0) shootAt(view.cx, view.cy)
    stepBullets(dt)

    if (state.net.active && !state.net.landed) {
      state.net.t = Math.min(1, state.net.t + dt / (reduced ? 0.05 : 0.32))
      if (state.net.t >= 1) { state.net.landed = true; resolveNet(b) }
    }

    draw()
    state.frames += 1
    if (!reduced && (keys.size || Math.abs(state.cam.speed) > 0.01 || state.net.active || state.firing
        || state.bullets.length || state.bursts.length)) raf = win.requestAnimationFrame(tick)
  }

  const schedule = () => {
    // Reduced motion renders one frame per explicit input.
    if (!raf && !stopped && !reduced) raf = win.requestAnimationFrame(tick)
    else if (reduced && !stopped) tick(last ? last + 16 : 16)
  }

  const resetFlight = () => {
    Object.assign(state.cam, {
      x: home.x, y: home.y, z: home.z, yaw: 0, pitch: 0, roll: 0, speed: 0, vx: 0, vy: 0, vz: 0
    })
    draw()
  }

  function resolveNet(b) {
    // Open the net where the ray is densest, not at a fixed distance: the plane
    // is a cloud with gaps, and a throw into a gap should still land on a knot.
    const CONE = Math.tan(17 * Math.PI / 180)
    const countAt = (depth) => {
      const radius = Math.max(0.08, depth * CONE)
      let n = 0
      for (const node of state.nodes) {
        const d = { x: node.x - state.cam.x, y: node.y - state.cam.y, z: node.z - state.cam.z }
        const dz = d.x * b.fwd[0] + d.y * b.fwd[1] + d.z * b.fwd[2]
        if (Math.abs(dz - depth) > 0.4) continue
        const off = Math.hypot(d.x - b.fwd[0] * dz, d.y - b.fwd[1] * dz, d.z - b.fwd[2] * dz)
        if (off <= radius) n++
      }
      return n
    }
    let depth = 1.25, best = -Infinity
    for (let d = 0.3; d <= 2.4; d += 0.1) {
      const score = countAt(d) - d * 0.3
      if (score > best) { best = score; depth = d }
    }
    state.net.reach = depth
    const radius = Math.max(0.08, depth * CONE)
    const caught = []
    for (const node of state.nodes) {
      const d = { x: node.x - state.cam.x, y: node.y - state.cam.y, z: node.z - state.cam.z }
      const dz = d.x * b.fwd[0] + d.y * b.fwd[1] + d.z * b.fwd[2]
      if (Math.abs(dz - depth) > 0.4) continue
      const off = Math.hypot(d.x - b.fwd[0] * dz, d.y - b.fwd[1] * dz, d.z - b.fwd[2] * dz)
      if (off <= radius) caught.push(node)
    }
    if (!caught.length) {
      // nothing near the ray: take the closest thing actually ahead
      let pick = null, bestAngle = 0.95
      for (const node of state.nodes) {
        const d = { x: node.x - state.cam.x, y: node.y - state.cam.y, z: node.z - state.cam.z }
        const dz = d.x * b.fwd[0] + d.y * b.fwd[1] + d.z * b.fwd[2]
        if (dz < 0.2 || dz > 3) continue
        const off = Math.hypot(d.x - b.fwd[0] * dz, d.y - b.fwd[1] * dz, d.z - b.fwd[2] * dz)
        const angle = Math.atan2(off, dz)
        if (angle < bestAngle) { bestAngle = angle; pick = { node, dz } }
      }
      if (pick) {
        state.net.reach = pick.dz
        const r = Math.max(0.12, pick.dz * CONE)
        for (const node of state.nodes) {
          const dx = node.x - state.cam.x, dy = node.y - state.cam.y, dz2 = node.z - state.cam.z
          const dz = dx * b.fwd[0] + dy * b.fwd[1] + dz2 * b.fwd[2]
          if (Math.abs(dz - pick.dz) > 0.45) continue
          const off = Math.hypot(dx - b.fwd[0] * dz, dy - b.fwd[1] * dz, dz2 - b.fwd[2] * dz)
          if (off <= r) caught.push(node)
        }
      }
    }
    state.catchList = caught.slice(0, 24)
    onCatch(state.catchList)
  }

  /**
   * Aim direction through a screen point, in this camera's own basis.
   *
   * Bullets travel, so aiming has to be a ray and not a screen-space pickup: the
   * shot leaves the barrel along the line you are pointing and has to arrive.
   */
  function aimDir(ax, ay) {
    const b = basis()
    const sx = (ax - view.cx) / view.f
    const sy = (view.cy - ay) / view.f
    const d = [
      b.fwd[0] + b.right[0] * sx + b.up[0] * sy,
      b.fwd[1] + b.right[1] * sx + b.up[1] * sy,
      b.fwd[2] + b.right[2] * sx + b.up[2] * sy
    ]
    const len = Math.hypot(d[0], d[1], d[2]) || 1
    return [d[0] / len, d[1] / len, d[2] / len]
  }

  /** The point the cannons converge on: the nearest concept under the reticle,
   *  or a point out in the air at CONVERGE when the crosshair is on nothing.
   *
   *  Converging on a fixed distance is what made the guns shoot wide: the shot
   *  leaves a muzzle well below the eye line, so it is only on the crosshair's
   *  ray where it has been aimed to meet it. */
  function aimPoint(d) {
    let best = null
    let bestD = Infinity
    for (const node of state.nodes) {
      const vx = node.x - state.cam.x
      const vy = node.y - state.cam.y
      const vz = node.z - state.cam.z
      const t = vx * d[0] + vy * d[1] + vz * d[2]
      if (t <= 0.15 || t >= bestD) continue
      const px = vx - d[0] * t
      const py = vy - d[1] * t
      const pz = vz - d[2] * t
      // This is only the point the muzzle aims at — collision stays a separate,
      // swept test, so a shot that misses the concept still misses it. The slack
      // scales with distance (a far concept covers less screen per unit) and is
      // capped so a shot into open glass never snaps onto something.
      const tol = Math.min(0.06, Math.max(0.02, t * 0.05))
      if (px * px + py * py + pz * pz > tol * tol) continue
      bestD = t
      best = node
    }
    return best
  }

  /** Where a cannon's muzzle sits on screen this frame. The recoil is a screen
   *  offset because the gun is part of the ship, not the world. */
  function gunScreen(side) {
    const k = state.kick[side < 0 ? 'l' : 'r'] / GUN_KICK
    const ui = uiScale(view.w)
    return {
      x: view.cx + side * GUN_X * ui,
      y: dashTop() - GUN_LEN * ui + k * 7 * ui
    }
  }

  function shootAt(ax, ay) {
    if (state.bullets.length >= MAX_BULLETS) state.bullets.shift()
    const d = aimDir(ax, ay)
    const b = basis()
    // Alternate barrels, a little off the centreline, so the stream reads as
    // fire from a ship rather than a stroke from the camera. The shot is then
    // aimed from the barrel at a point ON the aim ray — otherwise the offset
    // would bias every shot and a crosshair hit would miss by a barrel width.
    // Shots leave the ship's cannons, not the middle of the canopy: each shot
    // starts at the muzzle of whichever gun is up and is aimed at a point on the
    // crosshair's ray, so the two streams converge on the reticle.
    state.barrel = -state.barrel
    const side = state.barrel
    const gun = gunScreen(side)
    const gd = aimDir(gun.x, gun.y)
    const px = state.cam.x + gd[0] * MUZZLE_REACH
    const py = state.cam.y + gd[1] * MUZZLE_REACH
    const pz = state.cam.z + gd[2] * MUZZLE_REACH
    // Converge where the crosshair actually lands: the nearest concept along the
    // reticle's ray, or a default reach when there is nothing there. Converging
    // at a fixed distance would make the cannons shoot wide at every other depth.
    const under = aimPoint(d)
    const aim = under
      ? { x: under.x, y: under.y, z: under.z }
      : { x: state.cam.x + d[0] * CONVERGE, y: state.cam.y + d[1] * CONVERGE, z: state.cam.z + d[2] * CONVERGE }
    state.kick[side < 0 ? 'l' : 'r'] = GUN_KICK
    const vx = aim.x - px, vy = aim.y - py, vz = aim.z - pz
    const vl = Math.hypot(vx, vy, vz) || 1
    state.bullets.push({
      x: px, y: py, z: pz,
      px, py, pz,
      vx: (vx / vl) * BULLET_SPEED, vy: (vy / vl) * BULLET_SPEED, vz: (vz / vl) * BULLET_SPEED,
      life: BULLET_LIFE,
      ax, ay,
      gun: side
    })
    state.shotsFired += 1
    state.cool = FIRE_INTERVAL
    schedule()
    return true
  }

  /**
   * Move the bullets, and land the ones that arrive.
   *
   * Collision is a distance test in world space, not a screen ray: a bullet that
   * misses keeps going and expires, which is what makes holding the trigger feel
   * like firing rather than like selecting.
   */
  /** Squared distance from a point to a segment: a shot is swept, never tested
   * at one instant, or a fast bullet tunnels straight through a concept. */
  function segDist2(a, b, p) {
    const dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z
    const len2 = dx * dx + dy * dy + dz * dz
    let t = len2 > 0 ? ((p.x - a.x) * dx + (p.y - a.y) * dy + (p.z - a.z) * dz) / len2 : 0
    t = Math.max(0, Math.min(1, t))
    const cx = a.x + dx * t - p.x, cy = a.y + dy * t - p.y, cz = a.z + dz * t - p.z
    return cx * cx + cy * cy + cz * cz
  }

  function stepBullets(dt) {
    if (!state.bullets.length) return
    const keep = []
    for (const shot of state.bullets) {
      shot.px = shot.x; shot.py = shot.y; shot.pz = shot.z
      shot.x += shot.vx * dt; shot.y += shot.vy * dt; shot.z += shot.vz * dt
      shot.life -= dt
      let hitNode = null
      const from = { x: shot.px, y: shot.py, z: shot.pz }
      const to = { x: shot.x, y: shot.y, z: shot.z }
      for (const node of state.nodes) {
        if (segDist2(from, to, node) <= BULLET_R * BULLET_R) { hitNode = node; break }
      }
      if (hitNode) {
        state.hits[hitNode.l] = (state.hits[hitNode.l] || 0) + 1
        // The trail keeps the order it was flown: order is the only thing a route has that a
        // bag of concepts does not.
        if (flight.trail.indexOf(hitNode.l) < 0) flight.trail.push(hitNode.l)
        state.target = hitNode.l
        onTarget(hitNode)
        onName(hitNode.l, 'hit')
        onPicks(pickList())
        queuePicks()
        state.bursts.push({ x: shot.x, y: shot.y, z: shot.z, t: 0 })
        if (state.bursts.length > 24) state.bursts.shift()
        continue
      }
      if (shot.life > 0 && Math.abs(shot.x) < 1.9 && Math.abs(shot.y) < 1.9 && Math.abs(shot.z) < 1.9) keep.push(shot)
    }
    state.bullets = keep
    for (const burst of state.bursts) burst.t += dt
    state.bursts = state.bursts.filter((b) => b.t < 0.34)
  }

  function pickList() {
    return state.nodes
      .filter((n) => state.hits[n.l])
      .map((n) => ({ l: n.l, hits: state.hits[n.l], w: n.w, v: n.v }))
      .sort((a, z) => z.hits - a.hits || a.l.localeCompare(z.l))
  }



  // ---------------- input ----------------
  // Two ways to aim: click once and the mouse is captured (pointer lock, the
  // way a cockpit reads — the reticle is the cursor), or drag when the host
  // will not hand over the pointer. Escape always gives the mouse back.
  let drag = null
  let captured = false
  // Pointer lock is the way a cockpit reads, but the host is not obliged to grant it: a pane
  // that asks and is refused looks completely dead — the mouse that should be steering the ship
  // only reports hover. So capture is owned here as well: a pointer captured with
  // `setPointerCapture` keeps sending moves after the cursor leaves the canvas, which is the
  // whole of what steering needs, and needs no permission from anyone.
  let held = null
  // What this flight touched, in order, plus the verdicts given while flying. Handed over on
  // exit so the agent gets the result instead of the plugin throwing it away.
  const flight = { trail: [], kept: [], dropped: [] }
  const takeFlight = () => {
    const out = { trail: flight.trail.slice(), kept: flight.kept.slice(), dropped: flight.dropped.slice() }
    flight.trail.length = 0
    flight.kept.length = 0
    flight.dropped.length = 0
    return out
  }
  // Capture is sticky: one press takes the mouse, and it stays taken until Escape. Steering
  // that only worked while the button was down is not what a cockpit does — a person clicks
  // once, then moves the mouse and expects to turn.
  let engaged = false
  let touchPointer = null
  const TOUCH_TAP_SLOP = 10
  let pointerNote = ''
  const lockActive = () => {
    try { return !!doc.pointerLockElement && doc.pointerLockElement === el } catch (e) { return false }
  }
  const ownsPointer = () => lockActive() || engaged
  const steer = (dx, dy) => {
    if (!dx && !dy) return
    state.cam.yaw += dx * 0.0026
    state.cam.pitch = Math.max(-1.15, Math.min(1.15, state.cam.pitch - dy * 0.0022))
    schedule()
  }
  const onDown = (ev) => {
    // Touch drag turns; tap fires.
    if (ev.pointerType === 'touch') {
      onTouchFirst()
      touchPointer = { id: ev.pointerId, x: ev.clientX, y: ev.clientY, dragged: false }
      try { el.setPointerCapture(ev.pointerId) } catch (e) { /* document moves remain a fallback */ }
      if (typeof el.focus === 'function') { try { el.focus() } catch (e) { /* gone */ } }
      return
    }
    // Keys only reach this pane once it holds focus. A pane that is displayed
    // but not focused looks completely dead: nothing flies, nothing fires.
    if (typeof el.focus === 'function') { try { el.focus() } catch (e) { /* gone */ } }
    // Right button (or a two-finger drag on touch, mapped by the host to button 2)
    // looks; the left button is the trigger. Holding it fires a stream.
    if (ev.button === 2) {
      drag = { x: ev.clientX, y: ev.clientY, moved: 0 }
      return
    }
    const r = el.getBoundingClientRect()
    const ax = lockActive() ? view.cx : ev.clientX - r.left
    const ay = lockActive() ? view.cy : ev.clientY - r.top
    const aimed = aimPoint(aimDir(ax, ay))
    if (aimed) nameNode(aimed, 'click')
    state.firing = true
    shootAt(ax, ay)
    // Ask for the lock, take the pointer either way: a refused lock must still steer.
    if (el.requestPointerLock && !lockActive()) {
      try {
        const asked = el.requestPointerLock()
        // Chromium rejects when the host disallows locking; record why.
        if (asked && typeof asked.catch === 'function') {
          asked.catch((err) => {
            pointerNote = `${(err && err.name) || 'Error'}: ${(err && err.message) || 'refused'}`
          })
        }
      } catch (e) {
        pointerNote = `${(e && e.name) || 'Error'}: ${(e && e.message) || 'threw'}`
      }
    }
    // Held by our own accounting, not setPointerCapture (it throws when refused).
    // Document-level moves always arrive, which is all steering needs.
    engaged = true
    held = { x: ev.clientX, y: ev.clientY }
    el.style.cursor = 'none'
  }
  const onMove = (ev) => {
    if (ev.pointerType === 'touch' && touchPointer && ev.pointerId === touchPointer.id) {
      const dx = ev.clientX - touchPointer.x, dy = ev.clientY - touchPointer.y
      if (Math.abs(dx) + Math.abs(dy) > TOUCH_TAP_SLOP) touchPointer.dragged = true
      touchPointer.x = ev.clientX; touchPointer.y = ev.clientY
      steer(dx, dy)
      return
    }
    if (ownsPointer() || drag) return       // steering is the document's business (see onDocMove)
    if (!drag) {
      const r = el.getBoundingClientRect()
      const ax = ev.clientX - r.left, ay = ev.clientY - r.top
      let nearest = null, distance = Infinity
      const b = basis()
      for (const node of state.nodes) {
        const c = toCam(node, b)
        if (c.z <= 0.05) continue
        const s = project(c)
        const d = Math.hypot(s.x - ax, s.y - ay)
        if (d < distance) { nearest = node; distance = d }
      }
      if (nearest && distance <= 18) nameNode(nearest, 'hover')
      return
    }
  }
  // Steering, wherever the pointer is. A locked pointer reports movements; a held one reports
  // the delta from its last position; a right-drag reports its own. All three land here so none
  // of them depends on the pointer staying inside the canvas.
  const onDocMove = (ev) => {
    if (lockActive()) { steer(ev.movementX || 0, ev.movementY || 0); return }
    if (drag) {
      const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y
      drag.moved += Math.abs(dx) + Math.abs(dy)
      drag.x = ev.clientX; drag.y = ev.clientY
      steer(dx * 1.23, dy * 1.18)          // the drag rate the pane has always used
      return
    }
    if (engaged) {
      const dx = ev.movementX || (ev.clientX - held.x)
      const dy = ev.movementY || (ev.clientY - held.y)
      held.x = ev.clientX; held.y = ev.clientY
      steer(dx, dy)
    }
  }
  const onUp = (ev) => {
    if (ev.pointerType === 'touch' && touchPointer && ev.pointerId === touchPointer.id) {
      const tap = !touchPointer.dragged
      touchPointer = null
      try { el.releasePointerCapture(ev.pointerId) } catch (e) { /* gone */ }
      if (tap) shootAt(view.cx, view.cy)
      return
    }
    // Release the trigger. No click-to-select: the shot is the whole interaction.
    state.firing = false
    drag = null
    el.style.cursor = ownsPointer() ? 'none' : 'crosshair'
  }
  const onLockChange = () => {
    captured = lockActive()
    el.style.cursor = captured ? 'none' : 'crosshair'
    draw()
  }
  const onKey = (ev) => {
    const k = String(ev.key || '').toLowerCase()
    if (k === 'w' || k === 'a' || k === 's' || k === 'd' || k === 'q' || k === 'e' || k === 'shift'
        || k === 'arrowup' || k === 'arrowdown' || k === 'arrowleft' || k === 'arrowright') {
      keys.add(k); ev.preventDefault(); schedule(); return
    }
    if (k === 'f') {
      ev.preventDefault()
      if (!state.firing) { state.firing = true; shootAt(view.cx, view.cy) }
      return
    }
    if (k === ' ') { ev.preventDefault(); state.net = { active: true, t: 0, landed: false, reach: 1.25 }; state.catchList = []; onCatch([]); schedule() }
    else if (k === '0' || k === 'home') { resetFlight() }
    else if (k === 'c') { state.catchList = []; onCatch([]); draw() }
    else if (k === 'escape') {
      // Escape hands the mouse back and nothing else. Capture is sticky now, so this is the
      // only key that gives the cursor back without ending the flight — leaving it to also
      // exit meant a person who wanted their mouse back lost the view they were looking at.
      // The exit button is the exit: it is drawn in the corner and it files the flight.
      if (lockActive()) { try { doc.exitPointerLock() } catch (e) { /* gone */ } }
      state.firing = false
      held = null
      touchPointer = null
      engaged = false
      drag = null
      try { el.style.cursor = 'crosshair' } catch (e) { /* gone */ }
      draw()
    }
  }
  const onKeyUp = (ev) => {
    const k = String(ev.key || '').toLowerCase()
    keys.delete(k)
    if (k === 'f') state.firing = false
  }

  el.addEventListener('pointerdown', onDown)
  el.addEventListener('pointermove', onMove)
  el.addEventListener('pointerup', onUp)
  el.addEventListener('pointercancel', onUp)
  el.addEventListener('keydown', onKey)
  el.addEventListener('keyup', onKeyUp)

  // The pane must not depend on holding focus to fly. A canvas inside the app's
  // layout loses focus whenever the app re-renders around it, and then every key
  // silently does nothing. Listen at the document level too, and leave typing
  // alone: text fields, contenteditable and the pane's own bubbled events bail.
  const typing = (ev) => {
    const t = ev.target
    if (!t) return false
    const tag = String(t.tagName || '').toLowerCase()
    return tag === 'input' || tag === 'textarea' || tag === 'select' || t.isContentEditable === true
  }
  const onKeyDoc = (ev) => {
    if (typing(ev) || el.contains(ev.target)) return
    onKey(ev)
  }
  const onKeyUpDoc = (ev) => {
    if (typing(ev) || el.contains(ev.target)) return
    onKeyUp(ev)
  }
  doc.addEventListener('keydown', onKeyDoc)
  doc.addEventListener('keyup', onKeyUpDoc)
  doc.addEventListener('pointerlockchange', onLockChange)
  // The browser can drop a capture on its own (window blur, a host re-layout). Treat that as
  // the trigger releasing, so a lost capture cannot leave the ship firing forever.
  // A press that starts outside the canvas and ends on it must not leave the trigger on.
  const onUpDoc = (ev) => { if (held || drag) onUp(ev) }
  doc.addEventListener('pointermove', onDocMove)
  doc.addEventListener('pointerup', onUpDoc)
  doc.addEventListener('pointercancel', onUpDoc)

  // panes are resized constantly by sash drags: track the box, not a mount size
  let ro = null
  fit()
  if (typeof win.ResizeObserver === 'function') {
    ro = new win.ResizeObserver(() => { fit(); draw() })
    ro.observe(el)
  }

  // A read-only handle for debugging in the running app: the pane is canvas-only,
  // so without this there is no way to tell "empty graph" from "empty view".
  try {
    win.__cockpitDebug = () => {
      const b = basis()
      let front = 0, onScreen = 0, close = 0, minD = Infinity
      for (const node of state.nodes) {
        const c = toCam(node, b)
        if (c.z > 0.05) front += 1
        const s = project(c)
        if (c.z > 0.05 && s.x > 0 && s.y > 0 && s.x < view.w && s.y < view.h) onScreen += 1
        const d = Math.hypot(node.x - state.cam.x, node.y - state.cam.y, node.z - state.cam.z)
        if (d < minD) minD = d
        if (d < 0.6) close += 1
      }
      return { nodes: state.nodes.length, front, onScreen, close, minD: Number(minD.toFixed(3)),
               view: { w: view.w, h: view.h, f: view.f }, cam: { ...state.cam } }
    }
  } catch (e) { /* gone */ }

  let timer = null
  const stopPoll = () => { if (typeof timer === 'function') { try { timer() } catch (e) { /* gone */ } } else if (timer) { win.clearInterval(timer) } }
  poll()
  timer = ctx.setInterval ? ctx.setInterval(poll, COCKPIT_POLL_MS) : win.setInterval(poll, COCKPIT_POLL_MS)
  schedule()

  return {
    stats: () => ({
      nodes: state.nodes.length,
      lit: state.lit,
      key: state.key,
      path: state.path.length,
      frames: state.frames,
      catchCount: state.catchList.length,
      picks: pickList().length,
      shots: state.shotsFired,
      bullets: state.bullets.length,
      firing: state.firing,
      // Whether the pane owns the pointer — by lock or by capture — because "the mouse does
      // nothing" and "the mouse is steering a ship that is not moving" look identical on film.
      pointer: ownsPointer(),
      lock: lockActive(),
      pointerNote,
      hits: Object.keys(state.hits).length,
      target: state.target,
      error: state.error,
      reduced,
      ground: theme.ground,
      size: { w: view.w, h: view.h, dpr: view.dpr },
      cam: {
        x: state.cam.x, y: state.cam.y, z: state.cam.z,
        yaw: state.cam.yaw, pitch: state.cam.pitch, roll: state.cam.roll,
        speed: Math.hypot(state.cam.vx, state.cam.vy, state.cam.vz)
      }
    }),
    /** Everything this flight touched, in order, with the verdicts — and then forget it. */
    takeFlight: () => takeFlight(),
    /** A keep or a trash given while flying. Verdicts are the product metric, so they ride along. */
    noteVerdict: (label, verdict) => {
      const name = String(label || '')
      if (!name) return
      const into = verdict === 'keep' ? flight.kept : (verdict === 'trash' ? flight.dropped : null)
      if (!into) return
      const other = verdict === 'keep' ? flight.dropped : flight.kept
      const i = other.indexOf(name)
      if (i >= 0) other.splice(i, 1)
      if (into.indexOf(name) < 0) into.push(name)
    },
    // Test seams: a harness drives the same functions the input handlers do.
    apply,
    resolveNet: () => resolveNet(basis()),
    fire: shootAt,
    picks: pickList,
    // Harness seam: where the shots are on screen right now, in the same
    // projection the drawing uses. A bullet nobody can see is not a bullet.
    bulletScreen: () => state.bullets.map((shot) => {
      const c = toCam(shot, basis())
      return c.z > 0.05 ? { ...project(c), z: c.z, world: [shot.x, shot.y, shot.z], life: shot.life } : null
    }).filter(Boolean),
    key: (k) => {
      keys.add(k)
      if (k === 'f' && !state.firing) { state.firing = true; shootAt(view.cx, view.cy) }
      schedule()
    },
    unkey: (k) => { keys.delete(k); if (k === 'f') state.firing = false },
    releasePointer: () => onKey({ key: 'Escape', preventDefault: () => {} }),
    home: resetFlight,
    /** Where a label currently lands on the glass — used to aim a harness click. */
    screenOf: (label) => {
      const node = state.nodes.find((n) => n.l === label)
      if (!node) return null
      const c = toCam(node, basis())
      if (c.z <= 0.05) return null
      return project(c)
    },
    draw,
    destroy: () => {
      stopped = true
      if (raf) { try { win.cancelAnimationFrame(raf) } catch (e) { /* gone */ } }
      raf = 0
      // A pick still in the debounce window belongs to a pane that is going away; file it
      // before the listeners come off rather than dropping the last shot of the session.
      if (pickTimer) { win.clearTimeout(pickTimer); pickTimer = 0; flushPicks() }
      stopPoll()
      if (ro) { try { ro.disconnect() } catch (e) { /* gone */ } }
      el.removeEventListener('pointerdown', onDown)
      el.removeEventListener('pointermove', onMove)
      el.removeEventListener('pointerup', onUp)
      el.removeEventListener('pointercancel', onUp)
      el.removeEventListener('keydown', onKey)
      el.removeEventListener('keyup', onKeyUp)
      doc.removeEventListener('pointermove', onDocMove)
      doc.removeEventListener('pointerup', onUpDoc)
      doc.removeEventListener('pointercancel', onUpDoc)
      doc.removeEventListener('keydown', onKeyDoc)
      doc.removeEventListener('keyup', onKeyUpDoc)
      doc.removeEventListener('pointerlockchange', onLockChange)
      try { if (lockActive()) doc.exitPointerLock() } catch (e) { /* gone */ }
    }
  }
}

/**
 * Verdict controls are ordinary buttons rather than canvas hit targets: both the
 * label and the action remain reachable without a pointer. Network failure is
 * intentionally quiet — a personal judgement must not interrupt flight.
 */
function CockpitVerdict({ ctx, named, onVerdict }) {
  const [tally, setTally] = useState(null)
  const [busy, setBusy] = useState('')
  const label = named && named.label ? named.label : ''
  const source = named && named.source ? named.source : 'near'
  const win = typeof window === 'undefined' ? null : window
  const reduced = reducedMotion(win || {})

  const readSession = () => {
    try {
      const atom = host && host.state && host.state.focusedSessionId
      return atom && atom.get ? String(atom.get() || '') : ''
    } catch (e) { return '' }
  }
  const readTally = () => {
    if (!win || typeof win.fetch !== 'function') return
    try {
      const request = ctx && typeof ctx.rest === 'function'
        ? ctx.rest('/verdicts')
        : win.fetch(`/api/plugins/${ID}/verdicts`).then((response) => response && response.ok ? response.json() : null)
      Promise.resolve(request).then((data) => {
        if (!data || typeof data !== 'object') return
        const keep = Number(data.keep)
        const trash = Number(data.trash)
        if (Number.isFinite(keep) && Number.isFinite(trash)) setTally({ keep, trash })
      }).catch(() => {})
    } catch (e) { /* optional endpoint: the controls still work locally */ }
  }
  useEffect(() => {
    readTally()
    if (!ctx || typeof ctx.setInterval !== 'function') return undefined
    const stop = ctx.setInterval(readTally, COCKPIT_POLL_MS)
    return () => { if (typeof stop === 'function') stop() }
  }, [ctx])

  const submit = (verdict) => {
    if (!label || busy) return
    setBusy(verdict)
    const payload = { label, verdict, session: readSession() }
    try {
      // The pane lives on a file:// origin in the packaged app, where a relative
      // `fetch` cannot reach the gateway ("Failed to fetch") — the host's own REST
      // door is the only route that carries the session cookie. `ctx.rest` first,
      // the raw fetch only where a host has no door (the harness).
      const request = ctx && typeof ctx.rest === 'function'
        ? ctx.rest('/verdict', { method: 'POST', body: payload })
        : win && typeof win.fetch === 'function'
          ? win.fetch(`/api/plugins/${ID}/verdict`, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify(payload)
          }).then((response) => response && response.ok ? response.json() : null)
          : null
      Promise.resolve(request).then((data) => {
        if (data && data.ok) readTally()
      }).catch(() => {}).finally(() => setBusy(''))
    } catch (e) { setBusy('') }
    onVerdict(verdict)
  }

  useEffect(() => {
    const onKey = (event) => {
      const target = event.target
      const tag = String(target && target.tagName || '').toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select' || (target && target.isContentEditable)) return
      if (event.metaKey || event.ctrlKey || event.altKey) return
      const key = String(event.key || '').toLowerCase()
      if (key !== 'k' && key !== 't') return
      if (!label) return
      event.preventDefault()
      submit(key === 'k' ? 'keep' : 'trash')
    }
    if (!win) return undefined
    win.document.addEventListener('keydown', onKey)
    return () => win.document.removeEventListener('keydown', onKey)
  }, [label, busy])

  const control = (verdict, key, text) => jsx('button', {
    type: 'button',
    disabled: !label || Boolean(busy),
    onClick: () => submit(verdict),
    onFocus: (event) => { event.currentTarget.style.outline = '2px solid var(--ui-accent, currentColor)' },
    onBlur: (event) => { event.currentTarget.style.outline = 'none' },
    'aria-keyshortcuts': key,
    'aria-label': `${text} ${label || 'nearest concept'} (${key})`,
    style: {
      background: 'var(--ui-panel-background, transparent)',
      border: '1px solid var(--ui-stroke-secondary, currentColor)',
      borderRadius: '2px', color: 'var(--ui-text, currentColor)', cursor: label ? 'pointer' : 'default',
      padding: '4px 7px', font: `600 10px ${FONT.label}`, letterSpacing: '0.12em', textTransform: 'uppercase',
      opacity: label ? 1 : 0.55, outline: 'none', outlineOffset: '2px'
    },
    children: `${text} · ${key}`
  }, verdict)

  return jsxs('div', {
    style: {
      position: 'absolute', left: '18px', top: '82px', zIndex: 2, maxWidth: 'min(62%, 420px)',
      padding: '6px 8px 7px', ...PANEL, ...DATA, transition: reduced ? 'none' : 'opacity 180ms ease'
    },
    'aria-live': 'polite',
    children: [
      jsx('div', { style: { ...LABEL, color: 'var(--ui-text-secondary, inherit)' }, children: label ? `${source} · ${label}` : 'aim at a concept' }, 'name'),
      jsxs('div', { style: { display: 'flex', gap: '5px', marginTop: '5px' }, children: [
        control('keep', 'K', 'keep'), control('trash', 'T', 'trash')
      ] }, 'controls'),
      tally ? jsx('div', { style: { ...DATA, marginTop: '5px', color: 'var(--ui-text-secondary, inherit)' }, children: `kept ${tally.keep} · dropped ${tally.trash}` }, 'tally') : null
    ]
  })
}


/** The page: the state and the cockpit as two tabs of one screen.
 *
 * The cockpit used to be a second entry in the sidebar and a second full-height pane, which
 * made two products out of one plugin. It is a way of reading the same state, so it is a tab
 * beside it — one nav row, one page, one place to look.
 */
function AntemuseScreen({ ctx, start }) {
  const [tab, setTab] = useState(start === 'cockpit' ? 'cockpit' : 'state')
  const tabs = [
    { id: 'state', label: copy.state },
    { id: 'cockpit', label: copy.cockpit }
  ]
  const strip = jsx('div', {
    role: 'tablist',
    style: {
      display: 'flex', gap: '2px', padding: '4px 10px 0', flex: '0 0 auto',
      borderBottom: '1px solid var(--ui-stroke-secondary)'
    },
    children: tabs.map((one) => {
      const { id, ...tabProps } = one
      return jsx('button', {
      role: 'tab',
      'aria-selected': tab === id,
      tabIndex: tab === id ? 0 : -1,
      onClick: () => setTab(id),
      title: tabProps.label,
      style: {
        font: 'inherit', fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase',
        padding: '5px 10px 6px', cursor: 'pointer', background: 'transparent',
        color: tab === id ? 'var(--ui-text)' : 'var(--ui-text-secondary)',
        // The selected tab is marked by the accent rule under it, not by a filled box: on a
        // dark theme a panel-coloured pill reads as another piece of the backdrop.
        border: '0',
        borderBottom: '2px solid ' + (tab === id ? 'var(--ui-accent)' : 'transparent'),
        opacity: tab === id ? '1' : '0.72'
      },
      children: tabProps.label
    }, id)
    })
  }, 'strip')
  return jsx('div', {
    style: { display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 },
    children: [
      strip,
      jsx('div', {
        style: { position: 'relative', flex: '1 1 auto', minHeight: 0 },
        children: tab === 'cockpit'
          ? jsx(CockpitPane, { ctx, onExit: () => setTab('state') }, 'cockpit')
          : jsx(StateView, { ctx, onOpenCockpit: () => setTab('cockpit') }, 'state')
      }, 'body')
    ]
  })
}

/** The pane: a canvas, and the catches/selection as real text beside it. */
/**
 * File a flight. Escape hands the mouse back and stays, so the drawn exit button is the only
 * door that leaves — which makes this the only place a flight is written down, and worth a
 * function a harness can call without mounting a canvas.
 */
export function fileFlight(ctx, left) {
  if (!left) return null
  const payload = {
    trail: left.trail || [], kept: left.kept || [], dropped: left.dropped || [],
    session: (ctx && ctx.session) || ''
  }
  // A failed note is deliberately quiet — the exit must not be blocked by a lost one — but
  // "quiet" made a broken wire indistinguishable from a working one, so the outcome is kept
  // where a person (or a probe) can ask for it.
  const where = typeof window === 'undefined' ? null : window
  const record = (ok, detail) => {
    try { if (where) where.__flightPost = { ok, at: Date.now(), payload, detail } } catch (e) { /* gone */ }
  }
  try {
    if (ctx && typeof ctx.rest === 'function') {
      return Promise.resolve(ctx.rest('/flight', { method: 'POST', body: payload }))
        .then((res) => { record(true, res); return res })
        .catch((err) => { record(false, String(err && err.message ? err.message : err)); })
    }
    if (where && typeof where.fetch === 'function') {
      // The same record on the branch a host reaches when it has no `ctx.rest`: this is the
      // fallback that exists *because* the primary door can be missing, so leaving it silent
      // meant the one path most likely to fail was the one that never said why.
      return where.fetch(`/api/plugins/${ID}/flight`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload)
      })
        .then((res) => { record(true, res); return res })
        .catch((err) => { record(false, String(err && err.message ? err.message : err)); })
    }
  } catch (e) { /* a note that cannot be filed must not stop the exit */ }
  return null
}

// Touch controls are DOM buttons for accessibility.
function TouchControls({ cockpitRef, onRelease }) {
  const press = (key) => () => { if (cockpitRef.current) cockpitRef.current.key(key) }
  const release = (key) => () => { if (cockpitRef.current) cockpitRef.current.unkey(key) }
  const button = (id, label, key, text) => jsx('button', {
    type: 'button', id, 'aria-label': label, 'aria-keyshortcuts': key.toUpperCase(),
    onPointerDown: (event) => { event.preventDefault(); press(key)() },
    onPointerUp: release(key), onPointerCancel: release(key), onPointerLeave: release(key),
    style: {
      minWidth: '44px', minHeight: '44px', padding: '8px 10px', touchAction: 'none',
      background: 'var(--ui-panel-background, transparent)', color: 'var(--ui-text, currentColor)',
      border: '1px solid var(--ui-stroke-secondary, currentColor)', borderRadius: '2px',
      font: `600 10px ${FONT.label}`, letterSpacing: '0.12em', cursor: 'pointer'
    }, children: text
  }, id)
  return jsxs('div', {
    'aria-label': 'Touch flight controls',
    style: {
      position: 'absolute', left: '10px', right: '10px', bottom: '10px', zIndex: 4,
      display: 'flex', justifyContent: 'space-between', gap: '8px', maxWidth: 'calc(100% - 20px)',
      pointerEvents: 'auto', boxSizing: 'border-box'
    },
    children: [
      jsxs('div', { style: { display: 'flex', gap: '8px' }, children: [
        button('touch-steer-left', 'Turn left (Left Arrow)', 'arrowleft', 'left'),
        button('touch-steer-right', 'Turn right (Right Arrow)', 'arrowright', 'right')
      ] }, 'turn'),
      jsxs('div', { style: { display: 'flex', gap: '8px' }, children: [
        button('touch-fire', 'Fire (F)', 'f', 'fire'),
        jsx('button', {
          type: 'button', id: 'touch-release', 'aria-label': 'Release pointer (Escape)', 'aria-keyshortcuts': 'Escape',
          onClick: onRelease,
          style: {
            minWidth: '44px', minHeight: '44px', padding: '8px 10px', touchAction: 'manipulation',
            background: 'var(--ui-panel-background, transparent)', color: 'var(--ui-text, currentColor)',
            border: '1px solid var(--ui-stroke-secondary, currentColor)', borderRadius: '2px',
            font: `600 10px ${FONT.label}`, letterSpacing: '0.12em', cursor: 'pointer'
          }, children: 'release'
        }, 'release')
      ] }, 'actions')
    ]
  }, 'touch-controls')
}

function CockpitPane({ ctx, onExit }) {
  const cockpitRef = useRef(null)
  const leaving = useRef(false)

  // Leaving is the moment the flight becomes material. A panel that closes silently is a
  // panel whose work was thrown away, which is what this used to do.
  const postFlight = (left) => fileFlight(ctx, left)

  const leave = () => {
    if (leaving.current) return
    leaving.current = true
    const took = cockpitRef.current ? cockpitRef.current.takeFlight() : null
    postFlight(took)
    if (typeof onExit === 'function') onExit()
  }
  const canvasRef = useRef(null)
  const [caught, setCaught] = useState([])
  const [picks, setPicks] = useState([])
  const [named, setNamed] = useState(null)
  const [notice, setNotice] = useState(null)
  const [engaged, setEngaged] = useState(false)
  const [touchFirst, setTouchFirst] = useState(false)
  const reduced = reducedMotion(typeof window === 'undefined' ? {} : window)

  useEffect(() => {
    const win = typeof window === 'undefined' ? null : window
    if (!win || !win.matchMedia) return undefined
    const media = win.matchMedia('(pointer: coarse)')
    const apply = () => setTouchFirst(Boolean(media.matches))
    apply()
    if (typeof media.addEventListener === 'function') media.addEventListener('change', apply)
    else if (typeof media.addListener === 'function') media.addListener(apply)
    return () => {
      if (typeof media.removeEventListener === 'function') media.removeEventListener('change', apply)
      else if (typeof media.removeListener === 'function') media.removeListener(apply)
    }
  }, [])

  useEffect(() => {
    if (!notice) return undefined
    const fade = reduced ? null : setTimeout(() => {
      setNotice((current) => current && current.at === notice.at ? { ...current, visible: false } : current)
    }, 1300)
    const clear = setTimeout(() => {
      setNotice((current) => current && current.at === notice.at ? null : current)
    }, reduced ? 1300 : 1480)
    return () => { if (fade) clearTimeout(fade); clearTimeout(clear) }
  }, [notice, reduced])

  useEffect(() => {
    const el = canvasRef.current
    if (!el) return undefined
    const cockpit = createCockpit({
      ctx,
      el,
      callbacks: {
        onCatch: (list) => setCaught(list.map((n) => ({ l: n.l, w: n.w }))),
        onTarget: () => {},
        onName: (label, source) => {
          const event = { label, source, at: Date.now(), visible: true }
          setNamed(event)
          setNotice(event)
        },
        onPicks: (list) => setPicks(list.slice(0, 30)),
        onTouchFirst: () => setTouchFirst(true)
      }
    })
    // The cockpit is a page the user navigated to, so it takes the keyboard when
    // it mounts. Otherwise the first frame is a still picture and every key looks
    // broken until the user happens to click it.
    const focusTimer = setTimeout(() => { try { el.focus() } catch (e) { /* gone */ } }, 80)
    // The same read-only handle the harness uses, exposed in the running app: a canvas-only
    // pane gives no way to tell "the pointer is not captured" from "the ship is not moving".
    try { window.__cockpit = cockpit } catch (e) { /* no window */ }
    cockpitRef.current = cockpit
    return () => {
      cockpitRef.current = null
      if (focusTimer) clearTimeout(focusTimer)
      try { if (window.__cockpit === cockpit) delete window.__cockpit } catch (e) { /* gone */ }
      cockpit.destroy()
    }
  }, [ctx])

  // Until the pane has been clicked it cannot hear the keyboard, so say so
  // rather than presenting a still picture the user has to guess at.
  const hint = engaged
    ? null
    : jsx('div', {
        style: {
          position: 'absolute', left: '50%', top: '58%', transform: 'translateX(-50%)',
          pointerEvents: 'none', textAlign: 'center', whiteSpace: 'nowrap',
          ...LABEL, letterSpacing: '0.18em'
        },
        children: 'click to capture \u00b7 w/s throttle \u00b7 a/d bank \u00b7 arrows turn \u00b7 f fire \u00b7 esc frees the mouse'
      }, 'hint')

  const hitNotice = notice
    ? jsx('div', {
        style: {
          position: 'absolute', left: '50%', top: '18%', transform: 'translateX(-50%)', zIndex: 2,
          pointerEvents: 'none', ...DATA, color: 'var(--ui-text, currentColor)',
          opacity: notice.visible ? 0.95 : 0,
          transition: reduced ? 'none' : 'opacity 180ms ease'
        },
        children: `${notice.source} · ${notice.label}`
      }, `notice-${notice.at}`)
    : null

  const list = caught.length
    ? jsx('ul', {
        key: 'catch',
        className: 'antemuse-cockpit-catch',
        style: {
          position: 'absolute', left: '18px', bottom: '84px', margin: 0, padding: '6px 10px 7px',
          listStyle: 'none', maxWidth: 'min(46%, 340px)', maxHeight: '32%', overflow: 'hidden',
          ...PANEL, ...DATA, borderLeft: '2px solid var(--ui-accent, currentColor)'
        },
        children: [
          jsx('li', { key: 'head', style: { ...LABEL, color: 'var(--ui-text-secondary, inherit)' }, children: `net \u00b7 ${caught.length}` }),
          ...caught.slice(0, 6).map((n) => jsx('li', { key: n.l, children: n.l }))
        ]
      })
    : null

  // Interest is the pick list: ordered by how many times a concept was shot,
  // so the top of this column is what the session keeps coming back to.
  const pickPanel = picks.length
    ? jsxs('div', {
        key: 'picks',
        style: {
          position: 'absolute', right: '18px', top: '96px', padding: '6px 10px 7px',
          ...PANEL, ...DATA, maxWidth: '38%', maxHeight: '46%', overflow: 'hidden'
        },
        children: [
          jsx('div', {
            key: 'head',
            style: { ...LABEL, display: 'flex', gap: '8px', justifyContent: 'space-between' },
            children: [
              jsx('span', { key: 't', children: 'picked' }),
              jsx('span', { key: 'n', style: { color: 'var(--ui-accent, currentColor)' }, children: picks.length })
            ]
          }),
          ...picks.slice(0, 8).map((p) => jsxs('div', {
            key: p.l,
            style: { display: 'flex', gap: '8px', justifyContent: 'space-between' },
            children: [
              jsx('span', { key: 'l', children: p.l }),
              jsx('span', { key: 'n', style: { color: 'var(--ui-accent, currentColor)' }, children: `\u00d7${p.hits}` })
            ]
          }, p.l))
        ]
      })
    : null

  // The exit is drawn where a pilot is looking. Escape only releases the mouse and stays.
  const exitButton = jsx('button', {
    type: 'button',
    onClick: () => leave(),
    title: 'Leave the cockpit and file the flight; Escape only releases the mouse',
    'aria-label': 'Leave the cockpit',
    'aria-description': 'Files the flight; Escape only releases the mouse',
    style: {
      position: 'absolute', right: '14px', top: '12px', zIndex: 3,
      ...LABEL, letterSpacing: '0.14em', cursor: 'pointer',
      display: 'flex', alignItems: 'center', gap: '6px',
      padding: '5px 9px 6px', borderRadius: '2px',
      background: 'var(--ui-panel-background, transparent)',
      color: 'var(--ui-text, currentColor)',
      border: '1px solid var(--ui-stroke-secondary, currentColor)'
    },
    children: ['exit', jsx('span', { style: { opacity: '0.6' }, children: 'esc' }, 'k')]
  }, 'exit')

  // Captured is a state the person has to be able to see: the cursor is hidden, and a pane
  // that silently holds the mouse is indistinguishable from one that is broken.
  const captureBadge = engaged
    ? jsx('div', {
        style: {
          position: 'absolute', right: '14px', top: '52px', zIndex: 3, pointerEvents: 'none',
          ...LABEL, letterSpacing: '0.14em', padding: '4px 8px 5px', borderRadius: '2px',
          color: 'var(--ui-text-secondary, currentColor)',
          border: '1px solid var(--ui-stroke-secondary, currentColor)'
        },
        children: 'mouse captured · esc'
      }, 'captured')
    : null

  const touchControls = touchFirst
    ? jsx(TouchControls, {
        cockpitRef,
        onRelease: () => { if (cockpitRef.current) cockpitRef.current.releasePointer() }
      }, 'touch-controls')
    : null

  return jsxs('div', {
    style: { position: 'relative', width: '100%', height: '100%', minHeight: '240px', overflow: 'hidden' },
    children: [
      exitButton,
      captureBadge,
      jsx('canvas', {
        ref: canvasRef,
        tabIndex: 0,
        onPointerDown: () => setEngaged(true),
        onFocus: () => setEngaged(true),
        onBlur: () => setEngaged(false),
        role: 'application',
        'aria-label': 'Concept cockpit. Click once to capture the mouse; while captured, moving turns the ship and the left button fires a stream. Escape releases the mouse; the exit button leaves and files the flight. W and S throttle, A and D bank, arrow keys turn and pitch, space opens the net, 0 returns home, Escape releases the mouse.',
        style: { position: 'absolute', inset: 0, width: '100%', height: '100%', display: 'block', cursor: 'crosshair', touchAction: 'none' }
      }, 'canvas'),
      hint,
      hitNotice,
      touchControls,
      jsx(CockpitVerdict, {
        ctx,
        named,
        onVerdict: (verdict) => {
          if (named && named.label) {
            setNamed({ ...named, source: verdict, at: Date.now() })
            // A keep or a trash given in flight belongs to the flight, not just to the readout.
            if (cockpitRef.current) cockpitRef.current.noteVerdict(named.label, verdict)
          }
        }
      }, 'verdict'),
      list,
      pickPanel
    ]
  })
}

// Kept as a named export so a harness can drive the renderer without React; CockpitPane is
// exported too so the mount harness can exercise its exit control.
export { createCockpit, CockpitPane }

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
      render: () => jsx(AntemuseScreen, { ctx, start: 'state' })
    })
    ctx.register({
      id: 'nav',
      area: SIDEBAR_NAV_AREA,
      order: 60,
      data: { codicon: 'pulse', label: copy.pane, path: `/${ID}` }
    })
    // The cockpit is the same screen read from a heading instead of from above: a tab inside
    // Antemuse, not a second product with its own nav row. Its own route stays so a deep link
    // and the palette command still land, opening on that tab.
    ctx.register({
      id: 'cockpit-page',
      area: ROUTES_AREA,
      data: { path: `/${ID}/cockpit` },
      render: () => jsx(AntemuseScreen, { ctx, start: 'cockpit' })
    })
    ctx.register({
      id: 'cockpit-open',
      area: PALETTE_AREA,
      title: copy.cockpitOpen,
      run: () => goto(ctx, `/${ID}/cockpit`)
    })
    ctx.register({
      id: 'watch',
      area: PALETTE_AREA,
      title: copy.watch,
      run: () => goto(ctx, `/${ID}`)
    })
    // Settings are NOT a bespoke page: the host renders this plugin's manifest
    // `config_schema` as a form under Settings ▸ Plugins and saves it to
    // plugins.entries.antemuse.settings. Registering our own page here would shadow
    // that form with a second, divergent copy of the same controls.

  }
}
