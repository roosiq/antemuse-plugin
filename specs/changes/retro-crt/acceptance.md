# Acceptance — retro CRT

## Commands and results

| Check | Result |
| --- | --- |
| `pytest tests/` | **893 passed, 1 skipped** |
| `pytest tests/test_cockpit_pane.py` | **15 passed** |
| `tools/cockpit_harness.py` | **24/24 passed** |
| esbuild bundle | parsed |
| installed copy | byte-identical to `desktop/plugin.js` |

## Observed

- The field reads as sharp contacts on a phosphor tube: visible raster, bloom,
  vignette; the HUD is crisp monospace, evenly spaced, nothing clipped.
- Phosphor bloom on points and shots; amber only on picks and firing counts.
- Vignette at the rim, hairline frame inside it.

## Not done

- No pixelation of the world or the type. That was tried and reverted: retro is
  the display, not a low-resolution picture.
- No barrel/curvature warp of the raster (would need per-pixel remap each frame).
- No audio, no flicker or rolling-interlace animation (reduced-motion concerns).
- The DOM panels (`picked`, `net · N`) are terminal windows drawn as DOM text, so
  they sit outside the canvas effects (no bloom, no vignette).
