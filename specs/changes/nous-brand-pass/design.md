# Nous brand pass — design

## Token layer (`desktop/plugin.js`, before the cockpit)

```js
const BRAND = {
  blue:  '#0000f2',  // the ground
  deep:  '#00003c',  // far end of the ground gradient
  ink:   '#00001f',  // panels on the ground (the terminal block)
  paper: '#f2f2f2',  // type, hairlines, points
  dim:   '#a8a8ff',  // secondary type on blue
  neon:  '#79f200',  // one counterpoint, used sparingly
  yellow:'#f2f200',  // interest: pips, tracers, picks
  rule:  'rgba(242, 242, 242, 0.22)',
  veil:  'rgba(0, 0, 31, 0.92)'
}
const FONT = {
  display: '"Rules Gothic Condensed", "Bodoni Moda", Didot, "Liberation Serif", Georgia, serif',
  label:   '"Nimbus Sans Narrow", "Helvetica Neue", Arial, sans-serif',
  data:    'ui-monospace, SFMono-Regular, Menlo, monospace'
}
```

`PANEL`, `LABEL` and `DATA` compose those tokens once for the DOM; the canvas
composes the same tokens per draw. `cockpitTheme()` returns the brand surface and
takes nothing from the host — the deliberate exception to "theme variables only".

## Layout rules applied

| Element | Rule |
| --- | --- |
| Ground | flat `BRAND.blue`, no gradient — the brand's ground is one solid ink |
| Grain | deterministic 96px ink-speck tile, composited at 0.7; built once, so it does not boil |
| Points | ink marks: firing = filled paper dot + hairline ring; cold = hairline ring only; no shadow blur |
| Shots | plain paper dot, 4px, no tail or flare; slow travel (1.0 u/s); impact ring in yellow |
| Canopy / dash | `BRAND.ink` at 0.72 / 0.96, paper hairlines at 0.42 |
| Frame | four corner ticks, 10–18px, 7px inset, hairline |
| Wordmark | `Ψ` + `antemuse` in the display serif, lowercase, −0.01em; a hairline plate rule under it; `CONCEPT COCKPIT` right in tracked caps |
| HUD keys | `FONT.label`, 8px, tracking 0.26em, `BRAND.dim` |
| HUD values | `FONT.data`, 13px, tabular; paper except interest (yellow) |
| Heading tape | `FONT.data` 10px, tracking 0.1em; labels only when fully inside the tape |
| Points | paper for cold, `BRAND.yellow` for firing, `BRAND.dim` for the rest |
| Hit pips | yellow, `rr = r + 11`, ring plus one pip per hit, `×N` past one |
| Panels | `PANEL` + `DATA`, hairline `rule`, 2px corners, `LABEL` header |
| Status chip | label face, tracked, uppercase, host text colour retained |

## The grain

Flat colour plus a fixed grain tile is the whole difference between a device and a
screen. The tile is generated once from a seeded PRNG (xorshift, fixed seed), so
frames agree with each other; re-randomising every frame would produce television
static, which is the opposite of print.

## Legibility fixes that came out of review

- Concept labels flip to the left of a point when they would run off the glass,
  and are dropped if neither side fits. A half-cut label is a bug.
- Heading-tape numbers are suppressed within 20px of the tape edges: a clipped
  `010` reads as a broken instrument, not as a scale.
- `LIT` was renamed `FIRING` — the count is "how many concepts are firing now",
  and `LIT` was an in-joke, not a label.

## Guard rails (tests)

**Superseded.** The brand palette, and the guards that pinned it, were replaced by
`host-theme`: the pane reads the app's CSS variables now, so the token-collection and
palette-value tests named here no longer exist. The current guards are
`tests/test_cockpit_pane.py::test_the_cockpit_takes_its_colours_from_the_app_theme`,
`::test_alpha_is_derived_from_a_theme_colour_not_guessed` and
`::test_the_type_is_crisp_and_named`; `test_the_theme_names_every_colour_the_drawing_asks_for`
survived unchanged.

- `test_the_wordmark_appears_once_and_is_the_mark_plus_the_name` — `Ψ` via
  `String.fromCodePoint(0x3A8)`, `fillText('antemuse'` exactly once.
- `test_the_theme_names_every_colour_the_drawing_asks_for` — every `theme.*`
  reference must exist in what `cockpitTheme()` returns. This exists because
  `theme.paper` was missing and the shots silently inherited the last stroke
  colour, drawing yellow lasers rather than ink rules.

## Contrast

Paper `#f2f2f2` on blue `#0000f2` is ≈ 9:1; yellow `#f2f2f200` on the same ground
is ≈ 11:1; `BRAND.dim` (`#a8a8ff`) on blue is ≈ 4.4:1, used only for secondary
instrument keys at 8–10px with tracking, and mirrored in the DOM panels where the
ground is `BRAND.veil` (ink, 0.92) rather than blue.

## What did not change

- The map/activation pane's art ground and its 3D projection.
- Any route, payload field, or test-visible behaviour.
- The app's own chrome, theme, or fonts.
