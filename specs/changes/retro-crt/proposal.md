# Retro CRT cockpit

## Goal

Take the concept cockpit from "branded modern instrument" to **giga retro**: the
pane should read as an arcade cabinet's CRT — green phosphor, scanlines, bloom, a
vignetted tube — while still flying the same concept graph.

Retro here means the **display**, not a low-resolution picture: the panel is a
phosphor monitor, so the marks stay sharp. Downsampling the world and the type
was a wrong turn (it is pixel art, not a vector monitor) and was reverted.

## Why

The cockpit is a game-like surface. Flying and shooting at concepts is an arcade
verb, and the Nous brand pass made it look like a marketing page with a cockpit
painted on. Ryan asked for giga retro directly after the shooting mechanic landed.

## Non-goals

- Not a new pane, route, or data source: same `GET /graph`, same registrations.
- Not an audio pass.
- Not a global brand change: the rest of the plugin stays on host theme variables.
  The cockpit remains the stated exception.

## What changes

| Surface | Before | After |
| --- | --- | --- |
| Ground | flat electric blue + grain | near-black tube `#050a05`, phosphor speckle, scanlines |
| Type | display serif + condensed grotesque + mono | one monospace family in caps, tracked, drawn sharp |
| Interest | brand yellow | cabinet amber `#ffb000` |
| World | smooth vector | smooth vector, but on a phosphor tube: bloom, raster, vignette |
| Edge | none | tube vignette + hairline inner frame |

## Acceptance

- A still reads as an arcade CRT: chunky contacts, visible raster, green phosphor.
- HUD text is blocky and still legible; no cell overlaps or clipped values.
- All existing behaviour (flight, net, shooting, picks) is unchanged and tested.
