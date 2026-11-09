# Antemuse

The agent can take a walk, daydream, dream, doomscroll, or get unstuck — and a
person can watch it happen in the CLI and take the same state beside it.

A state is an **act with a dose**, not a duration. A walk is six turns of work with
the frame elsewhere; a daydream is two memory pairs confronted with whether they
join; a doomscroll is three feed items; a dream is two recombinations that land; an
unstuck is one direction named. The state ends when the dose is delivered — so a
fast model finishes sooner and a slow one is not cut short. Minutes are a ceiling,
and an expiry says how much of the dose arrived.

A state is a bounded change to behaviour, not a place:

- **tools** — what the agent may still touch (open by default; `block: true` closes them, `allow:` narrows)
- **directive** — injected into the turn the state governs
- **contract** — the one line the reply is held to
- **residue** — what it carries back when the state ends

Three endings, recorded separately: `complete` (dose delivered, or the agent calls
`state(action="complete")`), `returned` (you typed `/return`), and `expired` (the
ceiling passed first: "expired before its dose: 2 of 3").

Documentation authority:

- `docs/brd.md` — business intent and Ryan's quoted requirements.
- `docs/requirements.md` — operating detail and BR-to-implementation traceability.
- `docs/spec.md` — shipped behaviour, architecture, evidence, drift, and change log.
- `specs/changes/creative-state-evidence/spec.md` — governing spec for the
  approved experimental exploration work (library only; not runtime-active).

The BRD governs intent; the operating document must agree with it. The spec and
implementation/tests govern what actually ships.

## What it says without being asked

There is no `/break` and no strain score. A recommendation is a **measured** claim
or it is silence: the recommender reads counters the plugin already keeps and names
the state that fits — a tool failing three times in a row is a walk, a source
failing twice in four turns is a doomscroll, sixty turns is a dream, a stretch twice
your own measured median is a daydream, and a repo with no commits and no spec is an
unstuck. Every line carries the counter that justified it, and arrives at most once
per cooling window (45 minutes by default).

`core/mood.py` measures and never names; `core/recommend.py` names. One owner, so
two inferences cannot argue in the same turn.

## The panel

What you see depends on where you are standing:

- `antemuse` (the `bin/antemuse` launcher) hands the screen to the takeover:
  wordless full-screen imagery and live keys.
- In chat, entering a state posts its card as its own message — one picture, no
  caption, by design (BR-5). It posts on entry, not continuously.
- Where the terminal cannot draw, the text frame carries the record instead.

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

From a clone, for development:

```bash
git clone https://github.com/roosiq/antemuse-plugin ~/antemuse-plugin
ln -s ~/antemuse-plugin ~/.hermes/plugins/antemuse
hermes plugins enable antemuse
```

Once the plugin is listed in the catalog, `hermes plugins install antemuse`
installs the reviewed pin instead. Python dependencies (`pillow`, `nltk`) are
declared in `plugin.yaml`; Hermes prepares them at install time.

## Settings

Six settings, declared in `plugin.yaml`'s `config_schema`. The Hermes desktop app
renders them as a form under **Settings ▸ Plugins ▸ Antemuse**; the same values can
be set from a shell:

```bash
hermes config set plugins.entries.antemuse.settings.recommend_enabled false
hermes config get plugins.entries.antemuse.settings
```

| setting | default | what it changes |
|---|---|---|
| `recommend_enabled` | `true` | whether the recommender may speak at all |
| `recommend_cooling_minutes` | `45` | how long one recommendation holds (10–240) |
| `long_stretch_minutes` | `0` | `0` keeps the measured threshold; otherwise 30–360 |
| `picture_enabled` | `true` | post the state's card in chat on entry |
| `picture_narrow` | `false` | force the narrow card on a wide client |
| `journal_cap` | `60` | entries kept (reduce only, 20–60) |

A setting changes how loud or how long a state is. None of them changes what a state
*is*: directives, contracts, residue, `/return`, the tool policy default and the
no-model rule are not configurable. Out-of-range values are clamped to the nearest
bound and logged once — silently changing your number is worse than telling you.

## Layout

```
plugin.yaml            manifest: 1 tool, 8 hooks, 6 bounded settings
__init__.py            hooks (pre_llm_call, pre_tool_call, post_tool_call,
                       transform_llm_output), the five state commands plus
                       /return, and the state tool
core/states.py         the five states: dose, ceiling, tools, directive, contract
core/engine.py         enter/stop/tick, tool policy, journal, residue
core/storage.py        the one active record, and the data dir it lives in
core/walks.py          walks as data: graphs and the rules for moving on them
core/sources.py        material: WordNet steps, FrameNet frames, memories, feeds
core/social.py         the live feeds a doomscroll eats
core/ticker.py         frame timer for the takeover (the state path no longer
                       waits on a clock: delivery is per turn)
core/recommend.py      the only place a state is named, from counters
core/normal.py         the measured ordinary condition (turn shape, stretches)
core/settings.py       the six settings, read through the host and clamped
core/panel.py          the printed text frame
core/photographs.py    terminal images: cells, dissolves, drift
core/walk_map.py       the walk drawn as a side-scrolling place
core/backdrop.py       pre-rendered three.js frames, replayed as blocks
core/surfaces.py       one frame, encoded per client
core/tui.py            the full-screen takeover (alt screen, truecolor, keys)
core/collider.py       Collider source strategy (library only; not runtime-wired)
core/collision.py      collision mechanics (library only; not runtime-wired)
core/llm.py            bounded auxiliary LLM calls (library only; not runtime-wired)
core/orchestrator.py   run orchestration (library only; not runtime-wired)
core/selection.py      selection aids (library only; not runtime-wired)
core/feedback.py       human feedback plumbing (library only; not runtime-wired)
core/presenter.py      prepared-artifact presentation (library only; not runtime-wired)
evaluation/            evaluation controls and harness (library only)
data/collider/         real Open Collider generated examples, CC BY 4.0,
                       with attribution (library only)
bin/antemuse           launcher on PATH
tests/                 pytest suite (renderer tests need `npm ci`; count in spec §13)
```

## Experimental exploration library

The approved creative-state-evidence work adds an exploration layer at the
library level: `evaluation/`, `core/collider.py`, `core/collision.py`,
`core/llm.py`, `core/orchestrator.py`, `core/selection.py`, `core/feedback.py`,
`core/presenter.py`, and `data/collider/`.

- These modules exist and are controller-verified at the library level. Wave 3
  has begun: the three auxiliary task routes are declared (a routing entry, not
  a call), and the four session-boundary hooks are registered. On a session
  boundary those hooks release any material bound to that session — and the
  `spark` tool action is the first thing that binds any.
- The `state(action="spark")` pass is deterministic when the experimental flag is
  off, and uses the auxiliary routes through `ctx.llm` when it is on;
  `state(action="keep")` records a verdict by handle.
- The model receives candidates; the person receives a line of counts. Keep
  those separate; never put candidate text into a human-facing line.
- `state(action="enter")` accepts optional `method`, `seed`, and `budget`, and
  refuses them unless
  `plugins.entries.antemuse.settings.experimental.enabled: true`. With the flag
  on they are recorded on the active state and consumed by nothing yet.
- No creative-quality improvement is claimed. Runtime selection scores are not
  improvement evidence; promotion requires protected comparative evaluation.
- The approved spec, plan, and tasks under
  `specs/changes/creative-state-evidence/` are the authority for this work.
- The base five-state lifecycle remains deterministic: entry, exit, expiry, tool
  restoration, and rendering never require inference.

## Verify

```bash
tools/test.sh                    # suite, temp data home, ~30 s
tools/test.sh --with-renderers   # npm ci first, so renderer tests run too
hermes plugins doctor antemuse
hermes plugins validate . --install-deps --json   # what catalog CI runs
```

`tools/test.sh` uses `uvx` with the test dependencies from
`requirements-test.txt` (`pytest`, `pillow`, `nltk`, `pyyaml`, `fastapi`) and
drops the exported `PYTHONPATH`, which otherwise breaks collection. If you prefer
your own environment: `pip install -r requirements-test.txt` then
`ANTEMUSE_STATES_HOME=$(mktemp -d) pytest tests/ -q`.

A count written here rots the moment the next test is added, and this line had
drifted twice. The current count, its date, and the exact command live in
`docs/spec.md` §13 — that is the record, this is the pointer. The suite's one
stochastic case, FLAKE-1, is documented in
`specs/changes/creative-state-evidence/tasks.md`; it is narrower than it was but
not proven gone, so a single green run is not proof of stability. Renderer tests
skip when the npm dependencies are unavailable; `--with-renderers` fetches them.

## Notes

- The `state` tool is exempt from every block, so a state can always be ended even when every other tool is closed.
  An earlier build blocked its own escape hatch and locked the agent out of its
  tools until the clock ran down.
- State is profile-wide, not per-session: the metaphor is about the agent.
- Data lives in the profile plugin data dir, overridable with
  `ANTEMUSE_STATES_HOME`.

## Disclosures

What a person should know before installing. Each line names where it happens.

- **Network reads.** `doomscroll` fetches public RSS/JSON feeds through
  `core/sources.py` and `core/social.py` (8 s timeout, `urllib`, no credentials).
  Results are cached in the plugin data dir. No other runtime path makes a
  network call.
- **Reads outside the plugin data dir.** `daydream` reads the operator's Hermes
  memory files (`~/.hermes/memories/MEMORY.md` and `USER.md`) as its material,
  and walks use the local WordNet/FrameNet corpora via `nltk`. Nothing else
  outside the plugin data dir is read at runtime.
- **Writes.** The active state record, journal, residue, cursor and render caches
  go under the plugin data dir (`data_dir()`, honouring `ANTEMUSE_STATES_HOME`);
  per-project artifacts go under `<repo>/.antemuse/`. No writes to Hermes config,
  auth, memory or another plugin's files.
- **Child process.** The full-screen takeover may spawn `node` to rasterise the
  live scene (`core/tui.py`). It inherits no shell, is not started under approval
  bypass, and the takeover falls back to cached frames when `node` is absent.
- **Dev-only tools.** Scripts under `tools/` (frame rendering, pilots, benchmark
  harnesses) make network calls and spawn browsers; they are never imported by
  plugin registration. `tools/gen_frames.py` defaults to an operator-controlled
  `SD_SERVER` on a tailnet host, not localhost.
- **Credentials.** None requested, read, stored or refreshed. No `.env`, no
  `auth.json`, no keychain, no OAuth token. Environment reads are limited to
  `ANTEMUSE_STATES_HOME`, `NLTK_DATA`, `NO_COLOR` and `TERM`.
- **Telemetry and model usage.** None. No analytics, no usage reporting, no
  hidden LLM calls on the state path. The experimental exploration library uses
  `ctx.llm` only when explicitly invoked by code that is not runtime-wired.
- **Updates.** The plugin does not update itself and never fetches its own code.
  Updates arrive through the catalog's pinned SHA and `hermes plugins update`.
- **Unattended runs.** States work under cron and the messaging gateway; a state
  that cannot draw degrades to a picture or a text record rather than waiting on
  a person.

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

## Generated photographs

`tools/gen_frames.py` renders real images through the configured `SD_SERVER`.
The default is `http://100.82.186.41:8089`, an operator-controlled tailnet GPU
host, **not localhost**. Set `SD_SERVER` explicitly to use a different endpoint.
Generated photographs take priority over the three.js and parsed-walk fallbacks.
Whether the tailnet default satisfies BR-7's same-machine requirement is OPEN in
`docs/brd.md` and `docs/requirements.md`.

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

Matrix and Telegram profiles are configured but have not been verified against
real clients.

The channel is learned from the turn's `platform` (recorded in `pre_llm_call`)
and `state(card)` picks the plan automatically; `state(card, name="discord_desktop")`
forces one. Cards are fenced in a code block because a proportional font destroys
spaced art, and `_shrink` drops art rows from the middle when the message would
exceed the channel budget.

## Scenes

Four live scenes, rendered from `tools/scene.html`:

- **walk** — a figure walking away from camera toward a low sun on a perspective grid
- **daydream** — slow, translucent low-poly blobs drifting past each other
- **dream** — two coloured spheres merging and separating inside a slow dust field
- **doomscroll** — feed cards with text bars streaming toward the camera, tilted and accelerating

The generator also retains the retired `dissociate` knot; it is not a fifth live
state.

```bash
python3 -m http.server 40813 --bind 127.0.0.1 --directory ~/antemuse-plugin &
python3 tools/render_three.py          # 5 scenes x 8 frames, ~0.6 s each
```

## What each state actually does

States are not moods: each one pulls real material on a timer and writes it into
the journal as an event (`who="state"`), so the panel fills while you watch.

| state | length | cadence | material | done with it |
|---|---|---|---|---|
| **walk** | 3 min | 9 s | **WordNet** — 117,659 synsets | a path for the person to watch and for the agent to come back from; **no material is injected** while walking, because the evidence says the gain is in leaving the frame, not in new input |
| **daydream** | 3 min | 10 s | `MEMORY.md` + `USER.md` | two memories surface; they are joined only when they share enough terms, otherwise reported adjacent |
| **doomscroll** | 8 min | 6 s | Bluesky, fosstodon, HN, Ars Technica, and The Verge, cached 10 min | random items, no synthesis — the feed talks, you consume |
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

## The walk map

`core/walk_map.py` parses the journal into a side-scrolling map: every node is a
WordNet step that happened, relation colours distinguish climbs, descents, and
lateral moves, fog marks the unwalked graph, and a person's own word can join the
path. Its default rendering is wordless.

The map is **not always the takeover image**. Generated photographs have priority
and return before the map overlay is applied; without photographs, the live
three.js renderer can own the screen instead. The map remains available through
the fallback rendering path and through `panel.render()` for a walk or idle state
without a tty. See `docs/spec.md` §§10.2 and 14 for the current contract and the
owner decision about this precedence.

When the map is visible, `h`/`l` pan, `0` resets, and `j` adds your own word.

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

or just `/walk upward`. Built-ins: `outer` (the default — jumps to the farthest
concept WordNet can find rather than the nearest edge), `wander` (all edges, one
step at a time), `upward` (hypernyms + wholes), `downward` (hyponyms + parts),
`lateral` (similar / also-see / antonym).

Measured over twenty hops from `hand`: a wander hop has a mean WordNet path
similarity of 0.34 to the node it left; an outer hop has 0.05. Seven times
farther. User walks live as JSON in `<data>/walks/<name>.json`, so they can be
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

The visual contract is no titles, counters, labels, captions, or explanations —
the walk is imagery, the dream is weather, the scroll is a feed passing by. Keys
still work (`j` join, `h`/`l` pan, `space` return, `q` quit); they do not
advertise themselves. The current note/join typing prompts are an unresolved
exception recorded in `docs/spec.md` §14.

For states that feed material, words go to the agent's context, so the agent
reads the concepts, memories, or posts and reacts to them. A walk deliberately
injects no material while work continues. The person gets the experience; the
model gets the content.

```
[WHAT ARRIVED WHILE YOU WERE THERE — react to this, the person only sees pictures]
  · hand (noun) → extremity (noun) · took its hypernym · "that part of a limb…"
  · bluesky · @someone · the thing nobody says about the feed
```
