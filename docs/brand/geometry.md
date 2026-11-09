# Antemuse — the geometric layer

A structural pass for the look: what the mark, the material, and the geometry are,
with numbers. `docs/brand.md` remains the authority on the name, the vocabulary,
and the voice — nothing here changes those. This document only answers *what it
looks like when it has to be a shape instead of a photograph.*

Status: direction, with two drawn variants. Not yet wired to any surface.

## Premise

`docs/brand.md` describes a warm film still: `#0e0c0b` ground, amber light, teal
path, grain kept. That is a *place*. It has no shape, so every surface that needs
one — the marketplace icon, the desktop chip, the pane header, the favicon —
currently borrows something generic. `dashboard/manifest.json` ships
`"icon": "Waves"`, which is Lucide's waves, i.e. nothing of ours.

The brief was geometric, futuristic, abstract, hard-surface: Tesla Roadster,
Lamborghini, classical mathematics — and explicitly *not* the current world's
cyberpunk. So this layer has to be derived from the product, not decorated onto
it.

## The idea: one silhouette, four interiors

> A state is a bounded change to how the agent behaves, not a place it goes.

That sentence is the mark. **The outline never changes. Only its interior
ordering does.** Every state gets the same body, stamped with a different
interior — so four marks read as one object seen four ways, which is exactly what
the product is.

This also kills the wrong idea, which is the one every plugin brand reaches for:
a different picture per state, four little mascots. There is one thing here.

## Material

Not a frame. A body.

| | value | why |
|---|---|---|
| body weight | `BODY = 22` on a `B = 384` box | a bezel has thickness; an outline has none |
| edge | one hairline (`1.5`) inset by `BODY/2`, `#9aa6ab` at 45% | the chamfer catching light — the whole hard-surface read |
| corners | 45° cuts only, **never a radius** | radii read as software; chamfers read as machined |
| chamfers | `B/2.8` on two opposite corners, `B/9` on the other two | equal corners make a stop sign, and a stop sign is a UI container |
| construction | one vernier along the inner floor, long ticks at `1/φ²`, `1/φ`, `1` | the only classical-maths cue that reads as an instrument rather than an axis |
| gradients | none | value comes from area and edge, not from shading |

## Palette, with an area budget

The colours do not change. Their *jobs* get strict, because a geometric mark
fails by being evenly lit.

```
ground   #0e0c0b   >= 90% of any plate   the void the instrument sits in
struct   #9aa6ab     ~8%                 structure: body edge, dot fields
arc      #6fe0c8    <= 1.5%              the path; also the lit interior cut
amber    #f2b25a    <= 0.5%, exactly one element per plate   the emitter: the state itself
```

Amber is not a highlight. It is the only lit thing in the frame, and there is one
of it. Two ambers in a plate means the plate is telling two stories.

Cold rules that follow from "not analogous to current world":

- No magenta, no violet. Neon signage is the *current* world's future.
- No glyphs, no signage, no lettering inside a mark. Nothing to translate.
- No chrome, no bevels, no lens flare, no glow falloff. Instrument-lit, not
  signage-lit: the future here is a dark cabin with one warm readout.
- No grime, no scanlines, no VHS. Those are nostalgia, and nostalgia is the
  opposite of the brief.

## Type

- Marks carry no type.
- The wordmark is `ANTEMUSE`, all caps, geometric, monospaced or wide-grotesk,
  tracking `+0.24em`, one weight. Undecorated per BR-13 — no suffix, no glyph
  substitution in the name.
- Case in running copy stays sentence case per `docs/brand.md`. Caps belong to the
  mark, not to the prose.

## Motion

The terminal already has the vocabulary: `HOLD_S`, `FADE_S`, `DRIFT_S`, a Bayer
dissolve, and a crop drift. Keep all of it. Two rules for anything new:

- Nothing spins and nothing bounces. Cuts rotate in 30° steps only, and only on a
  state change.
- The dissolve is the only transition. A cut never slides in.

## The screensaver idiom

Photoreal plates were the wrong ambition. On the surfaces this product actually
has, the picture is a **glyph grid** — so a material render gets graded,
quantised, and destroyed on the way out, which is what happened to every plate I
tried. The idiom that is already terminal-native, and already the right period
reference, is the **Windows screensaver family**: Mystify, 3D Pipes, Marquee.

That is also the brief. Mystify *is* abstract, geometric, futuristic, and not of
this world — hard vector strands on a black field, bouncing off walls, mirrored
into symmetry, no material, no lighting, no depth of field. There is nothing to
grade because there was never a photograph.

```bash
python3 tools/screensaver.py walk 1 58x22         # one frame in the ramp
python3 tools/screensaver.py dream 2 --strip      # two frames side by side
python3 tools/screensaver.py --save               # write all four strips
```

Rules, so the family stays one family:

- **The field is black.** No vignette, no gradient, no grain.
- **A strand is one cell wide.** Two cells turns four mirrored copies into a smear.
- **Mirror, don't decorate.** Two-fold or four-fold symmetry about the centre.
- **Reflect off the walls**, linearly. No easing, no bounce physics, no curve.
- **Same language per state, different parameters** — trail length, speed,
  symmetry order, how many strands. Never a different visual language.
- **Amber stays the single hot accent**; everything else is the ramp.

What each state does inside that language:

| state | trail | symmetry | strands | reads as |
|---|---|---|---|---|
| walk | 22 | 2 | 2 | a path crossing the frame, once |
| daydream | 26 | 2 | 2 | long slow strands nearly touching |
| dream | 30 | 2 | 2 + fill | many crossings, dense, unresolved |
| doomscroll | 18 | 4 | 2 | fast, repetitive, four-fold chatter |

The icon mark keeps its own weight scale and is unaffected by this; what changes
is everything the *state* draws.

## Seen the way the product sees it

A plate is not only an icon. Run it through the plugin's own cell model and it
becomes what the takeover draws: `▀` glyphs, foreground the top pixel, background
the bottom one, truecolor.

```bash
python3 tools/term_view.py docs/brand/marks/walk.png 64 32 6
```

That writes three things beside the source: the literal characters (`.txt`), the
cells as coloured spans (`.html`), and a pixel-exact painting of those cells
(`.png`). The `▀` grid is the product's existing rendering path, not a new one —
`tools/term_view.py` imports `core/photographs.cells`, so what you see is what
the panel would actually emit.

Consequence worth stating: **at 64x32 the image survives; below about 40 columns
it stops being a plate and becomes an abstract field.** That is the same
abstention the plugin already makes for short text, applied to pictures — pick
the column count for the surface, do not scale the same art everywhere.

## Two variants, drawn

Both are generated, not hand-drawn: `python3 tools/gen_marks.py` writes
`docs/brand/marks/` (variant A) and `docs/brand/marks/cut/` (variant B). Re-cut
them by changing constants; do not trace them.

**A — diagram.** Walk is a stepping line, daydream a dot field out of register,
dream a three-revolution grid, doomscroll a tapering stack. Honest to the
machinery, and it renders cleanly at 96px.

**B — cut.** Each state is one decisive cut across the same body: walk a level
blade with a lifted leading edge, daydream two blades almost parallel,
dream three blades through one point, doomscroll one blade repeated downward.

Judgement, from looking at both at size: **A reads as a data-viz icon set.** A
polyline, a dot cloud, a hatch, and bars are chart forms, and charts read as
dashboard furniture, not as a mark. **B reads as machined cross-sections**, which
is the brief — the interiors look like the inside of a part rather than a plot of
it. B's weak plate is daydream: two parallel blades with nothing else in the frame
are the most abstract of the four, and may need one datum feature to hold it.

Recommendation: **B as the family, A's walk line kept as an in-product motif**
(the walk map already draws that path in the terminal, so the line is not lost).

## Where it lands, if approved

- `dashboard/manifest.json` — `"icon"` currently `Waves`; replace with the mark.
- `desktop/plugin.js` — the status chip and pane header are the smallest place
  the mark has to survive; 16–20px.
- Site favicon (`/home/ryan/antemuse/public/favicon.png`) — currently unrelated to
  the plugin's look.
- `README.md` — one plate at the top, no caption.

## Open — Ryan decides

1. **Variant A or B** as the family (recommendation: B).
2. **Amber or arc as "the state"** in the marks. Today amber is the emitter, one
   element. If amber should mean *the person's own step* instead, the marks
   invert.
3. **Whether the mark goes in the name at all** — a mark beside an undecorated
   wordmark, or mark-only where space is 32px.
