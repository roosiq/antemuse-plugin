# Antemuse — brand pass

Decisions, not options. Anything still open is listed at the bottom.

## The name

**Antemuse.** The plugin is not a product inside Antemuse; it is the part of
Antemuse that touches the agent, so it carries the brand name undecorated.

Earlier names are retired and appear nowhere in the repo: each described a
metaphor we dropped — a room, a workspace, a sub-brand — or a suffix that made
the plugin look like a feature of itself. The name is Antemuse, undecorated.

There is one project and it is called Antemuse. The part that touches the agent
is not a separate product with its own repo: it lives in the project, at
`/home/ryan/antemuse/plugin`. The site, the lab, and the states are the same
thing seen from different sides, and they share one name.

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
blocked     the agent is in a dream; no tools until it comes back. /return to end it early.
ending      WALKING ended · walked · 1m · 3 step(s) · body part → loins → torso
idle        not in a state.
```

## Commands

```
/walk  /daydream  /dream  /doomscroll     enter
/return                                   leave, keep the account
/states                                   what is happening now
```

`/return` is the name, and it was bought with a bug: Hermes ships `/snapshot`
with the alias `/snap`, so the plugin's `/snap` was rejected at registration and
silently never existed — the escape hatch every blocked-tool message pointed at.
Renamed to `/return`, which is also what the residue contract says ("come back
and tell the person what happened in there"). Rejected: `/back` (ambiguous with
navigation), `/wake` (implies sleep), `/end` (generic). A plugin command that
collides with a built-in is dropped with a warning, not an error, so this class
of breakage is silent — check the command actually appears after registering.

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
categories and none of them is cognition. The earlier recommendation to file
under `productivity` is invalid: that category does not exist.

**OPEN — Ryan decides:** accept `general`, the only honest existing fallback, or
propose a `cognition` category upstream before listing. The tags remain
`cognitive`, `creativity`, `states`, `imagery`. A plugin cannot invent a category,
but the submission can say plainly that Antemuse does not fit.

## Open

1. `/return` — settled; `/snap` was unavailable (built-in alias collision).
2. Propose a `cognition` category upstream, or file under `general` and say so.
   **OPEN — Ryan decides.** `productivity` is not a valid catalog category.
3. Version: 0.9.0 shipped with the internal consolidation (package `core/`,
   dead board removed). `scenes-per-surface` therefore lands as 1.0.0.
