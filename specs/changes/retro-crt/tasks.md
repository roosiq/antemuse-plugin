# Tasks — retro CRT

## T1 — Palette

**Superseded by `host-theme`.** The phosphor palette this task installed was replaced by
the host's own CSS variables. The CRT *treatment* (grain, scanlines, tube vignette) is
what survived, because it is display, not colour.
- [x] Replace the Nous tokens with tube / phosphor / amber tokens
- [x] Theme exposes every token the drawing asks for (`tubeClear`, `tubeEdge`,
      `frameEdge`, `glow`, `phosphor`)
- Evidence: `test_the_theme_names_every_colour_the_drawing_asks_for` (survived the theme
  pass). The palette-value guards were replaced by `host-theme`: the pane reads the app's
  variables now, so there is no plugin-owned palette left to assert.

## T2 — Raster (tube, not pixel art)
- [x] Phosphor speckle + scanlines baked into the grain tile
- [x] Tube vignette and inner frame drawn last
- [x] **No** downsampling of the world: pixelation rejected and reverted
- Evidence: stills from `tools/cockpit_video.py`; no page errors in the harness

## T3 — Type
- [x] One monospace family in three named roles, drawn at full resolution
- [x] HUD cells trimmed to `cellW - 10` so values never overlap
- [x] Wordmark `Ψ ANTEMUSE` in tracked caps
- Evidence: `test_the_type_is_crisp_and_named`,
  `test_the_wordmark_appears_once_and_is_the_mark_plus_the_name`

## T4 — Behaviour unchanged
- [x] Flight, net, hold-to-fire, picks still pass
- Evidence: harness 24/24, pane guards 15/15, suite 893 passed / 1 skipped
