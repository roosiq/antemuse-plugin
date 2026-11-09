// The 3D family: a real scene, converted to glyphs by three's own AsciiEffect.
//
// AsciiEffect is the reference implementation of "3D into characters": it
// renders the WebGL canvas, draws that down into a small 2D canvas at
// `resolution`, maps each pixel's brightness onto a character ramp and emits a
// table of spans — with `color` and `alpha` it writes a per-character colour and
// opacity, which is the mode that does not look like a terminal dump.
//
// Geometry is the brand's: hard-surface, geometric, no curves for their own
// sake. One chamfered slab turning slowly in fog, one thin ring, an amber key
// light and a teal rim. Amber is the only warm thing in the frame.

import * as THREE from './vendor/three.module.js'
import { AsciiEffect } from './vendor/AsciiEffect.js'

const RAMP = ' .:-=+*#%@'

/** A box with the top and bottom faces chamfered — a machined slab, not a cube. */
function slab(width, height, depth, bevel) {
  const geo = new THREE.BoxGeometry(width, height, depth, 1, 1, 1)
  const pos = geo.attributes.position
  const half = height / 2
  for (let i = 0; i < pos.count; i++) {
    const y = pos.getY(i)
    if (Math.abs(Math.abs(y) - half) < 1e-6) {
      // pull the extreme faces in, so the silhouette reads as a chamfer
      pos.setX(i, pos.getX(i) * (1 - bevel))
      pos.setZ(i, pos.getZ(i) * (1 - bevel))
    }
  }
  geo.computeVertexNormals()
  return geo
}

export function createScene3D({ width = 960, height = 800, dark = true, cellH = 17 } = {}) {
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: false })
  renderer.setPixelRatio(1)
  renderer.setSize(width, height, false)
  renderer.setClearAlpha(0)

  const scene = new THREE.Scene()
  scene.fog = new THREE.Fog(dark ? 0x0e0c0b : 0xf4f1ea, 6, 15)

  const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 100)
  camera.position.set(0, 1.1, 6.2)
  camera.lookAt(0, 0, 0)

  // Two lights, doing different jobs: a warm key from above-left, a cold rim
  // from behind. The glyph ramp only sees luminance, so the separation between
  // them is what gives the object its edges.
  const key = new THREE.PointLight(dark ? 0xf2b25a : 0x8a5a1e, 46, 22, 2)
  key.position.set(-3.2, 3.4, 3.0)
  scene.add(key)

  const rim = new THREE.PointLight(dark ? 0x5fc9c2 : 0x2c625f, 30, 24, 2)
  rim.position.set(3.6, -1.6, -4.0)
  scene.add(rim)

  scene.add(new THREE.AmbientLight(dark ? 0x20242a : 0xb9b2a6, 0.9))

  const body = new THREE.Mesh(
    slab(3.0, 0.62, 2.0, 0.14),
    new THREE.MeshStandardMaterial({
      color: dark ? 0x2b2f33 : 0x6c7076,
      metalness: 0.72,
      roughness: 0.34,
      flatShading: true
    })
  )
  scene.add(body)

  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(2.05, 0.035, 3, 96),
    new THREE.MeshStandardMaterial({
      color: dark ? 0x3a4046 : 0x555b60,
      metalness: 0.85,
      roughness: 0.28
    })
  )
  ring.rotation.x = Math.PI / 2.35
  scene.add(ring)

  // resolution 2/cellH is what makes one output row equal one glyph cell:
  // AsciiEffect samples every second pixel row, and its font size is 2/res.
  const effect = new AsciiEffect(renderer, RAMP, {
    resolution: 2 / Math.max(8, cellH),
    scale: 1,
    color: true,
    alpha: true,
    invert: !dark,
    strResolution: 'low'
  })
  effect.setSize(width, height)

  const dom = effect.domElement
  dom.setAttribute('aria-hidden', 'true')
  dom.style.cssText = 'margin:0;padding:0;overflow:hidden;pointer-events:none;'
  const table = dom.querySelector('table')
  if (table) {
    table.style.margin = '0'
    table.style.padding = '0'
    table.style.borderCollapse = 'collapse'
  }
  const cell = dom.querySelector('td')
  if (cell) {
    cell.style.display = 'block'
    cell.style.width = width + 'px'
    cell.style.height = height + 'px'
    cell.style.overflow = 'hidden'
  }

  let frames = 0
  let disposed = false

  function render(dt, t = 0) {
    if (disposed) return
    body.rotation.y += dt * 0.22
    body.rotation.x = Math.sin(t * 0.17) * 0.12
    ring.rotation.z += dt * 0.09
    effect.render(scene, camera)
    frames++
  }

  function resize(w, h, cell = cellH) {
    if (disposed) return
    width = w
    height = h
    renderer.setSize(w, h, false)
    camera.aspect = w / h
    camera.updateProjectionMatrix()
    effect.setSize(w, h)
    const c = dom.querySelector('td')
    if (c) { c.style.width = w + 'px'; c.style.height = h + 'px' }
  }

  function dispose() {
    disposed = true
    try { body.geometry.dispose(); body.material.dispose() } catch (e) { /* already gone */ }
    try { ring.geometry.dispose(); ring.material.dispose() } catch (e) { /* already gone */ }
    try { renderer.dispose() } catch (e) { /* already gone */ }
    try { dom.remove() } catch (e) { /* already gone */ }
  }

  return { domElement: dom, render, resize, dispose, stats: () => ({ frames, mode: 'ascii3d' }) }
}
