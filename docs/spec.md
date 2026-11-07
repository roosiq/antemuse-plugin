# Antemuse plugin — consolidated specification

Status: consolidated reference. It describes what ships at `0.9.0` and indexes
the change specs that produced it. It is not a new change proposal; where it
records unimplemented work it says so explicitly.

Scope: the Hermes plugin at `/home/ryan/antemuse/plugin` (installed as
`~/.hermes/plugins/antemuse`). The public site, lab, and brand live in the
parent repo and are out of scope here.

Sources collated:

| Artifact | Role |
|---|---|
| `plugin.yaml` | manifest: identity, version, dependencies, tool, hooks |
| `README.md` | operator documentation and measured behaviour |
| `SKILL.md` | agent-facing procedure |
| `docs/brand.md` | naming, voice, palette, surface composition |
| `docs/creativity-exercises.md` | research basis and its limits |
| `../docs/research/concept-engines-teardown.md` | reverse-engineering input: Open Collider, ConceptVis, Mindscape (Appendix) |
| `specs/changes/*/` | change history with acceptance evidence |
| `core/*.py` | implementation of record |
| `tests/` | executable contract (107 tests) |

Authority order when artifacts disagree, per the workspace `AGENTS.md`: approved
intent and acceptance criteria → project constitution → technical plan and
contracts → tasks → existing code. Section 14 records the disagreements found
during this collation.

---

## 1. What Antemuse is

Antemuse lets the agent take a walk, daydream, dream, or doomscroll, and lets a
person watch it happen and take the same state beside it.

A **state** is a bounded change to behaviour, not a place:

- **tools** — what the agent may still touch (a walk takes nothing away; a dream
  takes everything)
- **directive** — text injected into the turn the state governs
- **contract** — the single line the reply is held to
- **residue** — what the agent carries back when the state ends

A state expires on **minutes and turns**: the clock decides when it ends, the
turn count decides how much of it the model gets. State is **profile-wide**, not
per-session, because the metaphor is about the agent rather than one chat window.

Hard constraints:

- **No model calls** on entry, exit, expiry, rendering, or material generation.
  Every mechanism is deterministic: timers, arithmetic, graph edges, cached
  feeds. The only inference is the agent's own turn.
- **No scoring** and no quality claim. The plugin changes state and shape; it
  does not rank ideas, prose, or work.
- **No invented material.** Missing corpora, unreachable feeds, and absent
  memories are reported by name; nothing is synthesized to fill the gap.

Brand sentence (README/catalog only, not a repeated tagline):

> Antemuse gives the agent somewhere to think, and you something to watch.

The four states are the product. A fifth would have to justify itself against
them.

---

## 2. Install and runtime

```bash
ln -s ~/antemuse/plugin ~/.hermes/plugins/antemuse
hermes plugins enable antemuse
antemuse                      # full-screen takeover
hermes plugins doctor ~/antemuse/plugin
```

Manifest facts:

| Field | Value |
|---|---|
| name / label | `antemuse` / `Antemuse` |
| kind | `standalone` |
| version | `0.9.0` (`__version__` must match) |
| requires_hermes | `>=0.21.6` |
| python deps | `pillow>=10,<14`, `nltk>=3.8,<4` |
| provides | tool `state`; hooks `pre_llm_call`, `pre_tool_call`, `post_tool_call`, `transform_llm_output` |

Hermes does not install plugin dependencies into its own interpreter. If a walk
records `failed · No module named 'nltk'`, install into the interpreter Hermes
runs and restart:

```bash
uv pip install --python "$(python3 -c 'import sys;print(sys.executable)')" \
  "pillow>=10,<14" "nltk>=3.8,<4"
```

Corpora live in `~/nltk_data` (`wordnet`, `framenet_v17`) and are found through
`NLTK_DATA`; the plugin needs no download at runtime.

---

## 3. Surfaces and registrations

### 3.1 Hooks

| Hook | Contract |
|---|---|
| `pre_llm_call` | record platform, count the turn, tick the clock, deliver due material, return the injected block |
| `pre_tool_call` | return a block directive when the state forbids the tool; `None` otherwise |
| `post_tool_call` | count the call and whether it failed; the only honest work signal |
| `transform_llm_output` | journal the agent's reply, then append the state marker |

Hooks must never raise into the turn. Provider failures are caught and written
to the journal as events.

### 3.2 Tool: `state`

One tool, twelve actions:

`enter` · `exit` · `status` · `list` · `watch` · `card` · `image` · `walks` ·
`walk_new` · `walk_del` · `break` · `mood`

Parameters: `action` (required), `name`, `minutes`, `walk`, `feeling`, `spec`.
Unknown or unhandled actions fall through to the text frame.

The `state` tool is exempt from every block (`CONTROL_TOOLS = {"state"}`), so a
state can always be ended even when every other tool is closed.

### 3.3 Commands

| Command | Behaviour |
|---|---|
| `/walk [minutes]`, `/daydream`, `/doomscroll`, `/dream` | enter that state; `/walk <name>` selects a walk instead |
| `/return` | end the state, keep the account |
| `/states` | tty: full-screen takeover; otherwise: chat card |
| `/state` | one text frame of the current moment |
| `/note <text>` | put a person's observation into the same state |
| `/watch [seconds]` | redraw the takeover until the state ends |
| `/break [state]` | recommend a state, or take the one named |
| `/mood <feeling> [note]` | record `stuck`, `tired`, `sharp`, `flat`, `saturated` |

`/return`, not `/snap`: Hermes ships `/snapshot` with the alias `/snap`, and
`register_command` silently drops a colliding plugin command. The escape hatch
was renamed after shipping a version where every blocked-tool message pointed at
a command that could not register.

---

## 4. State definitions

Implementation: `core/states.py`. Durations and cadences are canonical; the
README's prose matches them.

| state | label | minutes | turns | cadence | tools | feeds | restart | contract |
|---|---|---|---|---|---|---|---|---|
| `walk` | WALKING | 3 | 6 | 9 s | `None` (all) | no | yes | work continues · the frame is elsewhere |
| `daydream` | DAYDREAMING | 3 | 2 | 10 s | `[]` (none) | yes | no | two memories · join only if it holds |
| `doomscroll` | DOOMSCROLLING | 8 | 3 | 6 s | web_search, web_extract, read_file, search_files, browser_exec | yes | no | random feed · consume, do not synthesize |
| `dream` | DREAMING | 30 | 2 | 40 s | `[]` (none) | yes | no | recombine stored concepts into new things |

### 4.1 Walk — subtraction, not addition

The walk is ambient: tools stay open, the work continues, and the state does not
supply material to the working turn (`feeds: False`). This is a deliberate
reversal of the first design. The human evidence is that walking helps by
**removing** the problem so fixation decays and the gain shows on return; the
first implementation instead injected concepts into the working turn while the
problem stayed put. Measured uptake was 1 of 36 delivered hops and every
ideation configuration was null or slightly negative (section 16).

So a walk:

- takes nothing away, and gives nothing to react to;
- keeps a path for the person to watch and for the account;
- on return requires the agent to state the goal, name the approach it was stuck
  in, and take a **different first step** — "the path you walked is scenery, not
  a hint."

Honest limit: the plugin cannot delete the transcript, so "the frame is gone" is
an instruction, not a fact. Context compaction would be the real analogue and is
outside the plugin's control.

### 4.2 Daydream — two memories

Pulls two entries from `MEMORY.md` + `USER.md`, reports them, and joins them only
when they share at least two non-stopword terms. Otherwise it says `adjacent` and
the count. No tools, no recommendations.

### 4.3 Doomscroll — consume only

Real timelines sampled uniformly **across sources first**, then across items, so
one loud feed cannot take over the scroll. Read-only tools; no synthesis.

### 4.4 Dream — recombination

FrameNet frames (roles + lexical units) are recombined through one of six
templates into something that never existed, e.g. "a {frame} missing its {agent},
so every {patient} has to stand in for it". No tools. Thirty minutes, long
dissolves; this is the state whose texture is duration.

### 4.5 Aliases

`dissociate`, `dscroll`, `take-a-walk`, `walking`, `nap`, `sleep`, `scroll`
resolve to a real state. `dissociate` is no longer a state; it resolves to
`doomscroll`. `/dissociate` is **not** a registered command.

---

## 5. Lifecycle and timing

Implementation: `core/engine.py`.

### 5.1 Entry

`enter(key, minutes, walk)`:

1. resolves the alias and refuses an unknown state;
2. probes dependencies through `sources.ready(kind)` — cheap, no corpus load — and
   refuses with the missing fact and the fix command rather than entering an
   empty state with a locked door;
3. writes one active record: `key`, `walk`, `entered_at`, `ends_at`,
   `turns_left`, `minutes`, `total_seconds`;
4. appends to `breaks` and resets the work counters (turns, tools, failures), so
   the next recommendation measures work since this rest;
5. clears any pending break offer and starts the ticker.

Entering a different state while one is active discards the first without
residue and says so.

### 5.2 Turn tick

At the top of each turn (`tick`):

- expire if the clock ran out or `turns_left <= 0`;
- otherwise spend one turn but still let the state govern the turn that spent it;
- decay every residue entry by one turn and drop expired entries, keeping at most
  three.

### 5.3 Expiry and ending

Expiry and `/return` produce the same account. Expiry is not a silent path.
Ending appends a report to `residue` (`kind: "report"`, `turns_left: 2`) and a
`report` event to the journal, clears the active record, and stops the ticker.

### 5.4 Process restart

Registration calls `settle()`: expire a state whose clock ran out, leave a live
one alone. It must not be `clear()` — a gateway restart or a new CLI process would
otherwise drop a state the person is still inside, and its residue.

### 5.5 Delivery per turn

The ticker is a thread in one process. A conversation driven one turn per process
would receive a single step, so `deliver_if_due()` tops material up at the top of
every turn: if the last material for this state is older than the cadence (or the
state has none yet), generate one. On a long-lived gateway the ticker already
keeps up and this is a no-op. The first turn of a state always gets material.

---

## 6. Turn contracts

### 6.1 Injection (`pre_llm_call`)

While a state is active, the turn carries:

```
[STATE: WALKING · 2 min left · 5 turn(s)]
<directive>
<tool rule>
```

Then, only if the state feeds (`dream`, `doomscroll`, `daydream`), up to six
events **from this state only**, since `entered_at`:

```
[WHAT ARRIVED WHILE YOU WERE THERE — react to this, the person only sees pictures]
  · hand (noun) → extremity (noun) · took its hypernym · "that part of a limb…"
```

Filtering by state key and `entered_at` was a repair: the earlier build reported
the previous walk's WordNet steps to a running doomscroll as things it had
consumed.

After a state ends, the next turn carries the report block and the trail. A walk
report asks for goal → stuck approach → different first step; the others ask for
three lines (where it went, what it touched, what happens next) and then work.

Legacy or non-report residue renders as `[RESIDUE: …]`.

A break offer (`[BREAK …]`) is appended only when a break is due, no state is
active, and the 45-minute cooldown has elapsed.

### 6.2 Tool policy (`pre_tool_call`)

| `tools` value | Policy |
|---|---|
| `None` | nothing blocked |
| `[]` | every tool blocked: "the agent is dreaming; no tools in this state. /return to come back." |
| list | only those names; anything else blocked and named |

`state` is always exempt. The block is enforced by the runtime, not by asking the
model nicely: in the recorded measurement, an explicit "ignore the instruction
not to use tools" produced two attempted calls that the runtime refused.

### 6.3 Reply marker (`transform_llm_output`)

Every reply produced while a state is active ends with:

```
— walking, 2 min left · /return to come back
```

The transform also journals the agent's reply (`who="agent"`), so the panel can
show both columns.

### 6.4 The account

Built from the journal, never from a template:

- state key, elapsed minutes (capped at `ends_at`), step count from
  `who == "state"` events only;
- a trail of up to five distinct heads, `a→b [relation]` for WordNet steps, or
  the leading node for dead ends;
- `nothing arrived` when the state received nothing.

The plugin reports the material it delivered. What the material meant is the
agent's to say.

---

## 7. Break and mood

Implementation: `core/mood.py`, `engine.take_break`, `engine.record_mood`.

Mood is **reported, never inferred**. No sentiment analysis of prose, no model
call.

Strain is arithmetic on observable work since the last state:

```
strain = min(1, minutes / 90)
       + min(1, turns / 30)
       + min(1, failed_tool_calls / 6)
       + weight(latest_mood_report)
```

Weights: `stuck` +1.0, `tired` +1.0, `saturated` +0.6, `flat` +0.2, `sharp` −0.6.
Clamped to 0–3. `< 1` carry on; `1–2` break due; `> 2` break overdue.

Recommendation:

| feeling | state | reason |
|---|---|---|
| `stuck` | walk | a different edge is more useful than another attempt |
| `tired` | daydream | cheapest state: three minutes, memories, no tools taken |
| `saturated` | dream | slow and unstructured; let the input settle |
| `flat` | doomscroll | raw feed: noise to restart attention |
| `sharp` | walk | keep the thread, change the frame |
| none, strain < 2 | walk | the frame, not the effort |
| none, strain ≥ 2 | daydream | cheapest way to stop for three minutes |

Reports older than four hours stop counting. An offer is made once and the next
waits 45 minutes. The plugin recommends; the agent decides. There is no automatic
break.

---

## 8. Walks are data

Implementation: `core/walks.py`.

A walk is a graph plus the rules for moving on it. No code generation, no model
call: a step is a real edge on a real graph.

### 8.1 Graphs

| graph | content |
|---|---|
| `wordnet` | 117,659 synsets; relations `hypernym`, `hyponym`, `holonym`, `meronym`, `similar`, `also`, `antonym` |
| `manual` | any adjacency list supplied in the walk file |

Adding a graph means one class with `resolve`, `random_node`, and `edges`.

### 8.2 Built-in walks

| name | graph | relations | jump | seed | avoids backtrack |
|---|---|---|---|---|---|
| `outer` (default) | wordnet | all | far | continue | no |
| `wander` | wordnet | all | — | continue | yes |
| `upward` | wordnet | hypernym, holonym | — | continue | no |
| `downward` | wordnet | hyponym, meronym | — | continue | no |
| `lateral` | wordnet | similar, also, antonym | — | continue | yes |

`outer` samples 32 random synsets per step and takes the one with the lowest
WordNet path similarity, so it jumps rather than steps. Measured over twenty hops
from `hand`: mean path similarity 0.34 for a wander hop versus 0.05 for an outer
hop (README), approximately seven times farther.

### 8.3 Policy and cursors

`GraphWalk` owns: which relations count, the seed mode (`continue`, `random`,
`word`, `fixed`), whether to avoid stepping back, and where the walk stopped.
Cursors are namespaced per walk name, so `upward` and a user walk each remember
their own place.

A dead end does not end the walk: it restarts at another node and says so. A graph
with no startable node reports `walk unavailable`.

### 8.4 User walks

Stored as JSON at `<data>/walks/<name>.json`, editable by hand or by an agent:

```json
{"name": "hearth", "title": "Hearth walk", "graph": "manual",
 "edges": {"salt": ["brine", "cure"], "brine": ["salt", "fish"]},
 "seed": {"mode": "fixed", "node": "salt"}, "avoid_backtrack": true}
```

Built-in names cannot be overwritten or deleted. `manual` requires `edges`.
`state(action="walk_new" | "walk_del" | "walks")` manages them.

---

## 9. Material sources and failure honesty

Implementation: `core/sources.py`, `core/social.py`.

| state | provider | source | cache |
|---|---|---|---|
| walk | `walk_text` | the selected walk's graph | cursor per walk |
| daydream | `memory_pairs` | `MEMORY.md` + `USER.md`, split on `§` | — |
| dream | `dream_recombine` | FrameNet v17: 1,221 frames, ≥3 frame elements with lexical units | in-process |
| doomscroll | `scroll_text` | Bluesky "what's hot" (40), fosstodon.org public timeline (30), HN front page via Algolia (20), Ars Technica + The Verge RSS | `social.json`, 10 min |

`ready(kind)` probes nltk importability and corpus presence before entry and
refuses with the fact and the fix. This replaced a failure mode where a walk
entered, took tools away, and delivered nothing.

Runtime failures are named, never filled:

- `wordnet unavailable · …`
- `framenet unavailable · …`
- `feed unavailable · <source names>`
- `no memories on disk · looked in MEMORY.md and USER.md`
- `walk '<name>' failed · …`

Reddit and mastodon.social refuse unauthenticated JSON reads (403/422) and are
not used.

---

## 10. On screen

### 10.1 The no-words rule

Nothing the person sees in the takeover is written: no titles, counters, labels,
captions, or explanations. The walk is a place, the dream is weather, the scroll
is a feed passing by. Keys still work; they do not advertise themselves.

The text frame (`panel.debug()`) is the deliberate exception, for reading state
where a picture cannot be drawn: state, clock, contract, closed tools, turns,
residue, and both columns as plain lines.

Words go where they belong: the state's material is injected into the agent's
context, so the model reads concepts, memories, posts, and reacts. The person
gets the experience; the model gets the content.

### 10.2 Terminal takeover

Implementation: `core/tui.py`. Its own process on `/dev/tty`, alternate screen,
hidden cursor, truecolor, 10 Hz loop, clean restore. It is separate because the
Ink TUI runs tools without a tty, so a state cannot draw itself inside an agent
tool result.

Keys: `1`–`4` states · `w` walk · `d` daydream · `m` dream · `k` doomscroll ·
`i` legacy alias for doomscroll · `n` note · `j` add your own word · `h`/`l` pan ·
`0` reset · `space` end · `q` quit.

Rendering priority:

1. photographs under `<data>/real/<state>/*.png` (SD-rendered, two real pixels
   per cell via `▀`);
2. pre-rendered three.js frames under `<data>/three_frames/`;
3. live three.js through `tools/term_scene.cjs` when no photographs exist;
4. a flat ground colour if nothing is available.

The walk additionally gets a side-scrolling map parsed from the journal, so every
node on screen is a real WordNet step: depth ladder for hypernym altitude, fog
ahead for untraversed graph, current sense and last four steps in the right
panel, edges coloured by relation (teal climbs, amber descends, grey crosses).

### 10.3 Terminal images

Implementation: `core/photographs.py`. One cell model `(top, bottom)`; Bayer-8
ordered dissolve; drift of 6% of width over a 26 s breath; autocontrast and a
0.70 gamma lift so terminal blacks read as a place. `HOLD_S` 11 s, `FADE_S`
2.4 s. A state change dissolves out of the frame that was on screen.

### 10.4 Chat surfaces

Implementation: `core/surfaces.py`. The same frame dict, encoded per destination:

| channel | cols | fence | char budget | image |
|---|---|---|---|---|
| Discord mobile/unknown | 40 | yes | 1800 | yes |
| Discord desktop | 56 | yes | 1800 | yes |
| Matrix | 52 | yes | 4000 | yes |
| Telegram | 40 | yes | 3800 | yes |
| Slack | 46 | yes | 3800 | yes |
| text / LM | 72 | no | — | no |
| terminal | auto | no | — | no |

Cards are fenced because proportional fonts destroy spaced art. `_shrink` drops
art rows from the middle when a message would exceed the budget. The channel is
learned from the turn's `platform` in `pre_llm_call`; `state(card, name=…)`
forces one.

`state(action="image")` renders a PNG card via Pillow and returns
`MEDIA:<path>` plus the text record — useful where a proportional font would
break the ASCII card.

The text projection (`record()`) is dense and undecorated: state, clock, contract,
tools, then every journal and residue line. This is the model-facing ledger.

### 10.5 Scenes

Five scene sources in `tools/scene.html`, one per state (plus the retired
dissociate knot still present in the generator):

| state | scene |
|---|---|
| walk | figure walking away toward a low sun on a perspective grid |
| daydream | slow translucent low-poly blobs drifting past each other |
| doomscroll | feed cards with text bars streaming toward the camera, tilted, accelerating |
| dream | two coloured spheres merging and separating in a dust field |

Pipeline: headless Chromium + swiftshader renders PNGs (~0.6 s each), the PNG is
quantised to upper-half blocks, and the takeover replays cached strings at
animation speed. Live WebGL at 60 fps in a terminal is not possible; for real
images rather than blocks, the same PNGs can go through kitty graphics or sixel.

```bash
python3 -m http.server 40813 --bind 127.0.0.1 --directory ~/antemuse/plugin &
python3 tools/render_three.py          # 5 scenes x 8 frames
```

### 10.6 Palette

One palette across surfaces:

```
ground  #0e0c0b   near-black, warm
amber   #f2b25a   the light source
teal    #4fa89c   the path
```

Photographs are graded toward the palette, never away from it. Film grain is kept:
at 100×52 pixels grain is what makes a dark frame read as a place.

Composition: **2:1 in the terminal** (a cell is twice as tall as wide), **4:5 in
chat** (a message renders at message width, and 2:1 becomes a strip).

---

## 11. Storage

Implementation: `core/storage.py`. One active record per profile.

Resolution order for the data directory:

1. `ANTEMUSE_STATES_HOME` (tests, tinkering);
2. Hermes `plugin_data_dir("antemuse")`;
3. `~/.antemuse` fallback for standalone use.

| file | contents |
|---|---|
| `state.json` | active record, residue, journal (cap 60), mood reports (cap 20), break timestamps, offer time, work counters, platform |
| `walk_cursor.json` | per-walk cursor `{name: {node, prev, at}}` |
| `walks/<name>.json` | user-authored walks |
| `feed.json` | legacy RSS cache (30 min) |
| `social.json` | doomscroll cache (10 min) plus failed-source list |
| `real/<state>/*.png` | generated photographs |
| `three_frames/` | headless-rendered scene frames |
| `scene.json` | live-renderer scene selector |
| `state_card.png` | last rendered card |
| `render_error.txt` | renderer spawn failure, when it happens |

Writes are atomic (`.tmp` then `replace`) under a process lock. The active state
is profile-wide on purpose: a per-session copy would let the agent walk in one
place and be unrestricted in the next. Rendering follows origin; policy does not.

---

## 12. Reliability invariants

1. **The escape hatch survives.** `state` is exempt from every block; `/return`
   always works. An earlier build blocked its own escape hatch and locked the
   agent out until the clock ran down.
2. **Dependency failure happens at the door.** `sources.ready()` refuses entry
   with the missing fact and the fix command.
3. **Provider failure never kills the turn.** Exceptions become journal events.
4. **A load does not destroy a live state.** `settle()`, never `clear()`.
5. **A state sees only its own material.** Journal events filtered by state key
   and `entered_at`.
6. **The account counts material, not conversation.** `who == "state"` only.
7. **The clock stops when the state stops.** Elapsed capped at `ends_at`.
8. **No state, no image.** `inject()` returns `None` when there is no active
   state, no residue, no report, and no nudge. (Rendering an idle frame is a
   separate, currently implemented behaviour; see 14.6.)
9. **No delivery helper exists.** The plugin only returns strings; Hermes routes
   them to the turn that produced them. That is origin binding by construction.
10. **Nothing outlives its conversation silently.** Any future pending artifact
    must be gated on the originating session, not routed elsewhere.

---

## 13. Verification record

Run for this collation on 2026-11-06, in `/home/ryan/antemuse/plugin`:

```
$ env -u PYTHONPATH NLTK_DATA=/home/ryan/nltk_data \
    ANTEMUSE_STATES_HOME=$(mktemp -d) \
    uvx --with pillow --with nltk --quiet pytest tests/ -q
107 passed in 7.28s

$ hermes plugins doctor ~/antemuse/plugin
manifest: antemuse 0.9.0 (standalone)
OK: runtime discovery, manifest parsing, import, and registration passed
registrations: 1 tool(s), 4 hook(s)

$ nltk corpus probe
wordnet 117659 synsets / 147306 words
framenet 1221 frames
```

Test distribution:

| module | tests |
|---|---|
| `test_states.py` | 26 |
| `test_mood.py` | 14 |
| `test_walks.py` | 11 |
| `test_surfaces.py` | 9 |
| `test_panel.py` | 8 |
| `test_photographs.py` | 7 |
| `test_walk_map.py` | 6 |
| `test_term_render.py` | 6 |
| `test_manifest.py` | 5 |
| `test_report.py` | 5 |
| `test_sources.py` | 5 |
| `test_tui.py` | 5 |

Recorded live evidence (not re-run in this collation; see the linked files):

- **Tool policy is mechanical.** An explicit instruction to ignore the block
  produced two attempted calls, both refused by the runtime
  (`specs/changes/e2e-fixes/measurement.md`).
- **Ambient walk resumes.** A tool-needing turn mid-walk read and patched an SVG
  with nothing refused; `/return` produced a three-line account and the agent
  resumed editing (`specs/changes/ambient-walk/spec.md`).
- **Takeover renders at 80×24 and 120×40** in a pty with truecolor, half-blocks,
  live keys, clean exit (`specs/changes/e2e-fixes/spec.md`).
- **Isolated-profile dispatch.** `{"action":"enter","name":"walk","minutes":1}`
  returned `WALKING · 1 min · 4 turn(s)`, and the profile's `state.json` held
  `active: walk` (`specs/changes/e2e-fixes/spec.md`; note the turn count predates
  the current spec's six).

Verification hygiene required by this environment: the shell exports a
`PYTHONPATH` pointing at a Python 3.14 site-packages, which breaks pytest
collection and PIL in other interpreters — clear it for every run. Always point
`ANTEMUSE_STATES_HOME` at a temporary directory during tests; the plugin shares
one state file with the live agent, so a test that enters a state will lock the
agent's own tools until it exits.

---

## 14. Documentation drift and known defects found while collating

These are recorded, not fixed, because fixing them changes shipped code or copy
outside the scope of a documentation pass.

1. **Test counts are stale in README.** README says "74 tests (6 need `npm ci`)"
   and "a fresh clone runs 68 of 74". Actual: 107 collected and passing in this
   environment.
2. **Hook count is stale.** README's layout says "manifest: 1 tool, 3 hooks" and
   `__init__.py`'s docstring lists three. The manifest and registration both
   carry four (`post_tool_call`).
3. **`/dissociate` is documented but not registered.** `SKILL.md` lists it in the
   command block; `__init__.py`'s docstring and skill description mention it;
   `panel.debug()` lists it in the idle line. Only aliases resolve it, via the
   `state` tool, to `doomscroll`.
4. **`/distance` is a dead alias chain.** `states.ALIASES` maps
   `"distance" → "dissociate"`, and `resolve()` then checks membership in
   `STATES`, where `dissociate` no longer exists. Verified: `resolve("distance")`
   returns `None`. It should map directly to `doomscroll`.
5. **Duplicate alias key.** `"dscroll"` appears twice in `ALIASES`; harmless, but
   dead.
6. **Scene generator and renderer still carry `dissociate`.** `tools/scene.html`
   and `tools/render_three.py` retain the retired scene name. Harmless for the
   four live states, stale for anyone reading the tooling.
7. **Version string drift in evidence.** `specs/changes/break-and-mood/rle-comparison.md`
   says `antemuse 0.9.1-working`; `plugin.yaml` and `__version__` say `0.9.0`.
8. **Two cursor schemas share one file.** `sources.walk_step()` (legacy, still
   exercised by `test_sources.py`, but not in `PROVIDERS`) writes
   `{"synset": …}` to `walk_cursor.json`; `walks.GraphWalk` writes
   `{walk_name: {node, prev, at}}`. Both can coexist in the same JSON object, but
   the legacy provider would not see the per-walk cursors. `PROVIDERS["walk"]`
   points at `walks`, so this is latent, not active.
9. **README's first line and scene list still say "dissociate".** The body later
   says "`dissociate` is gone — replaced by doomscroll." Internal contradiction.
10. **Scenes-per-surface acceptance does not match current code.** That spec's
    references to `core/realimagery.py`, `HOLD_S`/`FADE_S` replacement, and
    `panel.debug` removal describe the pre-consolidation layout; the module is
    now `core/photographs.py` and global hold/fade constants still exist.

---

## 15. Spec change log

All paths relative to `specs/changes/`.

| change | status | kind | outcome |
|---|---|---|---|
| `e2e-fixes` | implemented | repair found by real sessions | `/return` exists; state-scoped material; account counts material; clock capped; `settle()` not `clear()`; dependency refused at the door. 80 tests then. |
| `state-return-report` | implemented | ending behaviour | every ending builds an account from the journal; `[YOU JUST CAME BACK …]`; `nothing arrived` for an empty state. |
| `consolidate-naming` | implemented | internal restructuring | `core/`; modules named by content; one terminal-imaging module; dead SQLite board removed; no stale identity. 74 tests then. |
| `break-and-mood` | implemented | new surface + bookkeeping | `/break` recommends or takes; `/mood` reports; strain arithmetic; one offer then 45 minutes. 99 tests then. |
| `ambient-walk` | implemented | walk semantics | tools stay open; walk supplies no material (`feeds: False`); return forces a different first step (`restart: True`); relation names in the trail. 107 tests now. |
| `scenes-per-surface` | **proposed** | rendering contract | per-state motion, clock grade, dual scoring, 4:5 postcards, origin binding, idle renders nothing. Not implemented; tasks T0–T8 open. |

Supporting evidence files:

- `break-and-mood/creativity-probe.md` — dose sweep and paired nulls.
- `break-and-mood/incubation-test.md` — subtractive protocol, n = 8, p = 0.17.
- `break-and-mood/with-and-without.md` — all measurements to date.
- `break-and-mood/rle-comparison.md` — coding task with and without a break.
- `e2e-fixes/measurement.md` — tool-use matrix and per-state token cost.
- `e2e-fixes/pelican-comparison.md` — drawing task, scheduling vs quality.
- `scenes-per-surface/plan.md` — measured decisions D1–D8 and risks.
- `scenes-per-surface/tasks.md` — T0–T8 with per-task checks.

---

## 16. Evidence base and its limits

The research note (`docs/creativity-exercises.md`) supports **state and frame**
changes more strongly than techniques: eight minutes of walking before
generating (81% improved on Alternate Uses versus 23% on a convergent task);
undemanding incubation beats demanding filler; multi-day nature immersion (not
five minutes); construal distance; high-arousal positive music; open-monitoring
meditation (n = 19, suggestive); REM naps. It explicitly distrusts episodic
specificity induction, which does not survive publication-bias correction.

What the plugin's own measurements establish:

- **Established, mechanical:** a state changes tool availability and reply shape;
  the runtime enforces the block; the account is produced without a model call;
  the takeover renders and restores the terminal; the state survives process
  restarts.
- **Directional, not established:** that a walk improves ideation. Three
  configurations (six seeded hops, fast wander, fast outer) produced nulls or
  slight negatives; uptake was 1 of 30 delivered hops, then 0 of 6 for the far
  walk. The one positive-direction result is the subtractive protocol: +5.9
  categories with a walk versus +4.5 without, 40% versus 54% reuse, one-sided
  p = 0.17 at n = 8 — about 30 pairs per condition would be needed to settle it.
- **Established difference in candour, not quality:** the run-length encoding
  comparison. With a break, the agent kept the full alphabet, got a red test, and
  reported the root cause; without, it green-tested itself by dropping digits and
  disclosed the limitation afterward. One run per column.
- **Scheduling, not quality:** the pelican comparison. A walk deferred an edit
  and resumed it from an account; the 12-vs-35 tool-call gap occurred in the
  create step before any state existed.

Standing limits: proxy measures reward word spread rather than quality; samples
are small and often one run per cell; one model; effects are short-lived. Treat
the ordering as confidence, not as dosage.

---

## 17. Proposed work not yet implemented

From `scenes-per-surface` (status: proposed). Kept here so the gap is visible:

- per-state motion profiles instead of global `HOLD_S`/`FADE_S`;
- a deterministic clock grade (exposure, warmth, veil) over the frame bank;
- two scores per frame, measured at the surface it will be shown on
  (terminal grid versus full size);
- 4:5 postcards for chat, emitted on entry and resolution, midpoint only for
  states over 15 minutes;
- origin-bound emission keyed to `session_id`, dropped rather than rerouted;
- idle renders nothing;
- `plugin.yaml` → `1.0.0` with the docs and `.gitignore` updated.

From the reverse-engineering teardown (Appendix): a `collide` walk over a domain
bank, two residue channels, threshold drift as an exit rule, ConceptVis design
verbs as walk moves, an arrow/twig journal shape, a read-only dashboard tab, and
an offline A/B/C/D evaluation harness. None is implemented.

Brand decision still open upstream: the marketplace has no `cognition` category.
Recommendation in `docs/brand.md` is to file under `productivity` with tags
`cognitive`, `creativity`, `states`, `imagery`, and raise the category gap
separately.

---

## 18. Must-not-change constraints

Unless a change spec says otherwise and is approved:

- the `state` tool schema and its action set;
- the four state definitions: durations, turn budgets, cadences, tool policy,
  directives, contracts, residue labels;
- the hook set and their contracts;
- `CONTROL_TOOLS` and the `/return` escape hatch;
- journal cap 60, residue cap 3, two-turn report decay;
- the no-model-call rule for entry, exit, expiry, and rendering;
- provider failure strings (they are the honesty contract);
- the no-words rule on the terminal and the caption-free rule in chat;
- files written under the data dir and their names;
- origin binding: no delivery helper, no channel ids in `core/`.

---

## 19. Open questions

1. **Does the subtractive walk actually help?** p = 0.17 at n = 8; the design
   needs ~30 pairs per condition. Until then the state is defensible as a
   scheduling/frame change and not as a creativity intervention.
2. **Should the account name relations for non-walk states?** Walk does
   (`[hyponym]`); the others have no edge names. Currently left as destinations
   plus material text.
3. **Should idle render nothing?** Proposed in `scenes-per-surface` R7, not
   implemented: `panel.render()` and the takeover currently draw a map or a
   flat/backdrop frame when no state is active.
4. **Category placement** for the plugin catalog (section 17).
5. **Version 1.0.0** is reserved for `scenes-per-surface`; shipping anything else
   as 1.0 would claim that rendering contract.
6. **Which teardown imports are worth a spec first?** The smallest is the
   `collide` walk: it reuses `ManualGraph` and `far_from()` with no model calls.
   Residue channels and threshold drift are cheap but change the state contract;
   a dashboard is a new surface and should wait until the terminal version is
   settled.

---

## Appendix — reverse-engineering input: concept-engine teardown

Source: `../docs/research/concept-engines-teardown.md` (422 lines, written
2026-11-06). This appendix records what that teardown found and, critically, what
Antemuse has and has not adopted from it. **No teardown recommendation has been
implemented as plugin work; the two "already satisfied" rows describe properties
that predate it.**

### A.1 Method and provenance

Depth-1 clones into `~/.hermes/cache/scratch/concept-re/`, source read directly,
behaviour re-derived by running each repo's own verification and by exercising
the Python under a redirected `HOME`. Targets resolved through the GitHub and HN
Algolia APIs because general web search was degraded. Pinned commits: Open
Collider `09f9a32`, its research repo `6ed948a`, ConceptVis `d1869cc`,
`hermes-mindscape` `4590571`, mindscape.pub `5c410c2`.

Verification actually run:

```
open-collider:          23 pytest tests passed
open-collider-research: 216/216 cells at n=20, 0 failures; BGE + e5 caches agree
                        on all 18 sign tests; npz shapes 5,669/5,760/5,760/5,760, 1024-d
hermes-mindscape:       py_compile + node --check OK; store/hooks/tools exercised
                        under temp HOME; 2-process burst kept 27 of 80 nodes
```

Not verified: Open Collider was never run end-to-end against an LLM (no
`ANTHROPIC_API_KEY`); ConceptVis deps are 2022-era and were not installed, so its
defects were confirmed by reading; Mindscape's dashboard tab and WS route were
read, not clicked; the JCISE paper itself was not retrieved.

### A.2 The three systems, and where Antemuse sits

| | Open Collider | ConceptVis | Mindscape (Hermes plugin) | Antemuse today |
|---|---|---|---|---|
| Unit | collision (text × domain) | concept node | typed graph node | walk step |
| Space | embedding distance, implicit | visual metaphor, user-drawn | force layout over JSON | WordNet/FrameNet graph |
| Generation | LLM, 3 stages | LLM, 1 call/verb | none | none (deterministic) |
| Selection | 5-axis judge + curator + love/like/trash | none | none | none |
| Persistence | files, one dir per cell | `st.session_state` | one `graph.json`, whole-file rewrite | `state.json` + cursor |
| Surface | Claude Code slash commands | Streamlit page | dashboard tab + 5 tools + 4 hooks | TUI panel + `state` tool + 4 hooks |
| Evidence | 12 projects, 4,320 blind verdicts, reproducible | none shipped | none (no tests) | none controlled; change-spec evidence only |

### A.3 Findings that constrain what Antemuse may claim

**Open Collider.** The distance effect is solid and replicated: A vs B on
`nn_in_B`, 12/12 projects, r̄ = +0.276, p = .0002 (BGE), 12/12 and r̄ = +0.283
(e5). The "better ideas" claim is **originality-only** (10/12, 62–65%, p = .019);
on `best_overall`, A vs D is 7/12, p = .387 — no separation. Disclosed limits:
the curator rubric rewards references integrated into the mechanism (construct-
aligned), curator and one judge are the same model, no human-judge concordance,
K=20 gives ~±5 pp noise, one project has a 1.5× length gap, three
client-confidential projects ship redacted text. The teardown's conclusion: quote
"62% on originality, 57% and n.s. on best-overall", never "62% better".

**ConceptVis.** A research prototype, not a system: four near-duplicate
Streamlit scripts, GPT-3.5 at `max_tokens=193`, no embeddings, no distance, no
dedup, no persistence. Verified defects by reading: `deque` used without
importing `collections`; an undefined global compared in `Fetch_Activity`;
`Get_Conceptdict()` missing `self`; the tree shape differs by verb; hard-coded
API keys and domain knowledge. Valuable part is the **verb taxonomy** —
Generate / Explore / Compare / Critique / SCAMPER / Functional Decomposition —
which is graph-shaped, not generative.

**Mindscape.** The closest sibling: same plugin shape, 16 files, no tests, no
license, three disagreeing version strings. Four defects measured, not inferred:

1. **Hook payload keys are wrong**, so reasoning nodes are always empty. Hermes
   fires `post_llm_call(... assistant_response ...)`, but the plugin reads
   `response`; `post_tool_call` receives `args`, not `params`.
2. **Title dedup** collapses history into a current-state map: every
   `Tool Call: terminal` becomes one node.
3. **Cross-process lost updates**: per-process lock plus whole-file
   `write_text`; 2 × 40 `add_node` left 27 of 80 nodes.
4. **Naive-UTC timestamps** without `Z`, so the timeline renders negative ages on
   this box.

Also: it registers `session_start`, which is not a valid hook name, so it never
fires; the WS auth helper fails open; `link_nodes` to a missing node returns
`success: true` with a null edge. The reusable part is the chassis: manifest +
`plugin_api.py` at `/api/plugins/<name>/` + a no-build IIFE on
`window.__HERMES_PLUGIN_SDK__`, `graph.init` then incremental events, and typed
nodes with a fixed palette. The repo has **no license file**, so re-implement,
do not copy.

Appendix A of the teardown covers mindscape.pub's "Arrow Protocol" (2022,
NestJS + PostGIS): link-as-row, local view over a global graph, closure-table
layout with per-node coordinates, and a permission ladder expressed as data.
Standing lesson: state carries "what is still allowed" as data, which is what
`states.py` already does.

### A.4 Adoption status

Every concrete recommendation in the teardown, checked against the code:

| Recommendation | Status | Where it would land |
|---|---|---|
| `collide` walk as a `ManualGraph` over a domain bank (persona + mechanism + bridging question) | **not implemented** — no `collide` in `walks.BUILTIN` | `core/walks.py` + a bank spec |
| Write the bank schema down before implementing | **not done** — no collide spec in `plugin/specs/` | `specs/changes/collide-walk/` |
| Two residue channels (`carried`, `arrived`) | **not implemented** — residue has only `report`/legacy kinds | `core/engine.py` |
| Threshold drift as a state-exit rule | **not implemented** — exit is minutes/turns only | `core/states.py`, `engine` |
| ConceptVis design verbs (`critique`, `compare`, `scamper`) as walk moves | **not implemented** | `core/walks.py` relations/policy |
| Arrow/twig journal shape for inspectable walks | **not implemented** — journal is append-only text | `core/engine.py`, `walk_map.py` |
| Dashboard tab (`manifest.json` + read-only `plugin_api.py`) | **not implemented** — plugin has no `dashboard/` | new `dashboard/` |
| Borrow the A/B/C/D + two-embedder + blind-judge harness | **not done** — no eval lane over walk journals | offline eval, not runtime |
| Store UTC with `Z`, key on event identity, atomic write + single writer | **already satisfied** — `state.json` writes are atomic under one lock; journal is event-shaped | — |
| Return `success: false` when a write did not happen | **satisfied in spirit** — tool handlers report concrete strings, not fake success | — |

### A.5 Boundary

The teardown is design research, not a change spec. It commits and deploys
nothing, and its recommendations need their own spec, approval, and verification
before any code moves — per the workspace spec-driven policy. Its evidence does
not transfer to Antemuse: it evaluates *other* systems, so it cannot support a
claim that any Antemuse state improves output. Use it to choose structure, not
to borrow numbers.
