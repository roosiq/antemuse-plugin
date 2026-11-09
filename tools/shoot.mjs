/**
 * Render pages in headless Chromium and save screenshots — one browser for the whole batch.
 *
 *   node tools/shoot.mjs <out.png> <url> [<out2.png> <url2> ...]
 *
 * Bake time only: the plugin never imports three.js, and nothing here ships to a surface.
 * Playwright is the reliable launcher on this box — the distro `chromium-browser` exits silently.
 */
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)

const CANDIDATES = [
  '/home/ryan/.hermes/hermes-agent/node_modules/playwright',
  'playwright'
]

let chromium = null
for (const candidate of CANDIDATES) {
  try {
    const mod = require(candidate)
    chromium = mod.chromium || (mod.default && mod.default.chromium)
    if (chromium) break
  } catch (e) { /* try the next */ }
}
if (!chromium) {
  console.error('shoot: no playwright available')
  process.exit(3)
}

const pairs = []
const argv = process.argv.slice(2)
for (let i = 0; i + 1 < argv.length; i += 2) pairs.push({ out: argv[i], url: argv[i + 1] })
if (!pairs.length) {
  console.error('shoot: nothing to do')
  process.exit(4)
}

;(async () => {
  const browser = await chromium.launch({
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox']
  })
  let failed = 0
  try {
    for (const { out, url } of pairs) {
      const size = new URL(url).searchParams
      const w = parseInt(size.get('w') || '960', 10)
      const h = parseInt(size.get('h') || '600', 10)
      const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 })
      const errors = []
      page.on('pageerror', (e) => errors.push(e.message))
      page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
      try {
        await page.goto(url, { waitUntil: 'load' })
        await page.waitForFunction(
          () => document.title === 'ready' || document.title.startsWith('error'),
          null, { timeout: 30000 }
        ).catch(() => {})
        const title = await page.title()
        if (title !== 'ready') throw new Error('page said ' + title + ' ' + errors.join(' | '))
        await page.screenshot({ path: out })
      } catch (e) {
        failed += 1
        console.error('shoot: ' + out + ' failed · ' + ((e && e.message) || e))
      } finally {
        await page.close().catch(() => {})
      }
    }
  } finally {
    await browser.close()
  }
  process.exit(failed ? 1 : 0)
})()
