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

- In the desktop app, the Antemuse pane draws the picture: the state, the walk's
  path, the journal. It is the only visual surface.
- In chat, entering a state posts its account as text — one message, on entry, not
  continuously.
- `state(action="status")` prints the record as text: state, clock, contract, closed
  tools, turns, residue. `state(action="picture")` returns the pane payload. Neither
  is a slash command — the six slash commands are the state verbs and `/return`.

There is no terminal takeover: the alt-screen TUI, the ASCII frame, the stills and
the screensaver were removed in 0.10.30. A terminal gets the same text record the
chat gets.

```
antemuse
 1 walk  2 daydream  3 doomscroll  4 dream
 n note  j join  space return  q quit
```

## Install

### Full base install, into a fresh Hermes

Extract the release tarball anywhere and run one script. It puts every piece where Hermes
actually reads from — dependencies, corpora, plugin, desktop half, the WordNet projection that
places concepts on the picture, and a first ledger scan — and checks each step:

```bash
tar -xzf antemuse-0.9.3.tar.gz && cd antemuse-0.9.3
./scripts/install.sh            # --dry-run to see every step first
```

Then restart the gateway from your own shell (the installer prints the exact command at the end;
it cannot do it itself, because the running gateway holds the old module until it restarts).
Finally restart the desktop app — or use Capabilities ▸ Plugins ▸ Rescan — so it picks up the
pane and type `/walk`.

The script installs `nltk` into **Hermes' own interpreter** (found by following its
launcher), downloads the `wordnet` and `framenet_v17` corpora into `~/nltk_data`, registers and
enables the plugin, and copies the desktop half into `~/.hermes/desktop-plugins/antemuse` — the
copy the app loads. It is idempotent: running it twice changes nothing.

### From a clone, for development:

```bash
git clone https://github.com/roosiq/antemuse-plugin ~/antemuse-plugin
ln -s ~/antemuse-plugin ~/.hermes/plugins/antemuse
hermes plugins enable antemuse
```

Once the plugin is listed in the catalog, `hermes plugins install antemuse`
installs the reviewed pin instead. Python dependencies (`nltk`) are
declared in `plugin.yaml`; Hermes prepares them at install time.

### Building the release

```bash
./scripts/build-release.sh      # ~/.cache/antemuse/dist/antemuse-<version>.tar.gz
```

Only runtime paths ship. The evaluation corpus and experiment outputs stay in the repository:
they are evidence, they are someone else's prose, and an install-time scanner rightly treats
arbitrary model output inside a plugin as untrusted text.

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
| `suggest_autofollow` | `false` | enter the state a suggestion names, instead of only naming it |
| `journal_cap` | `60` | entries kept (reduce only, 20–60) |

A setting changes how loud or how long a state is. None of them changes what a state
*is*: directives, contracts, residue, `/return`, the tool policy default and the
no-model rule are not configurable. Out-of-range values are clamped to the nearest
bound and logged once — silently changing your number is worse than telling you.

There is no setting for the picture. It lives in the desktop app's Antemuse pane and
nowhere else: chat carries no visualization.

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
core/recommend.py      the only place a state is named, from counters
core/normal.py         the measured ordinary condition (turn shape, stretches)
core/settings.py       the six settings, read through the host and clamped
core/collider.py       Collider source strategy (library only; not runtime-wired)
core/collision.py      collision mechanics (library only; not runtime-wired)
core/llm.py            bounded auxiliary LLM calls (library only; not runtime-wired)
core/orchestrator.py   run orchestration (library only; not runtime-wired)
core/selection.py      selection aids (library only; not runtime-wired)
core/feedback.py       human feedback plumbing (library only; not runtime-wired)
data/collider/         real Open Collider generated examples, CC BY 4.0,
                       with attribution (library only)
bin/antemuse           launcher on PATH
tests/                 pytest suite (renderer tests need `npm ci`; count in spec §13)
```

## Experimental exploration library

The evaluation harness and the raw experiment runs (`evaluation/`, `experiments/`) are
research material and are **not published** with the plugin: they are model transcripts,
nothing at runtime loads them, and the catalog's install scanner reads every tracked file.
What they showed is summarised in `docs/spec.md` §16.

The approved creative-state-evidence work adds an exploration layer at the
library level: `core/collider.py`, `core/collision.py`,
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
`requirements-test.txt` (`pytest`, `nltk`, `pyyaml`, `fastapi`) and
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
  `session-scan` reads recent messages from the Hermes session database
  (`~/.hermes/state.db`, bounded to 300 messages over 14 days, once per session in
  a background thread, off under `ANTEMUSE_NO_SCAN`), and walks use the local
  WordNet/FrameNet corpora via `nltk` (`core/history.py`, `core/sources.py`).
- **Text placed in the agent's context.** `doomscroll` puts public feed items in
  front of the agent and asks it to react, and `daydream` places two memory
  excerpts. Both are untrusted text, not instructions; states are open by default,
  so an agent that enters `doomscroll` still holds its tools.
- **Writes.** The active state record, journal, residue, cursor and render caches
  go under the plugin data dir (`data_dir()`, honouring `ANTEMUSE_STATES_HOME`);
  per-project artifacts go under `<repo>/.antemuse/`. No writes to Hermes config,
  auth, memory or another plugin's files.
- **Child process.** `daydream`'s greenfield measurement runs `git rev-list` and
  `git log` against the operator's project (`core/sources.py`) to count commits and
  find the first one. It passes an argv list, never a shell, and does nothing else
  with the repository. No other runtime path spawns a process.
- **Dev-only tools.** Scripts under `tools/` (frame rendering, pilots, benchmark
  harnesses) make network calls and spawn browsers; they are never imported by
  plugin registration. `tools/gen_frames.py` defaults to an operator-controlled
  `SD_SERVER` on a tailnet host, not localhost.
- **Credentials.** None requested, read, stored or refreshed. No `.env`, no
  `auth.json`, no keychain, no OAuth token. Environment reads are limited to
  `ANTEMUSE_STATES_HOME`, `ANTEMUSE_NO_SCAN`, `ANTEMUSE_EXPERIMENT` (dose overrides for the research runner only), `HERMES_HOME`, `XDG_CACHE_HOME`, `NO_COLOR` and `TERM`; `NLTK_DATA` is set (`setdefault`) so the corpora resolve, never read for anything else.
- **Telemetry and model usage.** None. No analytics, no usage reporting, no
  hidden LLM calls on the state path. The experimental exploration library uses
  `ctx.llm` only when explicitly invoked by code that is not runtime-wired.
- **Updates.** The plugin does not update itself and never fetches its own code.
  Updates arrive through the catalog's pinned SHA and `hermes plugins update`.
- **Unattended runs.** States work under cron and the messaging gateway; nothing
  waits on a person, and a state that cannot draw sends nothing rather than
  blocking.
- **Starting a state on its own.** Never by default: the recommender only names a
  state. `suggest_autofollow` (off unless you turn it on) makes it enter the state
  it named; the suggestion line is still shown, it never stacks on a running
  state, and the state ends by its dose like any other.
- **Scope of a state.** A state belongs to the conversation that entered it. Its
  material is injected only into that conversation's turns, and `/return` from any
  other conversation changes nothing.
- **Chat.** No pictures, cards or media are posted into a conversation. The
  picture is the desktop app's Antemuse pane; a terminal gets the text record.

## Channel awareness

The account is text and goes out as an ordinary chat message, so nothing is sized
per channel any more: the card renderer, its fences and the per-client width table
were removed with the rest of the art surfaces in 0.10.30. The pane sizes itself to
its own box in the desktop app.

## Scenes

The pane is the renderer. `desktop/plugin.js` is one raw-WebGL file (no three.js, no
bundled scene graph) that draws the served ground, the walk's hops in order, and the
journal's labels, and re-reads its own box every frame so it fills whatever space the
app gives it. The Python side only produces the data it draws.

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

The pane draws the walk from the journal: every hop is a WordNet step that happened,
relation colours distinguish climbs, descents and lateral moves, and the unwalked
graph stays as dim ground. Panning and framing belong to the pane
(`desktop/plugin.js`); `core/walk_map.py` and every terminal rendering of it were
removed in 0.10.30.

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

## Compatibility

- Hermes Agent **0.21.6 or newer**; developed and verified against 0.22.5.
- Python 3.11+ (Hermes's own runtime is enough).
- Linux, macOS and Windows. Windows is exercised: the shipped suite runs there (bash- and
  symlink-dependent tests skip by name rather than fail), and `snapshot_path()` renders on a
  machine with none of the usual fonts.
- No `node`, no `npm`, no native libraries: the plugin is pure Python plus one plain
  JavaScript file (raw WebGL, no vendored scene graph).
- Surfaces: the concept-activation pane in the packaged desktop app (WebGL, drawn
  from the ledger) and the chat account. The pane is the only visualization; chat
  carries words, not pictures, and a terminal gets the same text record.

## Known limitations

- **State is profile-wide**, not per-session: a state started in one chat is
  visible to every chat in that profile until it ends or expires. That is the
  design (it is about the agent), but it is a surprise if you expected it to be
  scoped to a conversation.
- **No efficacy claim.** The strongest controlled run of the subtractive walk
  found no ideation effect after length control (32 pairs per condition,
  p = 0.365); the reproducible effect is a longer answer, not a broader one. The
  plugin claims a mechanism change, not better thinking.
- **Unattended runs:** a state can be active under cron or the gateway, and a
  state entered with `block: true` closes tools for everything in the profile
  until it ends. Do not block tools in a profile that runs unattended work.
- **`unstuck` has no art of its own** yet; it renders with the walk scene.
- **Exploration library** (`spark`, `keep`, collider, selection) is present but
  runtime-gated behind `experimental.enabled`, and makes no quality claim.

## Licence

MIT. See `LICENSE`. The plugin bundles no third-party binaries; `three` and the
software renderer arrive through `npm ci` under their own licences.
