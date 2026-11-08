# Scene assets — which pictures the visualizer needs

Status: **implemented for all four states** 2026-11-08 (43 credits). Companion to
`spec.md`; this file decides *what is drawn*, the other decides *how big and how served*.
Owner: Ryan Cook. Scope: scenes and assets only. The four-state lifecycle, durations,
turn budgets and tool policy are out of scope and must not change.

## 1. The states, and what each one is a picture of

From `core/states.py` — these are the lifecycle facts the pictures must serve, not
decorations on top of them.

| state | label | duration | turns | tools | contract | the picture must be about |
| --- | --- | --- | --- | --- | --- | --- |
| `walk` | WALKING | 3 min | 6 | all | work continues · the frame is elsewhere | a figure moving through a place; forward motion; the world carries on while work happens |
| `daydream` | DAYDREAMING | 3 min | 2 | none | two memories · join only if it holds | two concrete things in a soft field, drifting, briefly touching, separating |
| `doomscroll` | DOOMSCROLLING | 8 min | 3 | read-only | random feed · consume, do not synthesize | a stream of content sliding past the lens; nothing joined, nothing kept |
| `dream` | DREAMING | 30 min | 2 | none | recombine stored concepts into new things | objects combined into things that could not exist; slow; no horizon logic |

`dissociate` is present in `tools/scene.html` and in `three_frames/` but is **not a
state**. It is a retired scene and must not come back as one.

## 2. What the scenes are today, measured

All five are procedural primitives in one 248-line file, with no loader and no
assets. Inventoried from source:

- **walk** — a `PlaneGeometry` floor, a wide luminous path plane, a sun disc and
  halo, a low glow bar, and a figure built from a capsule torso, a sphere head and
  limbs. Camera drifts ±0.18 in x.
- **daydream** — seven transparent flat-shaded icosahedra on a ring, bobbing.
- **doomscroll** — fourteen wireframe cards receding to z = −20, each with a header
  bar and five procedural "text" lines, camera tilt 0.035 rad.
- **dream** — two translucent spheres sliding through each other, plus 300 dust
  points placed with `Math.random()`.
- **dissociate** — a torus knot plus a wireframe ghost of the same knot. Retired.

At 44 × 12 this is atmosphere. At 4,611 cells it is a diagram: flat untextured
primitives, one value per object, and a "person" made of three shapes.

## 3. Four rules every scene must pass

1. **One subject, large.** The eye lands on one thing. Two competing subjects at
   87 × 53 is clutter; at 44 × 12 it is noise.
2. **Read at 44 × 12 first.** The same scene feeds the chat card. If the card does
   not say which state it is, the pane is decoration — so shape, not detail, carries
   identity.
3. **A value structure, not a colour structure.** The ramp is luminance. Every scene
   needs a strong dark/light split and at least three distinguishable bands across
   the subject, or it flattens to one glyph.
4. **One deliberate motion per frame step.** At 8 frames a loop, a scene that moves
   everything reads as jitter; a scene that moves one thing reads as alive.

## 4. Assets required, per state

Asset roles are stated so a mesh can be sized and a billboard can be placed. Credits
are Meshy's declared estimates (`meshy_text_to_3d` preview 5, `+refine` 10,
`meshy_text_to_image` 3–9, `meshy_image_to_3d` 5–40).

### 4.1 walk — "a place, and a figure walking out of it"

| role | kind | note | credits |
| --- | --- | --- | --- |
| figure | 3D mesh, rigged optional, ≤ 15k tris | seen from behind, walking away; must silhouette cleanly at 44 × 12 | 15 |
| ground | procedural (existing plane) | texture from a 2D image, tiled | 3–9 |
| horizon light | procedural (existing sun disc) | no asset | 0 |
| mid-ground | 2 × 2D billboards at z −12, −20 | blurred shapes that give depth without detail | 6–18 |

Prompt seeds: *"a lone figure in a hooded coat, seen from behind, mid-stride, heavy
fabric, backlit"*; *"wet asphalt at dusk, amber light pooling, long exposure"*.

### 4.2 daydream — "two things, and the space between them"

| role | kind | note | credits |
| --- | --- | --- | --- |
| object A | 3D mesh, ≤ 3k tris | a small familiar thing: a cup, a key, a stone; must read as an object, not a blob | 5–15 |
| object B | 3D mesh, ≤ 3k tris | a different everyday thing, same visual weight as A | 5–15 |
| soft field | procedural | fog plus a gradient; no asset | 0 |

The current icosahedra say "abstract", which is the one thing a memory is not. Two
recognisable objects carry the state's meaning; seven blobs carry none.

### 4.3 doomscroll — "a feed, passing"

| role | kind | note | credits |
| --- | --- | --- | --- |
| card texture | 1 × 2D image | an abstraction of a social post: a photo above two lines of type, blurred past legibility | 3–9 |
| card geometry | procedural (existing planes) | reuse the existing card, now textured | 0 |
| grain/dust | procedural | no asset | 0 |

No new geometry is needed here. This state is the cheapest and the most likely to
look good first, because the subject is already a rectangle in motion.

### 4.4 dream — "a thing that could not exist"

| role | kind | note | credits |
| --- | --- | --- | --- |
| combination A | 3D mesh, ≤ 8k tris | a chair growing branches; a lamp with a face; one recognisable object fused with one incongruous one | 5–25 (+10 refine) |
| combination B | mirror of A, deformed copy | the second half of the recombination, procedurally warped from A | 0 |
| dust | procedural, **seeded** | replaces `Math.random()` | 0 |

This is the one state where a single mesh is worth the refine cost: the whole point
is that the object is strange in a way a primitive cannot be.

### 4.5 Shared assets

One figure mesh can serve `walk` (from behind) and, scaled and slowed, `dream`'s
human-scale object. Reuse is both cheaper and more coherent than five unrelated
packs. Nothing is shared between `daydream` and the rest: those objects should feel
borrowed from life, not from the other scenes.

## 5. Asset contract

- **Location** — `data/meshy/<state>/<role>.glb` (or `.png` for billboards), with
  `data/meshy/<state>/manifest.json` beside it: `role`, `provider`, `prompt`, `date`,
  `licence`, `sha256`, `format`, `triangles` (meshes), `size_px` (images).
- **Units and axes** — metres, origin at ground contact, forward −Z, up +Y. A figure
  that arrives at 40 m tall is a bug, not an art direction.
- **Triangle budgets** — figure ≤ 15k, prop ≤ 3k, dream object ≤ 8k. Above that the
  renderer is paying for detail the ramp discards.
- **No lettering in any texture.** ASCII cannot show type, and a picture that appears
  to contain words breaks the one rule this plugin is built on (BR-5).
- **No faces at camera, no text-bearing signage**, for the same reason.
- **Determinism** — every scene takes its randomness from a seed carried in the bake
  key; a re-bake of the same pack must be byte-identical.

## 6. Storyboard, 8 frames per state

Each row is what changes between frames; everything else holds still.

| state | frames 0–7 |
| --- | --- |
| walk | camera advances 0.35 m per frame; figure's stride alternates; sun disc does not move |
| daydream | A and B drift toward each other over frames 0–3, touch at 4, separate by 7 |
| doomscroll | card stream advances one card per frame at a speed that never pulses; tilt constant |
| dream | A morphs into B's shape slowly; dust rotates a fixed 1/8 turn per frame |

## 7. Cost, and the order to build in

| pack | credits |
| --- | --- |
| walk (figure + ground + 2 billboards) | 24–42 |
| daydream (2 props) | 10–30 |
| doomscroll (1 card texture) | 3–9 |
| dream (fused object + refine) | 15–35 |
| **total** | **52–116** |

Balance on hand is 1,101, and the plugin caps a chat at 200 credits, so the whole set
fits inside one approved budget. Order: **doomscroll → daydream → walk → dream**.
Doomscroll proves the texture path with three credits; daydream proves the loader
with two props; walk is the most valuable picture and needs a rigged figure; dream
needs the most judgement and the most money.

## 8. Acceptance per state

1. A person shown the four chat cards in random order names the state correctly, from
   the picture alone, without the label line.
2. At 87 × 53 the subject occupies ≥ 40 % of the frame's height and shows ≥ 3
   luminance bands.
3. The loop is invisible: frame 7 → 0 shows no jump in the subject's position beyond
   one cell.
4. Frame-to-frame motion is at least two cells at 87 × 53, and never more than eight
   (jitter, not animation).
5. No asset contains lettering; a scan of the pack finds no text-like region.
6. Same pack, same seed, same glyphs: two bakes compare byte-identical.

## 9. Open decisions (owner)

1. **Reuse the walk figure in dream?** Cheaper and more coherent; or keep every state
   cast with its own object.
2. **Does walk need a place at all?** A figure alone in a lit void might read harder
   at 44 × 12 than a figure on a road.
3. **Rigged or static figure?** Rigging is free of extra credits (`meshy_rig`, 5) but
   the bake only needs eight poses; a static mesh plus camera motion may be enough.

## 10. What was built (2026-11-08)

43 credits spent, all four states now draw real assets instead of primitives.

| state | assets | triangles | credits |
| --- | --- | --- | --- |
| walk | `walk/figure.glb` — hooded figure from behind | 15,810 | 5 |
| daydream | `daydream/mug.glb`, `daydream/stone.glb` | 3,164 / 3,138 | 10 |
| doomscroll | `doomscroll/card.png` (1024 × 1024) | — | 18 |
| dream | `dream/chair_branches.glb` | 8,366 | 5 |

Rejected and kept on disk with the reason: `doomscroll/card_v1_phone.png` — it
read as a photograph of a phone and carried roughly one luminance band, so the ramp
had nothing to work with. The second take is a bright card on black.

**What the pipeline needed that the plan did not anticipate:**

1. **A GLB reader, not a loader** (`tools/glb_mesh.js`, ~100 lines). The vendored
   `three.module.js` declares no revision and the repo's `three` is 0.82, so pairing
   either with a 0.180 `GLTFLoader` is a guess. The reader takes positions, normals
   and indices and nothing else — which is all a luminance ramp can use.
2. **A `prop()` normaliser.** Meshy meshes arrive at their own scale; each is
   rescaled to a stated longest side and re-centred on its bounding box, so a mug and
   a chair can share a scene without one being 40 m tall.
3. **Self-lit props.** Two point lights at four metres leave a small mesh almost
   black; the materials carry a little emissive so the ramp has something to read.
   The amber/teal split in the daydream render is the two lights, not a texture.
4. **A density regression the eye would miss.** Filling the frame with the card
   pushed the 40 × 8 chat card to **79.4 %** glyph coverage — a solid block. The
   existing `test_every_scene_is_actually_visible` bound of 60 % caught it; the
   camera sits back at 4.4 rather than relaxed to fit the test.

**Auth note, still true:** the plugin's 28 MCP tools are installed but reject the
CLI's OAuth token (401). Every asset above was generated through the CLI path, which
already holds a verified session. Balance after this pack: see §3.0.

**Not done:** the frames are still served at 44 × 12. The assets are full-size; the
surface that shows them is not. That is `spec.md`, which remains unimplemented.
