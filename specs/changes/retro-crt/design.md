# Design — retro CRT

## Palette

One token block, `BRAND`, is the only place a colour literal may appear.

| Token | Value | Use |
| --- | --- | --- |
| `screen` | `#050a05` | the lit tube, not pure black |
| `ink` | `#000000` | panels, raster lines |
| `phosphor` | `#3bff6e` | type, points, shots |
| `amber` | `#ffb000` | interest: pips, picks, impact |
| `dim` | `#2ecc5a` | labels, cold rings |
| `rule` | `rgba(59,255,110,0.30)` | hairlines |
| `veil` | `rgba(1,8,3,0.90)` | DOM panel ground |
| `tubeClear` / `tubeEdge` | transparent → `rgba(0,0,0,0.55)` | vignette |
| `frameEdge` | `rgba(59,255,110,0.12)` | inner frame |
| `glow` | `rgba(59,255,110,0.08)` | panel inner wash |

## Raster

`drawGrain` builds one 96px tile: phosphor speckle plus a dark line every third
row at 0.10 alpha. Built once so frames do not boil. Composited at 0.85.

That is the whole raster treatment. There is no downsampling: a vector monitor
draws clean strokes, and pixelating the world made the readouts worse without
buying any authenticity.

## Type

One monospace family in three roles (`display`, `label`, `data`), set at full
resolution: caps, wide tracking, tabular figures. Arcade cabinets did not have a
type system, but they did have sharp glyphs — the retro comes from the tube, not
from a character ROM.

Readouts are measured with `measureText` and trimmed to `cellW - 10`, so a value
never runs into its neighbour.

## Bloom

Points and shots carry `shadowBlur = 10` in phosphor. On a tube a bright dot
blooms; that is the medium rather than decoration, which is why bloom is allowed
here after being removed in the brand pass.

## Tube

`drawTube(w, h)` paints a radial falloff from transparent centre to
`rgba(0,0,0,0.55)` at the rim, plus a one-pixel inner frame. Drawn last, so the
chrome sits inside the glass.
