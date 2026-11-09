# The look

One rule set, applied to every plate. Derived from the direction — geometric,
futuristic, abstract, hard-surface, classical mathematics, aerodynamic surface
language — and validated against generated plates, not described in the
abstract.

## The rule

**A dark machined object in an empty black room that does not exist, lit by one
amber edge, crossed by one teal line.**

- **Object.** Graphite, brushed, matte, with fine tool marks. Faceted. It is
  always one thing, centred, with more void than object around it.
- **Teal is the path.** A single thin line — of light, of filament, of edge —
  that shows where something is going. It is the only cool element and there is
  never a second one.
- **Amber is the point.** Exactly one lit thing in the frame: one chamfer, one
  seam, one node. It marks the thing the state is *about*. Never a wash, never
  two.
- **Ground.** Pure black. Not dark grey, not a gradient, not a floor, not a
  horizon. The object is not standing on anything.

## Surface

| Do | Don't |
| --- | --- |
| Unequal 45° chamfers | Rounded edges, radii, fillets |
| Brushed graphite, tool marks | Chrome, mirror, gloss |
| Matte metal, hard shadow | Glow, bloom, lens flare, halation |
| Film grain, 1024² | Clean digital flatness |
| One object, generous void | Clutter, props, environment |

## Forbidden

Neon. Magenta, violet, purple. Signage. Glyphs used as decoration. Text of any
kind in the plate. Logos. Grime, rust, patina. Rooms, floor planes, horizons.
People. More than one warm light.

This is the line between *futuristic* and **the current world's cyberpunk**. The
plates are quiet machines, not streets at night.

## State grammar

Every state is the same three parts with one thing changed — the behaviour of
the teal line, and where the amber sits.

- **walk** — nodes receding along an invisible line into darkness. Teal is a
  path with direction. Amber marks the node it is on.
- **work** — a lattice assembling. Teal follows the seam being joined. Amber
  marks the cell that just landed.
- **daydream** — two clusters drifting, teal strung between them, nothing
  touching. Amber is off to one side, unattended.
- **dream** — shards converging. Teal is a halo. Amber is the core they form.
- **doomscroll** — a column of blank panels rushing past. Teal is one edge,
  repeated and unread. Amber flickers past without landing.
- **idle** — mass at rest. Teal lies still along the base. One faint amber seam.
  Sleep, not absence.

## Pipeline

Rendered by **gufo `serve image`** — `qwen_image_21`, base checkpoint
`Qwen/Qwen-Image-2.1` (33.1 GB, sharded text encoder with index; the Turbo
checkpoint ships its text encoder unsharded and gufo rejects it).

- `POST /v1/images/generations`, `size: 1024x1024`, `steps: 32`, fixed seed.
- 32 steps ≈ **121 s** per plate on this box.
- Prompt shape: *state sentence* + *style suffix* (graphite, chamfers, one amber
  edge, one teal filament, pure black void, no text, no neon, matte, film grain).
- The style suffix is not optional. Without "pure black void" the model adds a
  floor; without "matte" it adds chrome; without "one amber edge" it adds gold
  everywhere.

Lane discipline: the image lane and the LLM lane do not run together. The LLM
lane holds ~87 GiB of GTT; a 33 GB BF16 pipeline on top of it is an OOM. Stop
one, run the other.
