# Scene renderer — 3D straight to terminal pixels

Status: **proposed** 2026-11-08. Not implemented. Written from a working prototype,
not from a sketch.
Owner: Ryan Cook. Scope: `/home/ryan/antemuse/plugin` rendering only.

## 1. Problem

The chat card is one of eight cached PNG screenshots, cropped to the central
60%×76% of a 1600×420 frame, resized to 40×8 cells, and painted as text. At that
size a scene's geometry falls below one cell per feature: the walk's floor, path
edges and perspective all vanish, leaving the point trail and the ring. §14.15
made that visible by fixing the luminance ramp; it cannot put back what the
sampling threw away.

The cost is on both sides. Producing frames needs a static server, headless
Chromium with SwiftShader, and ~0.7 s per frame (8 frames × 5 scenes per
regeneration), and the result is ~500 KB of assets per scene bank that must be
shipped with the plugin.

## 2. Proposal

Render the scene in Python at the resolution the destination actually has,
instead of downsampling a photograph of it.

- `core/scene3d.py`: a deterministic software renderer with no third-party
  dependency — camera basis, perspective projection, painter's/z-buffer depth,
  distance fog, and a luminance accumulation buffer.
- Scene primitives mirror what `tools/scene.html` already draws: ground grid,
  luminous path plane, point trail, torus, and the per-state camera.
- Output packing per surface:
  - **terminal takeover** — truecolor half-blocks (`▀`, upper pixel as
    foreground, lower as background), which the TUI already speaks;
  - **chat card** — braille (U+2800–U+28FF), 2×4 addressable dots per cell,
    monochrome, no escape codes, still wordless under BR-5;
  - **PNG attachment** — the same buffer at full size, drawn as pixels rather
    than as text.
- `art()` gains a renderer choice: live scene, or the legacy frame bank. The
  default stays the frame bank until the live renderer is proven on both
  surfaces.

## 3. Prototype evidence (2026-11-08)

The walk scene, projected in Python with a z-buffer and packed 2×4 into braille:
**80×24 cells = 160×96 addressable dots**, rendered in **24 ms**, stdlib only, no
browser, no PNG bank, deterministic for a given camera. The corridor, the ring
and the trail were all legible; at 40×8 the same frame carried two of the five
features.

Prototype lived in scratch and is now `tools/scene3d_probe.py` — evidence that the
approach works, not an implementation.

## 4. Acceptance (when implemented)

1. No browser, no static server, and no Chromium invocation anywhere in the
   render path; `tools/render_three.py` either deleted or demoted to an
   optional exporter for the PNG bank.
2. `pytest tests/ -q` green; doctor unchanged in tool and hook counts.
3. The chat card renders a walk with the corridor's two path edges, the ring,
   and the trail distinguishable at the `discord` profile's 40 columns — judged
   by a test that asserts feature-level luminance peaks, not by eyeballing.
4. Rendering is deterministic: the same scene, camera, and frame index produce
   byte-identical cells, and there is no dependence on the previous frame.
5. No model call, no network, no sixel/kitty dependency; entry, exit, expiry,
   and `/return` stay inference-free.
6. The card remains wordless (BR-5) and carries no ANSI escapes.

## 5. Open decisions

- **Source of truth.** Port the scene definitions to Python and retire
  `tools/scene.html` + `three_frames/`, or keep the JS authoritative and accept
  that the live renderer is a second implementation that can drift. Recommendation:
  port, because two renderers of the same scene will diverge and the JS one costs
  a browser to run.
- **Chat glyph set.** Braille gives 8× the addressable resolution of the ramp but
  is monochrome and needs U+28xx coverage; block characters (`▁▂▃▄▅▆▇█`) give a
  continuous ramp at 1× resolution and are safer everywhere. Braille is the better
  picture; the ramp is the safer one. Needs a decision, not a default.
- **Aspect.** A 40×8 card is 5:1; a scene composed at 5:1 will not look like the
  same place at 4:5 postcard size. The `scenes-per-surface` proposal already asks
  for two crops; this renderer makes that cheap (two cameras, not two assets).

## 6. Non-goals

- No sixel, kitty graphics protocol, or image-in-terminal dependency.
- No live animation in chat surfaces, and no change to the terminal takeover's
  existing motion grammar.
- No model-generated imagery, no fetched imagery: the scene stays synthetic and
  deterministic.
- No change to state definitions, tool policy, journal, residue, or `/return`.

## 7. Affected paths (planned)

`core/scene3d.py` (new), `core/surfaces.py`, `core/tui.py`, `tests/test_scene3d.py`
(new), `tests/test_surfaces.py`, `tools/render_three.py` (retire or demote),
`tools/scene.html` + `three_frames/` (if the port goes ahead), `docs/spec.md` §17.
`tools/scene3d_probe.py` already exists as the measurement this proposal rests on.
