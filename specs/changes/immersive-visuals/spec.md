# Full-pane visuals — the pane is the picture

Status: **proposed** 2026-11-08. Intent only; nothing implemented.
Owner: Ryan Cook. Scope: `dashboard/` + `desktop/plugin.js` rendering path in
`/home/ryan/antemuse-plugin`. Does not touch the lifecycle, the card, or the CLI.

## 1. Problem, measured

The state's art is a 44 × 12 glyph grid drawn at a fixed `fontSize: '10px'` and then
parked at the top of a scrolling column.

Measured in the running app (Xvfb boot, `GET /state`, CDP `getBoundingClientRect`):

| fact | value |
| --- | --- |
| pane | 700 × 746 px |
| frame | 44 cols × 12 rows = **528 cells** |
| rendered `<pre>` | ≈ 264 × 120 px (10 px monospace, glyph cell ≈ 6 × 10) |
| share of pane area | **≈ 4.4 %** |
| frames available per scene | 8 (`three_frames/<scene>/*.png`) |
| frames actually served | 1 (always `index=0`) |
| ramp | 8 levels, `" .:-=+*#"` |

So the picture is a postage stamp in the corner of a large empty rectangle, static,
single-tone, and stretched. Two causes, both in this repository:

1. **A hardcoded grid.** `dashboard/projection.py` sets `FRAME_COLS = 44`,
   `FRAME_ROWS = 12` and `plugin_api.py` passes them straight to
   `core.surfaces.art(cols=44, rows=12, index=0, …)`. The number is a chat-card
   width (`ART_ROWS` in `core/surfaces.py` is keyed by chat width: 40→8, 56→12,
   72→14). A desktop pane is not a chat card and was never sized like one.
2. **A renderer that only knows one frame.** `art()` already accepts `index` and
   the scenes already ship 8 frames each, but the route never asks for any but the
   first, so a scene that was authored as movement is served as a still.

`art(cols, rows, index, ramp, scene)` is already parametric, so this is not a call
for a new drawing engine. It is a call to *use the parameters*.

## 2. What "full pane" has to mean, numerically

The pane's capacity in glyph cells is a function of its pixel box and the cell size,
and the cell size is a function of the font. Those three numbers cannot be chosen
independently, so the pane negotiates instead of guessing:

- the surface measures itself (`ResizeObserver`) and asks for
  `GET /state?cols=<n>&rows=<n>`;
- the backend clamps to a declared envelope and echoes what it actually drew;
- the surface sizes the font so the returned grid exactly fills the box.

Capacity at real pane sizes, at a 8 × 14 px cell:

| box | cells | vs today |
| --- | --- | --- |
| 700 × 746 (pane, current window) | 87 × 53 = **4,611** | 8.7× |
| 420 × 746 (min-width pane) | 52 × 53 = 2,756 | 5.2× |
| 1600 × 1000 (page route, maximised) | 200 × 71 = 14,200 | 26.9× |

## 3. Proposal

### 3.0 Where the imagery comes from — owner direction, 2026-11-08

The sampler is not the weak part of the current picture. The **source** is. The
scenes are procedural diagrams assembled from primitives in `tools/scene.html`
(248 lines, no loader, no assets): a `PlaneGeometry` floor and path, a
`CapsuleGeometry` torso with a `SphereGeometry` head, a `Points` dust cloud, planes
standing in for feed posts. Rendered at 44 × 12 that reads as a mood. Rendered at
4,611 cells it reads as exactly what it is — a diagram of a person, not a person.

Owner direction, therefore: **the pictures are real imagery — 2D or 3D, authored in
Meshy — rendered through three.js and converted to ASCII.** The conversion path
already exists in this repository and does not need replacing:

- `tools/render_three.py` bakes 8 frames per state by screenshotting
  `tools/scene.html?scene=<s>&f=<i>&n=8` in headless Chromium
  (`--use-angle=swiftshader --window-size=1600,420 --virtual-time-budget=8000`);
- `tools/term_scene.cjs` renders three.js to half-block truecolour in a terminal
  through `three-software-renderer`, with an 8 × 8 Bayer dissolve between scenes;
- the scene clock is already frame-indexed (`t = (F / N) * 2π`, one seamless loop),
  which is what a loopable bake needs.

What is missing is the assets and a loader. Three additions:

1. **An asset pack with provenance.** Assets land under `data/meshy/` (or
   `data/real/` for the existing SD route) with a manifest beside them:
   provider, prompt, date, licence, sha256, and for meshes the triangle count.
   `data/collider/ATTRIBUTION.md` is the pattern to copy.
2. **A loader in the scene.** `GLTFLoader` for 3D assets; for 2D, a textured
   billboard at a declared depth, which is cheaper, deterministic, and — at 4,611
   cells of luminance ramp — visually indistinguishable from a mesh for anything
   further away than the camera's near plane. States may mix the two.
3. **A seeded bake.** `tools/scene.html:186` calls `Math.random()` for dust
   positions, so a re-bake is not reproducible today. Randomness must come from a
   seeded PRNG keyed on the bake, or a frame cannot be re-made, compared, or
   blamed.

Bake keys are therefore `(asset-pack hash, scene id, frame index, cols, rows, ramp,
dither)`. A size change is a new bake, not a resample of an old one.

**Availability, stated plainly:** the Meshy CLI is **not installed** here
(`npm exec --yes --package=meshy-cli@0.4.3 -- meshy …`), and every generation is a
paid operation needing authorization and a credit balance. The 2D route is usable
today (local SD server, `tools/gen_frames.py`); the 3D route needs an install and a
spend decision from the owner.

Five changes to the surface itself, in dependency order — on top of the source fix
in 3.0. Each is small; together they are the difference between a thumbnail and a
surface.

### 3.1 Size negotiation instead of a constant

`projection.project()` takes `cols`/`rows` and echoes them in `payload.frame`.
`plugin_api.state()` accepts `cols`/`rows` query parameters, clamped to
`MIN = 24 × 8`, `MAX = 200 × 80`, defaulting to today's 44 × 12 so the chat-facing
behaviour and every existing test stay identical. An out-of-range or non-integer
request is clamped and reported, never silently resized.

The desktop half measures its own box, converts to cells using the same metrics it
will use to draw, and re-asks only when the box changes by more than one cell in
either axis (so a window drag does not hammer the route).

### 3.2 Cell-aspect correction

A glyph cell is taller than it is wide (≈ 6 × 10 px, ratio 0.6). Today `art()`
resizes the source image straight to `(cols, rows)`, which is correct only when
`cols/rows` happens to equal the source aspect divided by 0.6 — at 44 × 12 it is
not, so the picture is horizontally stretched by ≈ 2.2× on top of everything else.
At 528 cells nobody notices. At 4,611 cells a stretched circle is the first thing a
person sees.

The sampler must work in *pixel* space: choose the sub-rectangle of the source that
matches `cols × cell_w : rows × cell_h`, crop it (cover) or fit it (contain), and
only then downsample. This is a coordinate fix inside `art()`, not a new renderer.

### 3.3 A frame strip, looped on the surface

The backend returns `frames: [lines, …]` (up to 8, one per authored PNG) and the
surface loops them at a per-state cadence. This is the only way to get movement
without a socket, without a second renderer, and without a model call: the pixels
are baked once per size, then cycled.

Cadence is data, not taste — declared per state, defaulting to a small table, and
clamped so a slow state cannot look like a shimmer and a fast one cannot strobe.
The loop pauses when the pane is hidden (`document.hidden`) and when the theme asks
for reduced motion, in which case a single deterministic frame is shown.

### 3.4 Tone that survives magnification

At 528 cells an 8-step ramp reads as texture. At 4,611 cells it reads as banding:
large flat regions of `=`, visible contour steps, and glyphs whose density no longer
matches the source luminance they are standing in for.

- Ordered (Bayer 4 × 4) dithering between adjacent ramp levels, applied in the
  sampler, so gradients stay smooth at any cell count and the ramp stays 8 glyphs.
- One hue per state, chosen from the state's own identity, applied as a CSS colour
  on the `<pre>` — the glyphs stay monochrome, the surface stops being grey soup.
- A contrast floor: the brightest run against the pane background ≥ 4.5:1 in both
  light and dark themes, checked in test rather than by eye.

### 3.5 Immersive layout

The pane stops being a column of labels with a picture in it and becomes the
picture with a HUD in the corner:

- art on a zero-padding, zero-gap, `overflow: hidden` box at `height: 100%`;
- label, counts and contract collapse into one 11 px line at ≈ 55 % opacity,
  bottom-left, which fades out after ~10 s of no state change and returns on hover
  or focus;
- no scrollbar in the pane, ever;
- the page route (`/antemuse`) gets the same treatment at window size, which is the
  "immersive" case proper: 14,200 cells.

## 4. Acceptance (when implemented)

Measured in the app on Xvfb, not asserted from the source:

1. At a 700 × 746 pane the art's bounding box is ≥ 90 % of pane width and ≥ 85 % of
   pane height (today: 38 % × 16 %).
2. `payload.frame.cols × rows` ≥ 3,000 at that box, and the echo proves the grid was
   negotiated rather than defaulted.
3. A known-circular region of a scene stays within ±5 % of circular after sampling
   (unit test on the aspect math, at three different `cols/rows` pairs).
4. The strip moves: consecutive frames differ, ≤ 8 frames, payload ≤ 256 KB.
5. Reduced motion yields one deterministic frame; hidden pane issues no repaints.
6. Contrast ≥ 4.5:1 for the brightest glyph run, light and dark themes.
7. No scrollbar, no clipping, no layout shift when counts tick over.
8. Idle still says `no state` and draws nothing — no invented scene, no placeholder.
9. `card()` and `test_card_is_only_a_picture` unchanged; the full suite stays green;
   doctor still reports `1 tool(s), 8 hook(s)`.
10. Screenshots at pane size and at page size, both with a live state.
11. Every served frame traces to a manifest entry — provider, prompt, date, licence,
    sha256 — and a missing asset fails loudly rather than falling back to a diagram.
12. Two bakes of the same pack produce byte-identical glyphs (seeded randomness; the
    current `Math.random()` in `scene.html` fails this today).
13. The client does no WebGL and no per-frame image work: the pane's payload is text.
14. A 3D asset survives the pipeline recognisably — a turntable test with a known
    subject still reads as that subject at 4,611 cells.

## 5. Non-goals

- No second renderer. Python still owns the glyphs; JavaScript still displays text.
  The surface chooses *size* and *which frame*; it samples nothing.
- No image, video or canvas fallback. The medium stays ASCII.
- No WebGL in the client. three.js runs at bake time only; a pane never opens a
  GL context.
- No change to `card()`, and none to BR-5: the chat card stays a picture with no
  words in it. The HUD is pane furniture, not a caption on the card.
- No claim about creative quality. Framing is presentation.
- No new dependency; the sampler stays Pillow + stdlib.

## 6. Must not change (spec §18)

Four-state lifecycle, durations, turn budgets, cadences, tool policy, directives,
contracts, residue labels, journal cap 60, residue cap 3, two-turn report decay, hook
contracts, `/return`, `CONTROL_TOOLS`. Entry, exit, expiry and rendering never
require a model. A missing scene still renders nothing and says so.

## 7. Open decisions (owner)

1. **Colour or monochrome?** A per-state hue is proposed above; the alternative is
   one ink for all states and identity carried only by the scene.
2. **Crop or fit?** Covering the pane loses scene edges at narrow widths; containing
   leaves letterbox bands. Proposal: cover above 3:2, contain below.
3. **Where does the immersive case live?** Pane only, or does `/antemuse` become a
   full-window art page (my reading of "full pane, immersive" is both).
4. **Meshy spend.** Generating assets is paid and needs authorization per pack —
   roughly one pack per state, five states. Until then the 2D route (local SD
   server) is the only source that can be exercised without spending.
5. **Mesh or billboard per state?** 3D meshes cost generation, load time and a
   loader; textured 2D billboards cost almost nothing and look the same once
   luminance-quantised. Proposal: meshes only where the camera moves past the
   subject (walk, doomscroll); billboards where the subject is seen once.

Approval of this intent is gate 1; the plan and tasks come after, and only then code.
