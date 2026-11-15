# Design — host theme

## Reading the theme

`cockpitTheme(el, doc, win)` runs once per mount. The app declares many tokens as
`color-mix(...)`, and `getComputedStyle().getPropertyValue()` hands those back
**unresolved**, so the value cannot be parsed or alpha-adjusted.

Instead it resolves them the way the browser would: attach an off-screen probe
`span`, set `color: var(--token, rgb(1, 1, 1))`, and read the computed `color`.
The grey sentinel identifies a token that does not exist, which lets the lookup
fall through the preference list:

| Theme key | Preference order |
| --- | --- |
| `glass` | `--ui-panel-background`, `--ui-background` |
| `text` | `--ui-text`, `--ui-text-secondary` |
| `dim` | `--ui-text-secondary`, `--ui-text` (at 0.6 alpha) |
| `stroke` | `--ui-stroke-secondary`, `--ui-stroke` |
| `accent` | `--ui-accent` |
| `ink` | `--ui-panel-background`, `--ui-background` |

The probe is removed before return.

## Alpha

`withAlpha(colour, a)` parses `#rgb`, `#rrggbb`, `rgb()` and `rgba()` into an
`rgba(...)` string. A `var()` is a colour reference, not a string you can append
hex alpha to.

## What stays literal

- `#000000` raster lines and the black vignette: the tube is hardware.
- `#ffffff` / `#000000` fallbacks, used only when the host exposes nothing.

Everything else is theme-derived, and the colour guard fails the build on any
chromatic literal in the cockpit block.

## Texture on a themed ground

Grain composites at 0.5 and scanlines at 0.08 — enough to read as a CRT, light
enough that a themed panel background still looks like the app.
