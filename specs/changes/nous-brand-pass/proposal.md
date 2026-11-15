# Nous brand pass

> Superseded for the cockpit surface by `specs/changes/retro-crt`: the pane is
> now an arcade CRT. The tokens and rules below still describe the pane's DOM
> chrome prior to that change.

Change id: `nous-brand-pass`
Repo: `antemuse-plugin`
Status: implemented, unreleased (`plugin.yaml` still `0.10.44`)

## Goal

Make the plugin read as a Nous Research instrument rather than a generic dark
pane. The trigger was the cockpit: it was drawing in the host's `--ui-accent`
(which, in the harness, was a campfire orange) and in plain system type, so the
most distinctive surface in the product looked like no one's product.

## What the brand actually is

Sampled from the public surfaces rather than guessed:

- `nousresearch.com` — `body` background `#0000f2`, type `#f2f2f2`; a paper
  `#f2f2f2` stage inside a blue frame; palette constants
  `--hermes-color-blue #0000f2`, `white #f2f2f2`, `neon #79f200`,
  `yellow #f2f200`, `red #f20000`, `cyan #00f2f2`.
- `hermes-agent.nousresearch.com` — electric blue ground, paper type, display
  face `Rules Gothic Condensed` with tight tracking for headlines, uppercase
  widely tracked labels for navigation, flat white pill buttons, and dark
  translucent terminal blocks for code/data.
- Type families are proprietary (Rules Gothic, Aeonik Fono), so no font file
  ships: the plugin names the family first and falls back to a condensed
  grotesque for labels and a serif for the display line.

## Decisions

- **The cockpit paints the brand ground, flat, with grain.** It is our surface,
  like the art pane that already paints its own backdrop, so it no longer
  inherits the host palette. One solid electric blue, plus a fixed ink-speck tile:
  a gradient and a glow are the tells of a screen, and the brand reads printed.
- **Marks are ink, not lamps.** Firing concepts are filled dots with a hairline
  ring; cold ones are rings. `shadowBlur` is gone. Shots are solid paper rules
  from the dash line with a pen tick at the muzzle.
- **One colour block.** `BRAND` is the only place a literal colour may appear;
  everything downstream refers to tokens, and a test enforces both the palette
  contents and that each literal is written exactly once.
- **Three type roles, named once.** `FONT.display` (wordmark), `FONT.label`
  (uppercase tracked keys), `FONT.data` (mono readouts and concept names).
  A font spelled inline is a test failure, so the system cannot rot into
  one-offs.
- **Interest is the yellow.** Hits, pips, tracers and pick counts use the brand
  yellow; chrome and points are paper; nothing else borrows an accent.
- **Panels are terminal blocks.** Ink ground, hairline rule, 2px corners, a
  tracked label above monospace rows — the site's code block, not a card.
- **The wordmark appears once.** Ψ ANTEMUSE at the top-left of the glass, with
  `CONCEPT COCKPIT` set right in the same tracked label face. No watermark.
- **Host theme still owns non-brand surfaces.** The activation art pane keeps
  its own dark ground; the status chip still takes `--ui-text-secondary`, but
  its type is now the brand label style.

## Copy voice

Terse, declarative, lowercase for body lines and uppercase for instrument keys:
`FIRING 11/120`, `PICKED · 2`, `NET · 3`, `LOCKED`, `firing 0.42 · met 29%`.
No adjectives, no exclamation, no invented certainty — the existing habit of the
pane (say which failure it is, never say "backend unavailable" for an expired
session) is the brand voice as much as the colour is.

## Non-goals

- No font files shipped, no network font loading.
- No logo asset: the mark is the character Ψ, drawn from its code point.
- No change to the map pane's projection, the `/graph` contract, or any
  behaviour under test.
- No attempt to restyle the host app itself.

## Acceptance

`acceptance.md`. Summary: 892 passed / 1 skipped, harness 21/21, pane guards
14/14.

## Open questions

- Panel chrome has no browser verification yet — the harness renders the canvas
  only, so the DOM panels are guarded by static tests and reviewed in the app.
- The wordmark's display face resolves differently per machine (Liberation
  Serif here, Didot or Rules Gothic if present). It is a stack, not a promise.
- Whether the blue ground is too strong at full-bleed in a light-themed app is
  untested; the pane is opaque by design.
