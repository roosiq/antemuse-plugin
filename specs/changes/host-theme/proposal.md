# The cockpit wears the app's theme

Change id: `host-theme`
Repo: `antemuse-plugin`

## Goal

The cockpit pane should use the desktop app's own theme variables — panel ground,
text, secondary text, strokes and accent — so it reads as part of the window it
lives in, not as a kiosk painted inside it.

## Why

Three palettes have now been tried on this pane: host theme, a Nous brand palette,
and an arcade phosphor palette. The last two painted a surface of their own, and
in the app they read as a foreign panel — the exact failure the plugin's house
rule ("theme variables only") exists to prevent. Ryan: "match the theme set in the
app."

## Non-goals

- Not a change to the CRT treatment: grain, scanlines, bloom and vignette stay,
  now tinted through the theme.
- Not a change to flight, net, shooting, picks or layout.
- No new dependency or backend surface.

## What changes

| Surface | Before | After |
| --- | --- | --- |
| Canvas ground | phosphor-tinted black | `--ui-panel-background` (fallback `--ui-background`) |
| Type and marks | P1 green | `--ui-text` / `--ui-text-secondary` |
| Strokes | brand green | `--ui-stroke-secondary` |
| Interest | brand amber | `--ui-accent` |
| DOM panels | inline brand colours | `var(--ui-panel-background)`, `var(--ui-accent)`, `var(--ui-text-secondary)` |

The only literals left in the pane are the tube itself: black raster lines, black
vignette, and neutral fallbacks for hosts that expose no variables.
