# Antemuse

The agent can take a **walk**, **daydream**, **dream**, **doomscroll**, or get
**unstuck** — four states that change what the work looks like, and one that names a
direction. You can take the same state beside it, and the desktop app's pane shows it
happening.

A state is an **act with a dose**, not a duration. A walk is six hops with the frame
elsewhere; a daydream is two memory pairs confronted with whether they join; a doomscroll is
three feed items; a dream is two recombinations that land; an unstuck is one direction named.
The units arrive one a second from the moment the state exists, so a six-hop walk is served in
about six seconds and closes on the turn that uses it — the dose ends the state, not the clock.
Minutes are a stall guard for a state nobody is turning over, and an expiry says how much of
the dose arrived.

A state is a bounded change to behaviour, not a place:

- **tools** — what the agent may still touch (open by default; `block: true` closes them, `allow:` narrows)
- **directive** — injected into the turn the state governs
- **contract** — the one line the reply is held to
- **residue** — what it carries back when the state ends

Three endings, recorded separately: `complete` (dose delivered, or the agent calls
`state(action="complete")`), `returned` (you typed `/return`), and `expired` (the
ceiling passed first: "expired before its dose: 2 of 3").

## The six commands

```
/walk [minutes]      /daydream      /dream
/doomscroll          /unstuck       /return
```

That is the whole command surface. Agents use the tool instead:
`state(action="enter", name="walk")`, `state(action="exit")`,
`state(action="status")`, `state(action="break")`, `state(action="list")`.

## What it says without being asked

There is no `/break` and no strain score. A recommendation is a **measured** claim or it
is silence: the recommender reads counters the plugin already keeps and names the state
that fits — a tool failing three times in a row is a walk, a source failing twice in four
turns is a doomscroll, sixty turns is a dream, a stretch twice your own measured median is
a daydream, and a repo with no commits and no spec is an unstuck. Every line carries the
counter that justified it, and arrives at most once per cooling window (45 minutes by
default).

`core/mood.py` measures and never names; `core/recommend.py` names. One owner, so two
inferences cannot argue in the same turn.

## The pane

The picture lives in the desktop app's **Antemuse pane** and nowhere else.

- The pane draws the state, the walk's hops in order, and the journal's labels. It is the
  only visual surface.
- In chat, entering a state posts its account as text — one message, on entry.
- `state(action="status")` prints the record as text: state, clock, contract, closed
  tools, turns, residue.

There is no terminal takeover: the alt-screen TUI, the ASCII frame, the baked stills, the
card renderer and the screensaver were removed in 0.10.30. A terminal gets the same text
record the chat gets.

## Install

### Full base install, into a fresh Hermes

Extract the release tarball anywhere and run one script. It puts every piece where Hermes
actually reads from — dependencies, corpora, plugin, desktop half, the WordNet projection
that places concepts on the picture, and a first ledger scan — and checks each step:

```bash
tar -xzf antemuse-<version>.tar.gz && cd antemuse-<version>
./scripts/install.sh            # --dry-run to see every step first
```

Then restart the gateway from your own shell (the installer prints the exact command at
the end; it cannot do it itself, because the running gateway holds the old module until it
restarts). Finally restart the desktop app — or use Capabilities ▸ Plugins ▸ Rescan — so it
picks up the pane and type `/walk`.

The script installs `nltk` into **Hermes' own interpreter** (found by following its
launcher), downloads the `wordnet` and `framenet_v17` corpora into `~/nltk_data`, registers
and enables the plugin, and copies the desktop half into
`~/.hermes/desktop-plugins/antemuse` — the copy the app loads. It is idempotent: running
it twice changes nothing.

### From a clone, for development

```bash
git clone https://github.com/roosiq/antemuse-plugin ~/antemuse-plugin
ln -s ~/antemuse-plugin ~/.hermes/plugins/antemuse
hermes plugins enable antemuse
```

Once the plugin is listed in the catalog, `hermes plugins install antemuse` installs the
reviewed pin instead. Python dependencies (`nltk`) are declared in `plugin.yaml`; Hermes
prepares them at install time.

### Building the release

```bash
./scripts/release.sh <version>  # bump, changelog, catalog entry, validated pack
./scripts/build-release.sh      # ~/.cache/antemuse/dist/antemuse-<version>.tar.gz
```

Only runtime paths ship. Research material does not: `experiments/` and `evaluation/` hold
model transcripts, nothing at runtime loads them, and an install-time scanner rightly
treats arbitrary model output inside a plugin as untrusted text. The one exception is
`experiments/idea-states/`, which publishes its report, plots, measurement scripts and
per-model aggregates — scores, not prose. See `experiments/idea-states/EVIDENCE.md`.

## Settings

Six settings, declared in `plugin.yaml`'s `config_schema`. The desktop app renders them as
a form under **Settings ▸ Plugins ▸ Antemuse**; the same values can be set from a shell:

```bash
hermes config set plugins.entries.antemuse.settings.show_recommendations true
hermes config get plugins.entries.antemuse.settings
```

| setting | default | what it changes |
|---|---|---|
| `recommend_enabled` | `true` | whether the measurement runs and `/break` can name a state |
| `show_recommendations` | `false` | whether a suggestion is shown to the person and offered to the agent |
| `recommend_cooling_minutes` | `45` | how long one recommendation holds (10–240) |
| `suggest_autofollow` | `false` | enter the state a suggestion names, instead of only naming it |
| `long_stretch_minutes` | `0` | `0` keeps the measured threshold; otherwise 30–360 |
| `journal_cap` | `60` | entries kept (reduce only, 20–60) |

A setting changes how loud or how long a state is. None of them changes what a state *is*:
directives, contracts, residue, `/return`, the tool policy default and the no-model rule
are not configurable. Out-of-range values are clamped to the nearest bound and logged once
— silently changing your number is worse than telling you.

There is no setting for the picture. It lives in the pane and nowhere else.

## Layout

```
plugin.yaml            manifest: 1 tool, 8 hooks, 6 bounded settings
__init__.py            hooks, the five state commands plus /return, the state tool
core/states.py         the five states: dose, ceiling, tools, directive, contract
core/engine.py         enter/stop/tick, tool policy, journal, residue
core/storage.py        the one active record, and the data dir it lives in
core/walks.py          walks as data: graphs and the rules for moving on them
core/sources.py        material: WordNet steps, FrameNet frames, memories, feeds
core/social.py         the live feeds a doomscroll eats
core/recommend.py      the only place a state is named, from counters
core/normal.py         the measured ordinary condition (turn shape, stretches)
core/settings.py       the six settings, read through the host and clamped
core/history.py        the session and memory material daydream reads
core/atlas.py          concept projection: where a concept sits, for the pane
core/graph.py          the concept graph behind the pane's ground
core/activation.py     activation records for a concept the work touched
core/report.py         the account a state leaves behind
core/recall.py         bounded recall over recent turns
core/session.py        per-session bookkeeping for the hooks
core/runtime.py        host access, data dir, defensiveness at the boundary
core/options.py        option resolution and clamping
core/mood.py           the measurement that never names anything
core/collider.py       Collider source strategy (library only; not runtime-wired)
core/collision.py      collision mechanics (library only; not runtime-wired)
core/llm.py            bounded auxiliary LLM calls (library only; not runtime-wired)
core/orchestrator.py   run orchestration (library only; not runtime-wired)
core/selection.py      selection aids (library only; not runtime-wired)
core/feedback.py       human feedback plumbing (library only; not runtime-wired)
core/seeding.py        how a state's first material is chosen
data/collider/         real Open Collider generated examples, CC BY 4.0,
                       with attribution (library only)
desktop/plugin.js      the pane: one raw-WebGL file, no three.js
tests/                 pytest suite
```

## Verify

```bash
tools/test.sh                    # suite in a temp data home
tools/test.sh --with-renderers   # npm ci in the harness dir, then mount the pane
hermes plugins doctor antemuse
hermes plugins validate . --install-deps   # what catalog CI runs
```

`tools/test.sh` uses `uvx` with the test dependencies from `requirements-test.txt`
(`pytest`, `nltk`, `pyyaml`, `fastapi`) and drops the exported `PYTHONPATH`, which
otherwise breaks collection. If you prefer your own environment:
`pip install -r requirements-test.txt` then
`ANTEMUSE_STATES_HOME=$(mktemp -d) pytest tests/ -q`.

No test count is written here: a number in a README rots the moment the next test is
added. Run the command. `TESTING.md` has the manual recipes and what each check proves.

## What each state actually does

States are not moods: each one pulls real material on a timer and writes it into the
journal as an event (`who="state"`), so the pane fills while you watch.

| state | length | cadence | material | done with it |
|---|---|---|---|---|
| **walk** | 3 min | 9 s | **WordNet** — 117,659 synsets | a path for the person to watch and for the agent to come back from; **no material is injected** while walking, because the evidence says the gain is in leaving the frame, not in new input |
| **daydream** | 3 min | 10 s | `MEMORY.md` + `USER.md` | two memories surface; they are joined only when they share enough terms, otherwise reported adjacent |
| **doomscroll** | 8 min | 6 s | Bluesky, fosstodon, HN, Ars Technica, and The Verge, cached 10 min | random items, no synthesis — the feed talks, you consume |
| **dream** | 30 min | 40 s | **FrameNet** — 1,221 frames | a frame's roles and lexical units recombined into a thing that does not exist |
| **unstuck** | 1 turn | — | the repo's own state: commits, specs, what failed last | one direction named, and the counter that justified it |

Sources are honest about failure: missing WordNet says `wordnet unavailable`, missing
FrameNet says `framenet unavailable`, an unreachable feed says `feed unavailable`, and none
of them invents content.

Corpora live in `~/nltk_data` (`wordnet`, `framenet_v17`) and are found through
`NLTK_DATA`, so the plugin needs no download at runtime. The walk keeps its place in
`walk_cursor.json` and refuses to step straight back where it came from.

### Coming back

Every state ends with an account of itself, built from the journal rather than from a
template: state, minutes, step count, and the trail, condensed to four-word heads.

```
WALKING ended · walk 1m · 3 step(s) · salt to brine → brine to fish → fish to salt
Come back and tell the person what happened in there.
```

The account is kept as residue (`kind: "report"`), journalled as an event named `report`,
and the next turn opens with `[YOU JUST CAME BACK — say what happened in there, in your own
words, before anything else]`. Expiry and `/return` produce it identically; a state that
received nothing says `nothing arrived`.

## The walk map

The pane draws the walk from the journal: every hop is a WordNet step that happened,
relation colours distinguish climbs, descents and lateral moves, and the unwalked graph
stays as dim ground. Panning and framing belong to the pane.

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

or just `/walk upward`. Built-ins: `outer` (the default — jumps to the farthest concept
WordNet can find rather than the nearest edge), `wander` (all edges, one step at a time),
`upward` (hypernyms + wholes), `downward` (hyponyms + parts), `lateral` (similar /
also-see / antonym).

Measured over twenty hops from `hand`: a wander hop has a mean WordNet path similarity of
0.34 to the node it left; an outer hop has 0.05. Seven times farther. User walks live as
JSON in `<data>/walks/<name>.json`, so they can be edited by hand or generated by an agent.

`GraphWalk` (in `core/walks.py`) owns the policy: which relations count, what seed to start
from (`continue`, `random`, `word`, `fixed`), whether to avoid stepping back, and where it
stopped. Cursors are namespaced per walk, so `upward` and `salt circle` each remember their
own place. A dead end does not end the walk — it picks up at another node and says so.

## Doomscroll sources

Real timelines, sampled uniformly across sources so one loud feed cannot take over the
scroll:

- **Bluesky** — `public.api.bsky.app` "what's hot", 38 posts per pull
- **Mastodon** — `fosstodon.org` public timeline, 30 posts
- **Hacker News** — Algolia front page, 20 stories
- **RSS** — Ars Technica and The Verge

Cached 10 minutes in `social.json`. A source that fails is listed by name in the
`feed unavailable` event; nothing is invented. Reddit and mastodon.social both refuse
unauthenticated JSON reads (403 / 422), so they are not used.

## Disclosures

What a person should know before installing. Each line names where it happens.

- **Network reads.** `doomscroll` fetches public RSS/JSON feeds through `core/sources.py`
  and `core/social.py` (8 s timeout, `urllib`, no credentials). Results are cached in the
  plugin data dir. No other runtime path makes a network call.
- **Reads outside the plugin data dir.** `daydream` reads the operator's Hermes memory files
  (`~/.hermes/memories/MEMORY.md` and `USER.md`) as its material, `session-scan` reads recent
  messages from the Hermes session database (`~/.hermes/state.db`, bounded to 300 messages
  over 14 days, once per session in a background thread, off under `ANTEMUSE_NO_SCAN`), and
  walks use the local WordNet/FrameNet corpora via `nltk` (`core/history.py`,
  `core/sources.py`).
- **Text placed in the agent's context.** `doomscroll` puts public feed items in front of
  the agent and asks it to react, and `daydream` places two memory excerpts. Both are
  untrusted text, not instructions; states are open by default, so an agent that enters
  `doomscroll` still holds its tools.
- **Writes.** The active state record, journal, residue, cursor and render caches go under
  the plugin data dir (`data_dir()`, honouring `ANTEMUSE_STATES_HOME`); per-project artefacts
  go under `<repo>/.antemuse/`. No writes to Hermes config, auth, memory or another plugin's
  files.
- **Child process.** `unstuck` and `daydream`'s greenfield measurement run `git rev-list` and
  `git log` against the operator's project (`core/sources.py`) to count commits and find the
  first one. They pass an argv list, never a shell, and do nothing else with the repository.
  No other runtime path spawns a process.
- **Dev-only tools.** Scripts under `tools/` (screenshots, graph inspection, projection
  rebuilds) are run by hand and are never imported by plugin registration.
- **Credentials.** None requested, read, stored or refreshed. No `.env`, no `auth.json`, no
  keychain, no OAuth token. Environment reads are limited to `ANTEMUSE_STATES_HOME`,
  `ANTEMUSE_NO_SCAN`, `ANTEMUSE_EXPERIMENT`, `HERMES_HOME`, `XDG_CACHE_HOME`, `NO_COLOR` and
  `TERM`; `NLTK_DATA` is set (`setdefault`) so the corpora resolve, never read for anything
  else.
- **Telemetry and model usage.** None. No analytics, no usage reporting, no hidden LLM calls
  on the state path. The experimental exploration library uses `ctx.llm` only when
  explicitly invoked by code that is not runtime-wired.
- **Updates.** The plugin does not update itself and never fetches its own code. Updates
  arrive through the catalog's pinned SHA and `hermes plugins update`.
- **Unattended runs.** States work under cron and the messaging gateway; nothing waits on a
  person, and a state that cannot draw sends nothing rather than blocking.
- **Starting a state on its own.** Never by default: the recommender only names a state.
  `suggest_autofollow` (off unless you turn it on) makes it enter the state it named; the
  suggestion line is still shown, it never stacks on a running state, and the state ends by
  its dose like any other.
- **Scope of a state.** A state belongs to the profile, not to a conversation. Its material
  is injected only into the conversation that entered it, and `/return` from another
  conversation changes nothing.
- **Chat.** No pictures, cards or media are posted into a conversation. The picture is the
  pane; a terminal gets the text record.

## Compatibility

- Hermes Agent **0.21.6 or newer**; developed and verified against **0.23.1**.
- Python 3.11+ (Hermes's own runtime is enough).
- Linux and macOS are the verified platforms. On Windows the installer and runtime are pure
  Python and the plugin loads; the suite's bash- and symlink-dependent tests skip there by
  name, and the pane is unverified.
- No `node`, no `npm`, no native libraries at runtime: the plugin is pure Python plus one
  plain JavaScript file for the pane (raw WebGL, no vendored scene graph). `npm ci` is
  needed only to run the pane harness (`tools/desktop_harness/mount.mjs`).
- Surfaces: the pane in the packaged desktop app, and the chat account. The pane is the only
  visualization.

## Known limitations

- **State is profile-wide**, not per-session: a state started in one chat is visible to every
  chat in that profile until it ends or expires. That is the design (it is about the agent),
  but it is a surprise if you expected it scoped to a conversation.
- **No efficacy claim.** The strongest controlled run of the subtractive walk found no
  ideation effect after length control (32 pairs per condition, p = 0.365); the reproducible
  effect is a longer answer, not a broader one. The plugin claims a mechanism change, not
  better thinking.
- **Unattended runs:** a state can be active under cron or the gateway, and a state entered
  with `block: true` closes tools for everything in the profile until it ends. Do not block
  tools in a profile that runs unattended work.
- **Exploration library** (`spark`, `keep`, collider, selection) is present but runtime-gated
  behind `experimental.enabled`, and makes no quality claim.
- **The pane needs the desktop app.** In a terminal or a chat-only install there is no
  picture at all — by design, since 0.10.30.

## Elsewhere in this repository

- `CHANGELOG.md` — what changed, release by release.
- `SKILL.md` — the agent-facing instructions Hermes loads.
- `SECURITY.md` — the threat model in one page.
- `TESTING.md` — the manual checks and what each one proves.
- `CONTRIBUTING.md` — how to change something here.
- `experiments/idea-states/BENCHMARK.md` — what a state does to a list of fifty ideas.

## Licence

MIT. See `LICENSE`. The plugin bundles no third-party binaries.
