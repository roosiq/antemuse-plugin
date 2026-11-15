# Design system

The values both panes draw with. Everything here is derived from `desktop/plugin.js`; if this
document and the code disagree, the code is wrong and this document says what it should be.

## Voice

How the product speaks is a design surface, not a copywriting afterthought. The rules — promise
first, mechanism second, one plain caveat, counts over adjectives — live in
`specs/product/positioning.md`, and the worked examples in `specs/product/examples.md` are generated
from the engine rather than written, so the panes, the README and the marketplace cannot disagree
about what a state does.

## Colour

The pane has no palette of its own. Every colour is a CSS variable belonging to the desktop
app, read through `cockpitTheme()` with a fallback chain, so a light theme, a different accent
or a future redesign reaches the panes without a release.

| Role | First choice | Fallbacks | Used for |
| --- | --- | --- | --- |
| `accent` | `--ui-accent` | — | firing, picks, the `EDGE` warning, the reticle when hot |
| `text` | `--ui-text` | `--foreground`, `--color-foreground`, `--ui-text-secondary` | values, labels on the glass |
| `dim` | `--ui-text-secondary` | `--muted-foreground`, `--color-muted-foreground`, `--ui-text` | HUD labels, secondary lines |
| `stroke` | `--ui-stroke-secondary` | `--ui-stroke`, `--border`, `--color-border` | hairlines, frames, the horizon |
| `glass` | `--ui-panel-background` | `--ui-background`, `--background`, `--sidebar` | the tube's ground, the dash |

Rules:

- **No hue literals in the pane.** Naturals are permitted only for the tube itself
  (`rgba(0,0,0,…)` vignette, neutral grey grain). A coloured literal is a second product.
- **Never stroke a hairline in `stroke` and then multiply alpha onto it.** Two of the map's
  boundary lines rendered nothing for exactly this reason: `--ui-stroke-secondary` is already
  a translucent `color-mix`, so `alpha × already-alpha` vanished. Hairlines that must be seen
  are drawn in `text` at low alpha.
- **Unresolved tokens keep the previous value.** Assigning `undefined` to `strokeStyle`
  silently keeps the last colour, which is how the shots once drew yellow. Every role is read
  through a chain with a guaranteed last resort.

## Type

Three roles, one family each, no fourth:

| Role | Family | Where |
| --- | --- | --- |
| `display` | the app's display stack | wordmark, `CONCEPT COCKPIT` |
| `label` | the app's UI stack | HUD labels, buttons, corner notes |
| `data` | the app's mono stack | every number, every concept label |

Sizes are derived from the canvas, never fixed at one size for all viewports:

| Element | Size | Weight / tracking |
| --- | --- | --- |
| HUD label | `clamp(10, w/150, 13)`px | 600, `0.24em`, uppercase |
| HUD value | `clamp(13, w/105, 18)`px | 600, `0.02em` |
| Pane corner label | 11px | 600, `0.14em`, uppercase |
| Concept label | `9 × uiScale(w)`px | 500, `0.18em` |
| Wordmark | `uiScale`-scaled | 600, `0.3em` |

Hierarchy rule: a label is never more than 70% of its value's size, and labels are `dim`
while values are `text`. If a label starts competing with a number, the label is wrong.

## Space

A 4px scale, in use: 4, 8, 12, 16, 24, 32. Everything inside a pane sits on it.

- Pane corner inset: 12px.
- HUD cell gutter: 10px.
- Gaps between a label and its value: 7px at the current sizes.
- Radii: 2px for controls (the cockpit button), 0 for instrument frames. Nothing is a pill.

## Motion

- Motion is physics, not decoration: throttle spool (`dt × 3.2`), drag (`exp(-dt × 0.55)`),
  bank and pitch interpolation.
- The tube's idle drift is 0.00022 rad/ms and stops the moment the pointer is down.
- **`prefers-reduced-motion` must remove motion, not shorten it:** no idle drift, immediate
  net, and no bullet travel animation (hit resolves on fire). Currently only the net is
  reduced — see the audit.

## States

Every surface must have all five, and each has its own copy:

| State | Copy | Where |
| --- | --- | --- |
| empty | `no state` / `nothing picked yet` | pane corner, cockpit pick panel |
| loading | `…` | pane corner |
| active | state label + counts | pane corner, pane button |
| unavailable | `backend unavailable`, `sign-in required`, `the backend did not answer`, `the plugin backend is not mounted` | `whyFailed()`, pane |
| reconnecting | `reconnecting` | pane corner after a failed poll |

The cockpit currently collapses all of these into `map unavailable · <raw error>`, which is a
second language for the same event. It must use `whyFailed()`.

## Composition rules

1. **One primary instrument per surface.** The map is the pane; the sky is the cockpit. Text
   lives in the corner of the instrument, never in the middle of it.
2. **No chrome that describes the product.** A surface does not need to name itself inside
   itself.
3. **A control that cannot be discovered does not exist.** If it is drag, wheel, hover or a
   key, something on screen has to say so at least once.
4. **Fire only where the person is looking.** Accent appears on what changed (a hit, a pick, a
   wall) and nowhere else.
