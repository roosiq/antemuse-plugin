# Nous brand pass — tasks

## T1 — Read the brand instead of guessing it
- [x] Sample `nousresearch.com`: body `#0000f2`, type `#f2f2f2`, palette constants
      (`--hermes-color-blue/white/neon/yellow/red/cyan`), display face
      `Rules Gothic Condensed`, uppercase tracked nav labels, 1px blue frame
- [x] Sample `hermes-agent.nousresearch.com`: blue ground, paper type, tight-tracked
      display headline, white pill buttons, dark translucent terminal blocks
- Evidence: computed styles and screenshots captured during the pass; values
  recorded in `design.md`.

## T2 — One token block, one type system
- [x] `BRAND` (nine tokens) and `FONT` (display / label / data) defined once
- [x] `PANEL`, `LABEL`, `DATA` compose them for the DOM
- [x] `cockpitTheme()` returns the brand surface and reads nothing from the host
- Evidence: superseded with the palette — see `host-theme` for the guards that hold now.

## T3 — Ground, frame and wordmark
- [x] Radial ground `blue → deep`
- [x] Canopy/dash in ink; hairlines in paper; four corner ticks
- [x] `Ψ ANTEMUSE` wordmark left, `CONCEPT COCKPIT` right, both tracked
- Evidence: harness still; wordmark guard test.

## T3b — Grain and ink marks
- [x] Flat ground, no gradient; deterministic 96px ink-speck tile at 0.7
- [x] Points as ink marks (filled + ring for firing, ring for cold), no shadow blur
- [x] Shots as 380 ms paper rules from the dash with a muzzle tick and a yellow
      impact mark; yellow no longer used for chrome
- Evidence: vision review of video frames — grain visible, tracers read as ink
  rules; `test_the_theme_names_every_colour_the_drawing_asks_for` now stops the
  class of bug (a missing `theme.paper`) that made the first tracers yellow.

## T4 — Instrument typography
- [x] HUD keys `FONT.label` 8px tracking 0.26em; values `FONT.data` 13px
- [x] Heading tape `FONT.data` 10px tracking 0.1em; edge labels suppressed
- [x] Concept labels `FONT.data`; flip left when they would leave the glass
- [x] `LIT` renamed `FIRING`; yellow only on `PICK` and `FIRING`
- Evidence: vision review of two stills — clipped labels and half-cut tape
  numbers were both found and fixed, then re-reviewed.

## T5 — Panels and pane chrome
- [x] Net list, pick list and locked chip on `PANEL`/`LABEL`/`DATA`, 2px corners
- [x] Increase type: `picked` header with the count in yellow, `×hits` per row
- [x] State pane corner lines use the label/data roles; status chip tracked caps
- Evidence: pane guards; panels not yet browser-verified (see acceptance).

## T6 — Verification and record
- [x] Harness 21/21, pane guards 13/13, full suite 891 passed / 1 skipped
- [x] Spec written; `CHANGELOG.md` line under `0.10.44`
- Evidence: commands in `acceptance.md`.

## Not done

- [ ] **DEFERRED — no live desktop-app verification in this repository task; retain for a running-app pass.** Browser screenshot of the DOM panels (harness renders canvas only)
- [ ] **DEFERRED — no live desktop-app verification in this repository task; retain for a running-app pass.** Verify the pane in the running app after a plugin reload
- [x] **DONE — host-theme test and cockpit harness exercise a resolved `#f4f4f4` ground; no dimming is applied.** Decide whether the ground should be dimmed when the app theme is light
