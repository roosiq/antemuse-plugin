#!/usr/bin/env node
/*
 * three.js in the terminal, for real.
 *
 *   node tools/term_scene.cjs --scene walk --cols 100 --rows 26 --fps 12
 *   node tools/term_scene.cjs --watch /path/scene.json     (live switching)
 *   node tools/term_scene.cjs --scene walk --ppm out.ppm    (one frame, pixels)
 *   node tools/term_scene.cjs --scene walk --debug          (lit-pixel check)
 *
 * The software rasteriser draws into a pixel buffer; every cell becomes `▀`
 * with the top pixel as foreground and the bottom as background — two pixels
 * per cell, truecolour. A scene change renders both scenes and dissolves
 * through an 8x8 Bayer threshold.
 *
 * Two things this renderer cannot do, learned the hard way: LineSegments makes
 * it drop the entire scene (so floor lines are thin planes), and a large
 * transparent shell in front of a object hides it completely.
 */
'use strict'

const path = require('path')
const fs = require('fs')
const ROOT = path.join(__dirname, '..', 'node_modules')
const THREE = require(path.join(ROOT, 'three'))
const SoftwareRenderer = require(path.join(ROOT, 'three-software-renderer'))

const argv = process.argv.slice(2)
const flag = (name, fallback) => {
  const i = argv.indexOf('--' + name)
  return i >= 0 && argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : fallback
}
const has = (name) => argv.includes('--' + name)

const SCENE = flag('scene', 'walk')
const COLS = parseInt(flag('cols', '100'), 10)
const ROWS = parseInt(flag('rows', '26'), 10)
const FPS = parseFloat(flag('fps', '12'))
const WATCH = flag('watch', '')
const PPM = flag('ppm', '')
const AT = parseFloat(flag('t', '0'))

const BAYER = [
  [0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
  [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
  [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
  [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]
]

function makeStage() {
  const renderer = new SoftwareRenderer({ alpha: false })
  renderer.setSize(COLS, ROWS * 2)
  return {
    renderer,
    scene: new THREE.Scene(),
    camera: new THREE.PerspectiveCamera(45, COLS / (ROWS * 2), 0.1, 200)
  }
}

function light(stage, hex, intensity, x, y, z, dist) {
  const l = new THREE.PointLight(hex, intensity, dist || 80)
  l.position.set(x, y, z)
  stage.scene.add(l)
  return l
}

function bg(stage, hex) {
  stage.scene.background = new THREE.Color(hex)
  stage.renderer.setClearColor(new THREE.Color(hex))
}

function floor(stage, colour, railColour, span) {
  const plane = new THREE.Mesh(
    new THREE.PlaneGeometry(span, span),
    new THREE.MeshBasicMaterial({ color: colour })
  )
  plane.rotation.x = -Math.PI / 2
  stage.scene.add(plane)

  const mat = new THREE.MeshBasicMaterial({ color: railColour })
  for (let x = -24; x <= 24; x += 4) {
    const rail = new THREE.Mesh(new THREE.PlaneGeometry(0.28, span * 0.7), mat)
    rail.rotation.x = -Math.PI / 2
    rail.position.set(x, 0.02, -14)
    stage.scene.add(rail)
  }
  for (let z = -40; z <= 10; z += 4) {
    const rail = new THREE.Mesh(new THREE.PlaneGeometry(48, 0.28), mat)
    rail.rotation.x = -Math.PI / 2
    rail.position.set(0, 0.02, z)
    stage.scene.add(rail)
  }
}

const scenes = {}

scenes.walk = (stage, t) => {
  bg(stage, 0x14202a)
  stage.scene.fog = new THREE.Fog(0x14202a, 18, 70)
  const s = stage.scene
  s.add(new THREE.AmbientLight(0x5a6c78))
  light(stage, 0xe8a33d, 1.6, 0, 6, -10, 90)
  light(stage, 0x9fd8cf, 1.0, -6, 6, 8, 60)

  floor(stage, 0x16323a, 0x4fa89c, 90)

  const sunMat = new THREE.MeshBasicMaterial({ color: 0xffd48f })
  sunMat.fog = false
  const sun = new THREE.Mesh(new THREE.SphereGeometry(3.1, 24, 16), sunMat)
  sun.position.set(0, 5.2, -9)
  s.add(sun)

  const dark = new THREE.MeshLambertMaterial({ color: 0x0b141a })
  const figure = new THREE.Group()
  const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.22, 0.66, 12), dark)
  torso.position.y = 1.02
  figure.add(torso)
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.15, 12, 10), dark)
  head.position.y = 1.46
  figure.add(head)
  const legL = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.05, 0.56, 8), dark)
  const legR = legL.clone()
  legL.position.set(-0.09, 0.36, 0)
  legR.position.set(0.09, 0.36, 0)
  figure.add(legL, legR)
  const armL = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.04, 0.46, 8), dark)
  const armR = armL.clone()
  armL.position.set(-0.23, 1.08, 0)
  armR.position.set(0.23, 1.08, 0)
  figure.add(armL, armR)

  const swing = Math.sin(t * 2.2) * 0.5
  legL.rotation.x = swing
  legR.rotation.x = -swing
  armL.rotation.x = -swing * 0.6
  armR.rotation.x = swing * 0.6
  figure.position.set(0, Math.abs(Math.sin(t * 2.2)) * 0.03, 3.4)
  s.add(figure)

  stage.camera.position.set(Math.sin(t * 0.4) * 0.25, 1.8, 6.1)
  stage.camera.lookAt(0, 2.3, -6)
}

scenes.daydream = (stage, t) => {
  bg(stage, 0x1a121c)
  stage.scene.fog = new THREE.Fog(0x1a121c, 12, 46)
  const s = stage.scene
  s.add(new THREE.AmbientLight(0x6b5876))
  light(stage, 0xd79ac0, 1.2, 2, 3, 3, 60)
  light(stage, 0x7fb2c9, 1.0, -4, -1, 2, 60)

  for (let i = 0; i < 7; i++) {
    const geo = i % 2
      ? new THREE.IcosahedronGeometry(0.55 + (i % 3) * 0.2, 0)
      : new THREE.OctahedronGeometry(0.5 + (i % 4) * 0.16, 0)
    const m = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({
      color: i % 2 ? 0xf0d6e8 : 0xa7d8e0
    }))
    m.position.set(Math.sin(i + t * 0.5) * 1.8, Math.cos(i * 1.7 + t * 0.6) * 1.1, 0.4 - i * 0.85)
    m.rotation.set(t * 0.4 + i, t * 0.3, 0)
    s.add(m)
  }
  stage.camera.position.set(0, 0.3, 4.4)
  stage.camera.lookAt(0, 0, -3)
}

scenes.dream = (stage, t) => {
  bg(stage, 0x120d1e)
  stage.scene.fog = new THREE.Fog(0x120d1e, 10, 40)
  const s = stage.scene
  s.add(new THREE.AmbientLight(0x4b4468))
  light(stage, 0x9f8fe8, 1.4, 0, 2, 5, 60)
  light(stage, 0xe8a33d, 0.8, 3, -1, -3, 60)

  const a = new THREE.Mesh(new THREE.SphereGeometry(1.35, 22, 16),
    new THREE.MeshLambertMaterial({ color: 0x8f7fe0 }))
  const b = new THREE.Mesh(new THREE.SphereGeometry(1.0, 20, 14),
    new THREE.MeshLambertMaterial({ color: 0xe0b078 }))
  const sep = 1.6 + Math.sin(t * 0.8) * 0.9
  a.position.set(-sep * 0.55, 0.1, 0.6)
  b.position.set(sep * 0.55, Math.sin(t * 0.6) * 0.3, 0.1)
  s.add(a, b)

  for (let i = 0; i < 26; i++) {
    const d = new THREE.Mesh(new THREE.SphereGeometry(0.05, 6, 5),
      new THREE.MeshBasicMaterial({ color: 0xcfc4f0 }))
    d.position.set(Math.sin(i * 13.1 + t) * 2.6, Math.cos(i * 7.7 + t * 0.6) * 1.4, -1 - (i % 6) * 0.6)
    s.add(d)
  }
  stage.camera.position.set(0, 0.2, 4.6)
  stage.camera.lookAt(0, 0, -2)
}

scenes.doomscroll = (stage, t) => {
  bg(stage, 0x1a0f0b)
  stage.scene.fog = new THREE.Fog(0x1a0f0b, 8, 34)
  const s = stage.scene
  s.add(new THREE.AmbientLight(0x6b4436))
  light(stage, 0xd2603f, 1.3, 0, 2, 6, 60)

  const speed = 1.0 + (Math.sin(t) * 0.5 + 0.5) * 1.6
  for (let i = 0; i < 10; i++) {
    const card = new THREE.Group()
    card.add(new THREE.Mesh(new THREE.PlaneGeometry(3.0, 1.9),
      new THREE.MeshLambertMaterial({ color: 0x2a1813 })))
    const hdr = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 0.2),
      new THREE.MeshBasicMaterial({ color: 0xf0b45e }))
    hdr.position.set(-0.3, 0.66, 0.02)
    card.add(hdr)
    for (let r = 0; r < 4; r++) {
      const w = 1.4 + ((i * 3 + r * 7) % 8) * 0.16
      const line = new THREE.Mesh(new THREE.PlaneGeometry(w, 0.1),
        new THREE.MeshBasicMaterial({ color: 0xe8cdbd }))
      line.position.set(-0.3 + (2.2 - w) * 0.5 - 1.1 + w / 2, 0.34 - r * 0.24, 0.02)
      card.add(line)
    }
    const z = ((i * 1.9 - t * speed * 2.4) % 18 + 18) % 18
    card.position.set(0, 0, -z + 1.5)
    card.rotation.y = Math.sin(i * 2.1) * 0.05
    card.scale.setScalar(0.55 + Math.max(0.1, 1 - z / 18) * 0.85)
    s.add(card)
  }
  stage.camera.position.set(0, 0, 5.0)
  stage.camera.lookAt(0, 0, -5)
}

function renderStage(stage, name, t) {
  while (stage.scene.children.length) stage.scene.remove(stage.scene.children[0])
  stage.scene.fog = null
  ;(scenes[name] || scenes.walk)(stage, t)
  stage.scene.updateMatrixWorld(true)
  stage.camera.updateMatrixWorld(true)
  stage.camera.updateProjectionMatrix()
  return stage.renderer.render(stage.scene, stage.camera)
}

function mix(a, b, t) {
  if (t <= 0) return a
  if (t >= 1) return b
  const data = new Uint8ClampedArray(b.data.length)
  const width = b.width
  for (let i = 0, p = 0; i < b.data.length; i += 4, p++) {
    const x = p % width
    const y = (p / width) | 0
    const src = BAYER[y % 8][x % 8] / 64 < t ? b.data : a.data
    data[i] = src[i]; data[i + 1] = src[i + 1]; data[i + 2] = src[i + 2]; data[i + 3] = 255
  }
  return { data, width: b.width, height: b.height }
}

function toAnsi(image) {
  const { data, width, height } = image
  const out = []
  for (let y = 0; y < height; y += 2) {
    let line = ''
    for (let x = 0; x < width; x++) {
      const top = (y * width + x) * 4
      const bot = ((y + 1) * width + x) * 4
      line += `\x1b[38;2;${data[top]};${data[top + 1]};${data[top + 2]}m` +
              `\x1b[48;2;${data[bot]};${data[bot + 1]};${data[bot + 2]}m▀`
    }
    out.push(line + '\x1b[0m')
  }
  return out.join('\n')
}

const stageA = makeStage()
const stageB = makeStage()

if (PPM) {
  const image = renderStage(stageA, SCENE, AT)
  const header = Buffer.from(`P6\n${image.width} ${image.height}\n255\n`)
  const body = Buffer.alloc(image.width * image.height * 3)
  for (let i = 0, j = 0; i < image.width * image.height * 4; i += 4, j += 3) {
    body[j] = image.data[i]; body[j + 1] = image.data[i + 1]; body[j + 2] = image.data[i + 2]
  }
  fs.writeFileSync(PPM, Buffer.concat([header, body]))
  process.exit(0)
}

if (has('debug')) {
  const image = renderStage(stageA, SCENE, AT)
  let lit = 0
  for (let i = 0; i < image.data.length; i += 4) {
    if (image.data[i] + image.data[i + 1] + image.data[i + 2] > 150) lit++
  }
  console.error(`${SCENE} ${image.width}x${image.height} lit=${lit}`)
  process.exit(0)
}

let current = SCENE
let fading = null
const started = Date.now()
const FADE_MS = 900

const readWatch = () => {
  if (!WATCH) return current
  try {
    return JSON.parse(fs.readFileSync(WATCH, 'utf8')).scene || current
  } catch (e) {
    return current
  }
}

const finish = () => {
  process.stdout.write('\x1b[0m\x1b[?25h')
  process.exit(0)
}
process.on('SIGINT', finish)
process.on('SIGTERM', finish)

process.stdout.write('\x1b[?25l')
let lastWatch = 0

function loop() {
  const now = Date.now()
  const t = ((now - started) / 1000) * 1.1

  if (WATCH && now - lastWatch > 150) {
    lastWatch = now
    const want = readWatch()
    if (want !== current) {
      fading = { name: current, started: now }
      current = want
    }
  }

  let image = renderStage(stageA, current, t)
  if (fading) {
    const p = (now - fading.started) / FADE_MS
    if (p >= 1) {
      fading = null
    } else {
      image = mix(renderStage(stageB, fading.name, t), image, p)
    }
  }

  process.stdout.write('\x1b[H' + toAnsi(image) + '\x1b[0m')
  setTimeout(loop, 1000 / FPS)
}

loop()
