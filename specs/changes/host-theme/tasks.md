# Tasks — host theme

## T1 — Read the host theme
- [x] `cockpitTheme(el, doc, win)` resolves tokens through a probe element
- [x] Grey sentinel distinguishes "undefined variable" from a real colour
- [x] Probe removed after reading
- Evidence: `test_the_cockpit_takes_its_colours_from_the_app_theme`

## T2 — Alpha from any colour
- [x] `withAlpha` parses hex and `rgb()/rgba()`
- Evidence: `test_alpha_is_derived_from_a_theme_colour_not_guessed`

## T3 — DOM chrome in the app's variables
- [x] Panels: `var(--ui-panel-background)`, border `var(--ui-stroke-secondary)`
- [x] Interest: `var(--ui-accent)` on picks, counts and the net rule
- [x] Labels: `var(--ui-text-secondary)`
- Evidence: colour-guard test; stills from `tools/cockpit_video.py`

## T4 — Texture tuned for a themed ground
- [x] Grain 0.5, scanlines 0.08
- [x] Behaviour unchanged: harness 24/24, pane guards 15/15, suite 893/1
