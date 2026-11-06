# Antemuse — brand pass

Decisions, not options. Anything still open is listed at the bottom.

## The name

**Antemuse.** The plugin is not a product inside Antemuse; it is the part of
Antemuse that touches the agent, so it carries the brand name undecorated.

Retired: `concept-kitchen`, `antemuse-kitchen`, `antemuse-room`,
`antemuse-states`. Each described a metaphor we dropped — a kitchen, a room, a
sub-brand.

Repo directory: `/home/ryan/antemuse-plugin`. It cannot be `~/antemuse` because
that path is the public site repository.

## The sentence

> Antemuse gives the agent somewhere to think, and you something to watch.

Use it in the README, the catalog listing, and nowhere else. It is a description,
not a tagline to repeat.

## What a state is called

Lowercase, verb, the thing a person does:

```
walk    daydream    dream    doomscroll
```

Not "mode", "session", "journey", "room", "experience", "episode". A state is a
bounded change to behaviour — that is the whole idea, and the vocabulary should
not smuggle in a container again.

The four are the product. One more would need to justify itself against these.

## Voice

- Sentence case. Second person. No exclamation marks.
- Never explain the mechanism to the person. In the terminal there is no text at
  all; in chat there is one image and no caption.
- Speak about the agent in the third person when the person is the audience:
  *the agent is walking*, not *you are walking*.
- Short. A blocked tool says what happened and how to leave.

Copy in place:

```
catalog     Antemuse — let the agent walk, daydream, dream, or doomscroll.
blocked     the agent is walking; no tools while it walks. /snap to bring it back.
ending      WALKING ended · walked · 1m · 3 step(s) · body part → loins → torso
idle        not in a state.
```

## Commands

```
/walk  /daydream  /dream  /doomscroll     enter
/snap                                     leave, keep the account
/states                                   what is happening now
```

`/snap` is the one contested name. It is short, it is what you say to someone
spacing out, and it fits on a key. Alternatives considered and rejected:
`/back` (ambiguous with navigation), `/wake` (implies sleep, and dream is the
state where sleep actually makes sense), `/end` (generic).

## Look

One palette across every surface:

```
ground   #0e0c0b    near-black, warm
amber    #f2b25a    the light source
teal     #4fa89c    the path
```

Photographs are graded toward this palette, never away from it. Film grain is
kept, not cleaned up — at 100×52 pixels grain is what makes a dark frame read as
a place.

Composition per surface: **2:1 in the terminal** (because a cell is twice as tall
as it is wide), **4:5 in chat** (because a message renders an image at message
width, and 2:1 becomes a strip).

## Surfaces, in brand terms

- **Terminal** — a film. Continuous, graded by the clock, no words.
- **Chat** — a postcard. Two or three stills over the life of a state, no caption.
- **The model** — a ledger. The same state as text, addressed to the agent, never
  shown to the person.

## Catalog

Category is unresolved by construction: the marketplace has nine hard-coded
categories and none of them is cognition. File under `productivity` with tags
`cognitive`, `creativity`, `states`, `imagery`, and keep the gap on record — a
plugin cannot invent a category, but the submission can say plainly that it does
not fit.

## Open

1. `/snap` — keep or rename. Recommendation: keep.
2. Propose a `cognition` category upstream, or file under `productivity` and say
   so. Recommendation: file, and raise the category gap separately.
3. Version: 0.9.0 shipped with the internal consolidation (package `core/`,
   dead board removed). `scenes-per-surface` therefore lands as 1.0.0.
