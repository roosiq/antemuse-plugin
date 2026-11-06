# Antemuse

The agent can take a walk, daydream, dissociate, dream, or doomscroll — and a
person can watch it happen in the CLI and take the same state beside it.

A state is a bounded change to behaviour, not a place:

- **tools** — what the agent may still touch (a walk takes everything away)
- **directive** — injected into the turn the state governs
- **contract** — the one line the reply is held to
- **residue** — what it carries back when the state ends

States expire on minutes *and* turns; the clock decides when it ends, the turn
count decides how much of it the model gets.

## The panel

What you see depends on where you are standing:

- `/states` in a terminal hands the screen to the takeover: clock, draining bar,
  the agent's column on the left and yours on the right, live keys.
- `/state` prints one frame of the state as a picture — no words, by design.
- In chat, `/states` prints a postcard: one image, no caption.

The text frame still exists for reading state in a place that cannot draw
(`panel.debug()` in `core/panel.py`): state, clock, contract, closed tools,
turns, residue, both columns as plain lines.

Two surfaces, one state: the takeover is its own process (the Ink TUI runs
tools without a tty, so a state cannot draw itself inside an agent tool result),
and everything else — card, postcard, plain record — is encoded from the same
state dict.

```
antemuse
 1 walk  2 daydream  3 doomscroll  4 dream
 n note  j join  space return  q quit
```

## Install

```bash
ln -s ~/antemuse-plugin ~/.hermes/plugins/antemuse
hermes plugins enable antemuse
```

## Layout

```
plugin.yaml            manifest: 1 tool, 3 hooks
__init__.py            hooks (pre_llm_call, pre_tool_call, transform_llm_output),
                       /walk /daydream /dissociate /dream /doomscroll /return
                       /states /note /watch, and the state tool
core/states.py         the five states: tools, directive, contract, residue
core/engine.py         enter/stop/tick, tool policy, journal, residue
core/storage.py        the one active record, and the data dir it lives in
core/walks.py          walks as data: graphs and the rules for moving on them
core/sources.py        material: WordNet steps, FrameNet frames, memories, feeds
core/social.py         the live feeds a doomscroll eats
core/ticker.py         the timer that delivers material while a state runs
core/panel.py          the printed text frame
core/photographs.py    terminal images: cells, dissolves, drift
core/walk_map.py       the walk drawn as a side-scrolling place
core/backdrop.py       pre-rendered three.js frames, replayed as blocks
core/surfaces.py       one frame, encoded per client
core/tui.py            the full-screen takeover (alt screen, truecolor, keys)
bin/antemuse           launcher on PATH
tests/                 74 tests (6 need `npm ci` for the renderer)
```

## Verify

```bash
antemuse                     # full-screen view
hermes plugins doctor ~/antemuse-plugin
PYTHONPATH= ANTEMUSE_STATES_HOME=$(mktemp -d) uvx pytest tests/ -q
hermes chat -q '/walk' && hermes chat -q '/states'
```

A fresh clone runs 68 of the 74 tests; the six renderer tests skip until
`npm ci` has fetched three and the software renderer.

## Notes

- The `state` tool is exempt from every block, so a state can always be ended even when every other tool is closed.
  An earlier build blocked its own escape hatch and locked the agent out of its
  tools until the clock ran down.
- State is profile-wide, not per-session: the metaphor is about the agent.
- Data lives in the profile plugin data dir, overridable with
  `ANTEMUSE_STATES_HOME`.

## three.js backdrop

The takeover can carry a real 3D animation. WebGL does not run in a terminal, so
the pipeline is: headless Chromium + swiftshader renders the scene to PNG, the
PNG is quantised to upper-half blocks (`▀` = two vertical pixels per cell), and
the takeover replays the cached frames at animation speed.

```bash
cd ~/antemuse-plugin && python3 tools/render_three.py    # 12 frames, ~0.65 s each
```

Frames land in `<plugin data>/three_frames/`; `core/backdrop.py` loads
them at whatever cell size the terminal can afford (44x14 in the takeover, 96x26
full-screen). Playback is free — pre-built strings, so the clock and spinner keep
their own timing.

Live WebGL at 60 fps inside a terminal is not a thing: one headless render costs
~0.65 s. For real images rather than blocks, the same PNGs can go through the
kitty graphics protocol or sixel where the terminal supports it.

## Channel awareness

The card is sized to the client, not to the terminal:

| channel | width (cols) | fence | budget |
|---|---|---|---|
| Discord (mobile / unknown) | 40 | yes | 1800 chars |
| Discord desktop | 56 | yes | 1800 chars |
| Matrix | 52 | yes | 4000 |
| Telegram | 40 | yes | 3800 |
| Slack | 46 | yes | 3800 |
| plain text / LM | 72 | no | — |

The channel is learned from the turn's `platform` (recorded in `pre_llm_call`)
and `state(card)` picks the plan automatically; `state(card, name="discord_desktop")`
forces one. Cards are fenced in a code block because a proportional font destroys
spaced art, and `_shrink` drops art rows from the middle when the message would
exceed the channel budget.

## Scenes

One scene per state, rendered from `tools/scene.html`:

- **walk** — a figure walking away from camera toward a low sun on a perspective grid
- **daydream** — slow, translucent low-poly blobs drifting past each other
- **dissociate** — the same knot twice: one solid and near, one wireframe and far, the gap breathing
- **dream** — two coloured spheres merging and separating inside a slow dust field
- **doomscroll** — feed cards with text bars streaming toward the camera, tilted and accelerating

```bash
python3 -m http.server 40813 --bind 127.0.0.1 --directory ~/antemuse-plugin &
python3 tools/render_three.py          # 5 scenes x 8 frames, ~0.6 s each
```

## What each state actually does

States are not moods: each one pulls real material on a timer and writes it into
the journal as an event (`who="state"`), so the panel fills while you watch.

| state | length | cadence | material | done with it |
|---|---|---|---|---|
| **walk** | 12 min | 18 s | **WordNet** — 117,659 synsets | one step per event along a named edge (hypernym, hyponym, holonym, meronym, similar, also-see, antonym), continuing from where the last step ended, with the destination's definition |
| **daydream** | 3 min | 10 s | `MEMORY.md` + `USER.md` | two memories surface; they are joined only when they share enough terms, otherwise reported adjacent |
| **doomscroll** | 8 min | 6 s | live RSS (Ars Technica, The Verge, HN), cached 30 min | random items, no synthesis — the feed talks, you consume |
| **dream** | 30 min | 40 s | **FrameNet** — 1,221 frames | a frame's roles and lexical units recombined into a thing that does not exist: "a {frame} missing its {agent}, so every {patient} has to stand in for it" |

Sources are honest about failure: missing WordNet says `wordnet unavailable`,
missing FrameNet says `framenet unavailable`, an unreachable feed says
`feed unavailable`, and none of them invents content.

Corpora live in `~/nltk_data` (`wordnet`, `framenet_v17`) and are found through
`NLTK_DATA`, so the plugin needs no download at runtime. The walk keeps its place
in `walk_cursor.json` and refuses to step straight back where it came from.

`dissociate` is gone — replaced by doomscroll.

### Coming back

Every state ends with an account of itself, built from the journal rather than
from a template: state, minutes, step count, and the trail, condensed to four-word
heads.

```
WALKING ended · walk 1m · 3 step(s) · salt to brine → brine to fish → fish to salt
Come back and tell the person what happened in there.
```

The account is kept as residue (`kind: "report"`), journalled as an event named
`report`, and the next turn opens with
`[YOU JUST CAME BACK — say what happened in there, in your own words, before
anything else]`. Expiry and `/return` produce it identically; a state that
received nothing says `nothing arrived`. What the material meant is still the
agent's to say. Spec: `specs/changes/state-return-report/spec.md`.

## The walk, as a place

`/walk` takes over the screen with a side-scrolling map instead of a looping
backdrop. The map is not decorative: it is parsed straight from the journal, so
every node on screen is a WordNet step that actually happened.

```
├ +4
├ +3                                    │SENSE
├ +2    ──○─ entity    ──●─ entity·2    │  a separate and self-contained
├ +1 ───     ───    ───└───┘            │  entity
├  0                       ──▮  thing   │PATH
▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁ │  ↓ abstraction ↑ entity
```

- **Camera follows x and depth.** The newest node sits right of centre; a climb
  scrolls the older nodes down instead of off the top.
- **The depth ladder** on the left is the hypernym altitude, so `+3` means three
  levels above where the walk started.
- **Fog ahead** of the walker is the part of the graph not walked yet — the map
  only ever shows what has been traversed.
- **The right panel** carries the current sense and the last four steps, so the
  definition stays on screen for the whole turn instead of scrolling past.
- **Edges are the relation**: teal climbs (hypernym/holonym), amber descends
  (hyponym/meronym), grey crosses (antonym/sibling).

Keys: `h`/`l` pan the camera, `0` resets, `j` adds your own word — it lands on
the map as a `◆` at the current depth and is scored against WordNet like any
other step, so the person walks the same path rather than watching one.

## Walks are data

A walk is a graph plus the rules for moving on it — no code, no model calls.

```python
state(action="walks")                     # list built-ins and yours
state(action="walk_new", spec={           # save your own
    "name": "hearth", "graph": "manual",
    "edges": {"salt": ["brine"], "brine": ["fish"], "fish": ["salt"]},
    "seed": {"mode": "fixed", "node": "salt"}})
state(action="enter", name="walk", walk="hearth")
```

or just `/walk upward`. Built-ins: `wander` (all edges), `upward` (hypernyms +
wholes), `downward` (hyponyms + parts), `lateral` (similar / also-see /
antonym). User walks live as JSON in `<data>/walks/<name>.json`, so they can be
edited by hand or generated by an agent.

`GraphWalk` (in `core/walks.py`) owns the policy: which relations count, what
seed to start from (`continue`, `random`, `word`, `fixed`), whether to avoid
stepping back, and where it stopped. Cursors are namespaced per walk, so `upward`
and `salt circle` each remember their own place. A dead end does not end the walk —
it picks up at another node and says so.

Graphs so far: `wordnet` (117,659 synsets, seven named relations) and `manual`
(any adjacency list you write). Adding a graph is one class with `resolve`,
`random_node` and `edges`.

## Doomscroll sources

Real timelines, sampled uniformly across sources so one loud feed cannot take
over the scroll:

- **Bluesky** — `public.api.bsky.app` "what's hot", 38 posts per pull
- **Mastodon** — `fosstodon.org` public timeline, 30 posts
- **Hacker News** — Algolia front page, 20 stories
- **RSS** — Ars Technica and The Verge

Cached 10 minutes in `social.json`. A source that fails is listed by name in the
`feed unavailable` event; nothing is invented. Reddit and mastodon.social both
refuse unauthenticated JSON reads (403 / 422), so they are not used.


## On screen: pictures only

Nothing the person sees is written. No titles, counters, labels, captions or
explanations — the walk is a place, the dream is weather, the scroll is a feed
passing by. Keys still work (`j` join, `h`/`l` pan, `space` return, `q` quit),
they just do not advertise themselves.

The words go where they belong: the state's material is injected into the
agent's context on every turn, so the agent reads the concepts, the memories,
the posts — and reacts to them. The person gets the experience; the model gets
the content.

```
[WHAT ARRIVED WHILE YOU WERE THERE — react to this, the person only sees pictures]
  · hand (noun) → extremity (noun) · took its hypernym · "that part of a limb…"
  · bluesky · @someone · the thing nobody says about the feed
```
