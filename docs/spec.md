# Antemuse plugin — consolidated specification

Status: consolidated reference. It describes what ships at `0.9.0` and indexes
the change specs that produced it. It is not a new change proposal; where it
records unimplemented work it says so explicitly.

Scope: the Hermes plugin at `/home/ryan/antemuse-plugin` (installed as
`~/.hermes/plugins/antemuse`). The public site, lab, and brand live in the
parent repo and are out of scope here.

Sources collated:

| Artifact | Role |
|---|---|
| `plugin.yaml` | manifest: identity, version, dependencies, tool, hooks |
| `README.md` | operator documentation and measured behaviour |
| `docs/brd.md` | business-intent authority and Ryan's quoted requirements |
| `docs/architecture.md` | the functional plan with per-component status — the map, not the record |
| `docs/requirements.md` | operating detail and BR-to-implementation traceability |
| `SKILL.md` | agent-facing procedure |
| `docs/brand.md` | naming, voice, palette, surface composition |
| `docs/creativity-exercises.md` | research basis and its limits |
| `../docs/research/concept-engines-teardown.md` | reverse-engineering input: Open Collider, ConceptVis, Mindscape (Appendix) |
| `specs/changes/*/` | change history with acceptance evidence |
| `core/*.py` | implementation of record |
| `tests/` | executable contract — the current count and date live in §13, never here |

Authority order when artifacts disagree, per the workspace `AGENTS.md`: approved
intent and acceptance criteria → project constitution → technical plan and
contracts → tasks → existing code. Within the business document set, `docs/brd.md`
owns quoted intent, `docs/requirements.md` owns operating detail and traceability,
and this spec owns shipped behaviour. Section 14 records the disagreements found
during this collation and the current documentation pass.

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

The five states are the product. A sixth would have to justify itself against
them.

---

## 2. Install and runtime

```bash
ln -s ~/antemuse-plugin ~/.hermes/plugins/antemuse
hermes plugins enable antemuse
antemuse                      # full-screen takeover
hermes plugins doctor antemuse
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
| `on_session_end` · `on_session_finalize` · `on_session_reset` · `on_session_delete` | release any prepared material bound to that session; each logs a failed release and never raises (Wave 3, J1) |

Hooks must never raise into the turn. Provider failures are caught and written
to the journal as events.

### 3.2 Tool: `state`

One tool, fourteen actions:

`enter` · `exit` · `status` · `list` · `walks` · `walk_new` · `walk_del` ·
`break` · `mood` · `spark` · `keep` · `watch` · `card` · `image`

The last three are surfaces rather than decisions: they stay handled for older callers
but are not part of the description a model reads. `spark` and `keep` replaced the
`/spark`, `/keep` and `/again` commands (see `specs/changes/command-surface`).

Parameters: `action` (required), `name`, `minutes`, `walk`, `feeling`, `spec`,
`goal`, `verdict`, `candidate`,
and — Wave 3, J1 — optional `method` (`collide` · `deep` · `chaos` · `spark`),
`seed`, and `budget` (`calls` 0–32, `tokens` 0–200000, `seconds` 1–900). The
three experimental fields are refused unless
`plugins.entries.antemuse.settings.experimental.enabled` is true. They are
recorded on the active state, and since J2 the run that consumes them is
`state(action='spark', goal=…)` — the fields still do not start a run by themselves,
because a run needs a goal and entry has none.
Unknown or unhandled actions fall through to the text frame.

The `state` tool is exempt from every block (`CONTROL_TOOLS = {"state"}`), so a
state can always be ended even when every other tool is closed.

### 3.3 Commands

| Command | Behaviour |
|---|---|
| `/walk [minutes]`, `/daydream`, `/doomscroll`, `/dream` | enter that state; `/walk <name>` selects a walk instead |
| `/return` | end the state, keep the account |

**Six commands, and nothing else.** Everything a person previously typed has moved:
their message is journalled as a `person` entry while a state runs (no `/note`), the
recommendation line arrives in the turn by itself (no `/break`), mood is reported in
words and recorded by the agent (no `/mood`), the picture arrives with the state (no
`/state`, `/states`, `/watch`), and exploration runs through the `state` tool —
`spark`, `keep` (no `/spark`, `/keep`, `/again`).

`/return`, not `/snap`: Hermes ships `/snapshot` with the alias `/snap`, and
`register_command` silently drops a colliding plugin command. The escape hatch
was renamed after shipping a version where every blocked-tool message pointed at
a command that could not register.

---

## 4. State definitions

Implementation: `core/states.py`. **A state ends on its dose, not on the clock** —
the minutes column is a ceiling. `specs/changes/semantic-states`; the
README's prose matches them.

| state | label | ceiling | turns | dose (the act) | tools | feeds | restart | contract |
|---|---|---|---|---|---|---|---|---|
| `walk` | WALKING | 3 min | 6 | 6 turns worked | **free** — `block: true` blocks nothing | no | yes | work continues · the frame is elsewhere |
| `daydream` | DAYDREAMING | 3 min | 2 | 2 memory pairs | **free** — `block: true` blocks every tool | yes | no | two memories · join only if it holds |
| `doomscroll` | DOOMSCROLLING | 8 min | 3 | 3 feed items | **free** — `block: true` leaves web_search, web_extract, read_file, search_files, browser_exec | yes | no | random feed · consume, do not synthesize |
| `dream` | DREAMING | 30 min | 2 | 2 recombinations | **free** — `block: true` blocks every tool | yes | no | recombine stored concepts into new things |

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

### 4.1 Where a state starts

Entry is specified in `specs/changes/state-entry`: `walk` draws its seed from a
**5 : 3 : 2** mix of project terms, conversation terms and deliberate randomness, and
`dream` from **6 : 2 : 2 memory : project : random** — a dream opens on something the
person said or stored, never on a random frame,
chosen by a deterministic hash of (state, entry time, counter), skipping terms the state
already used, and recording `seed=<source>:<term>` on the first line. `daydream` starts
from the conversation (memory files are enrichment), and `doomscroll` stays undirected —
that is its point.

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
every turn: one item per turn while the dose is unfinished (or the
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

| `tools` value | What the state's own spec says |
|---|---|
| `None` | nothing to withhold — free even when the entry asks to block |
| `[]` | every tool — enforced only when the entry asks with `block: true`; the refusal reads "the agent is dreaming; no tools in this state. /return to come back." |
| list | only those names, others named as blocked — also only under `block: true` |

**The default is `free` for every state.** `enter(..., block=True)` opts in;
`allow=[...]` narrows further and is refused without `block` rather than silently
ignored. One `_effective_tools()` decision feeds the injection, the pre-tool hook and
the panel, so the three cannot disagree.

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

**One owner.** `core/mood.py` measures and never recommends: minutes since the last
state, turns, failures, the run of consecutive failures, and any reported feeling. It has
no score, no `due`, no suggested state. (The old `strain` sum — minutes/90 + turns/30 +
fails/6, clamped to 0–3 — is gone: it was a timer that named a state, and it told a
healthy 122-minute session that "a daydream fits" with no evidence beyond the clock.)

Naming a state is `core/recommend.py`'s job alone, one line per cooling window, each
line carrying the counter that justified it:

| pattern | evidence | state |
|---|---|---|
| new project | < 3 commits and no spec | unstuck |
| reported | a mood report inside 4 hours | mapped from the report (`stuck`→walk, `tired`→daydream, `saturated`→dream, `flat`→doomscroll, `sharp`→walk) |
| loop | same tool failed ≥ 3× in a row | walk |
| data wall | ≥ 2 source failures in the last 4 turns | doomscroll |
| saturation | ≥ 60 turns, or ≥ 3 open decisions | dream |
| long stretch | ≥ 90 min since the last state and ≥ 10 turns | daydream |
| grind | ≥ 20 turns and a failure in the last 3 | daydream |
| rut | same state twice inside 10 min | a different state |

Reports older than four hours stop counting. One recommendation per 45 minutes.
Silence when nothing is measured. The plugin recommends; the agent decides. There is no
automatic break.

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
| `vault` | wordnet | all | vault (two far jumps) | continue | no |
| `run3` | wordnet | all | run:3 (three edges per arc) | continue | yes |
| `orbit` | wordnet | all | orbit (near, far, near, far) | continue | yes |
| `composite` | wordnet | all | all five, in rotation | continue | yes |

`composite` is not a sixth policy: it runs `run:3 → far → near → vault → orbit` in a fixed
rotation, so one walk covers ground by running, stepping, jumping and vaulting, and every
line says which navigation produced it. Measured at 40 trials/cell it delivers 95–98 % novel
concepts and 100 % distinct lines at doses 3/6/12, with freshness 87/94/91 % — slightly below
`outer`'s ~100 % because an arc deliberately revisits its own neighbourhood inside one step.
It is a coverage and legibility choice, not a novelty winner.

`vault` widens the far search to 64 samples and jumps twice per step, reporting the
concept it jumped *past*; `run3` reports three adjacent edges as one arc; `orbit`
alternates one near edge with one far jump. They exist because measuring the generator
(§15, `state-settings-experiment`) showed the navigation policy, not the dose, decides
whether material is new: at 40 trials per cell, adjacent `wander` delivered 68–71 % novel
concepts with freshness falling to 80 % at dose 12, while `outer` delivered 98–99 % novel
at 100 % freshness and 100 % distinct lines at every dose. Going further out is not a taste
— it is the difference between a walk that revisits its own neighbourhood and one that
does not.

`outer` samples 32 random synsets per step and takes the one with the lowest
WordNet path similarity, so it jumps rather than steps. Measured over twenty hops
from `hand`: mean path similarity 0.34 for a wander hop versus 0.05 for an outer
hop (README), approximately seven times farther.

### 8.2a What each state is for, and the measure that fits it

The states do not share one goal, so they do not share one number. The goals are Ryan's
definitions of 2026-11-08 and are authoritative; full statements — what each implies, where
the code stands, what must change — are in [`docs/goals.md`](goals.md), with the re-alignment
tracked in `specs/changes/state-goals/`.

| state | goal (Ryan, 2026-11-08) | what the state now does | measure that fits | measured |
|---|---|---|---|---|
| walk | distant **and connected** concepts for the current task | every step names the seed it started from and the hops back (`↩ N hops from <anchor>: a → …`), and says when the ledger has been there before | path distance, a resolvable chain back, and the cross-session repeat rate | far jump similarity **0.05** vs adjacent **0.34**; chain back built and tested; destinations repeating a concept from the previous session **9.0 % → 7.8 %** with ledger steering, over 600 steps each (`tools/measure_state_gaps.py`) |
| daydream | synthesize, introduce new thoughts and possibilities | every pair carries one possibility built from its own distinctive terms, hypothesis-phrased; a pair that does not join yields one from the gap | join rate on distinctive terms, and one possibility per item | join **6 % → 100 %**, median **3.5** shared distinctive terms; possibility present on every item |
| doomscroll | distraction via social-media stupidity and comedy | satire lanes only, with work-looking items excluded and counted (`[13 skipped as work]`) | distinct lines across sessions, and comedic share | distinct **48/22/11 % → 80/72/70 %** at dose 1/3/6; comedic share **not measured** |
| dream | process the day, connect tasks across projects | connects the day's commit subjects across repos, plus concepts **circling across sessions** the commits cannot see; invention is the labelled fallback | connections per dream, both sides named, and distinct frame pairs when it invents | connections **40/40 real** (both sides named, shared terms) after reading changed file names and widening a thin day to a stated window; invention is now the labelled fallback; cross-frame invention **100 % distinct pairs, overlap 0.0000** |
| unstuck | recommend one new thing from history + the concept graph | one direction resting on last commit subject, one graph edge, memory, and the ledger's circling/unused concepts; missing inputs named together | exactly one recommendation, with history citation and graph path | one direction at dose 1; **100/100** directions carry evidence; **28 %** distinct across 100 runs; graph, history and ledger paths all reached |

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
| walk | `walk_text` (seeded) | the selected walk's graph | cursor per walk |
| daydream | `memory_pairs` | recent turns captured from `pre_llm_call` (any provider) → `MEMORY.md` + `USER.md` when present | the built-in memory provider only; an external bank is out of reach and named |
| dream | `dream_recombine` (seeded) | FrameNet v17: 1,221 frames, ≥3 frame elements with lexical units | in-process |
| doomscroll | `scroll_text` | Bluesky "what's hot" (40), fosstodon.org public timeline (30), HN front page via Algolia (20), Ars Technica + The Verge RSS | `social.json`, 10 min |

`ready(kind)` probes nltk importability and corpus presence before entry and
refuses with the fact and the fix. This replaced a failure mode where a walk
entered, took tools away, and delivered nothing.

Runtime failures are named, never filled:

- `wordnet unavailable · …`
- `framenet unavailable · …`
- `feed unavailable · <source names>`
- `no memories yet · nothing said in this conversation, and no built-in MEMORY.md`
- `no memories on disk · memory provider is 'hindsight', which this state cannot read (built-in MEMORY.md only)`
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

Words go where they belong: for states that feed material, the state's material
is injected into the agent's context, so the model reads concepts, memories,
posts, and reacts. A walk feeds nothing into the working turn. The person gets
the experience; the model gets the content. Note/join entry currently introduces
a temporary typing prompt in the takeover; that deviation is recorded in §14.

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

`core/walk_map.py` parses a side-scrolling, wordless map from the journal, so
every node is a real WordNet step and edges retain their relation colours. It is
a fallback, not a guaranteed takeover layer. When photographs exist,
`imagery_frame()` returns them before applying the map overlay; when no
photographs exist, the live three.js renderer can own the screen instead. The
map renders through the remaining `imagery_frame()` fallback and through
`panel.render()` for a walk or idle state without a tty. Whether photograph
priority should suppress the parsed walk is an owner decision in §14.

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
forces one. Matrix and Telegram profiles are configured but have not been
verified against real clients.

`state(action="image")` renders a PNG card via Pillow and returns
`MEDIA:<path>` plus the text record — useful where a proportional font would
break the ASCII card.

The text projection (`record()`) is dense and undecorated: state, clock, contract,
tools, then every journal and residue line. This is the model-facing ledger.

### 10.5 Scenes

Five scene sources in `tools/scene.html`: four live states plus the retired
dissociate knot still present in the generator:

| state | scene |
|---|---|
| walk | figure walking away toward a low sun on a perspective grid |
| daydream | slow translucent low-poly blobs drifting past each other |
| doomscroll | feed cards with text bars streaming toward the camera, tilted, accelerating |
| dream | two coloured spheres merging and separating in a dust field |

Pipeline: headless Chromium + swiftshader renders PNGs (~0.6 s each), the PNG is
quantised to upper-half blocks, and the takeover replays cached strings at
animation speed. A scene can also be **derived** rather than baked: §10.6 renders the concept
map from the ledger's own servings, with no Chromium and no model in the loop. Live WebGL at 60 fps in a terminal is not possible; for real
images rather than blocks, the same PNGs can go through kitty graphics or sixel.

```bash
python3 -m http.server 40813 --bind 127.0.0.1 --directory ~/antemuse-plugin &
python3 tools/render_three.py          # 5 scenes x 8 frames
```

### 10.6 Activation — the concept map as a state visual

A state serves concepts turn by turn, and the ledger records every serving with its move, session
and timestamp. `core/activation.py` turns that record into weights, and
`tools/activation_render.py` draws them on the concept map: the semantic projection dimmed, the
concepts that are firing lit, radius and brightness by weight, and **no text anywhere**.

The model, and why each part is there:

| rule | value | why it is that and not something else |
|---|---|---|
| decay | `exp(-age / 180 s · ln2)` | a concept served three minutes ago is half as hot as one served now |
| floor | 0.25 of the hottest on screen | below this a concept is noise, not an activation |
| freshest wins | `max` per concept, not a sum | summing lets a word repeated all day outrank the one firing right now |
| only the past | a serving later than the frame's moment is not active | without this every concept in a long session lights up in frame one |
| frames | at real serving timestamps, evenly sampled | sessions are bursty; evenly spaced clock time spends most frames on the gaps between turns |

The time bound belongs in the SQL, not applied after a `LIMIT`: filtering the newest N rows by
time made every early frame of a long session empty.

Measured on the session of 2026-11-08 09:18: **263 concepts touched, 66 concurrently lit at the
peak**, over ten frames — an arc that rises, breathes and fades.

```bash
python3 tools/activation_render.py --session <id> --frames 10 --gif
python3 tools/activation_render.py --move walk --frames 8      # one state only
```

**The desktop pane draws it as images.** `core/activation_stills.py` renders three JPEG stills
(960×600) of the map at three moments of the state's arc and caches them for 45 s;
`GET /api/plugins/antemuse/state` returns them as `stills`, and the pane paints them through the
same cross-fading `<img>` layers the baked scenes use. `GET /art/{state}/{file}` serves only files
the plugin itself wrote — the name and filename are matched, never joined from user input, and a
refusal is a 404 rather than a 200 carrying a description of the refusal.

The state narrows the map only when that state has servings of its own in this session. A walk
entered a minute ago has none yet, and the session's firings are still what is on the map: falling
back to them is honest, and an empty field would be a lie about the picture.

No ASCII. The pane is a picture surface, and the map is drawn as one.

**The look is three.js, at bake time.** Each still goes through the official `EffectComposer` in
headless Chromium: `UnrealBloomPass`, a chromatic-separation `ShaderPass`, film grain and a
vignette, finished by `OutputPass`. Three.js is vendored under `vendor/three-bake/` (r180 core +
the passes it needs) and runs only in `tools/activation_post.html` — the plugin imports no three
and ships no shader to a surface. The passes change how the picture looks, never what it says, and
nothing is drawn on top of it.

`tools/postprocess_activation.py` drives that page through `tools/shoot.mjs`, one browser for the
whole batch and one server for the batch, waited on before the first request — three launches back
to back was where it was flaky. If no browser or three build is present, the stills keep their
plain render and the reason is named; a missing effect never costs the picture.

The look is settable at bake time without editing the page: `?grain=`, `?vignette=` and `?bloom=`
override the defaults (0.055 / 0.72 / 0.95). Recognising the grain is the loudest of the three is
the reason it is a parameter rather than a constant — at 0.055 a flat dark patch carries a
standard deviation of about 17 levels and the JPEG grows from 219 KB to 1.19 MB.

**How the pane reaches them.** The pane is called **Antemuse** in the sidebar; it is not called "State" — the state is what the
pane shows, not what the pane is. The desktop pane is a `file://` page: it cannot fetch
`/api/plugins/antemuse/art/...` without the gateway's token, and the app's `ctx.rest` goes over IPC
rather than the page's network stack, so no `<img>` can ride on it. The pane therefore reads the
stills as local files from `plugin-data/antemuse/activation/<state>/` — the sibling directory of
the plugins install, resolved from the module URL and, when the module is bundled and
`import.meta.url` is not a file, from the installed path, exactly as the baked scenes are.
`/state` still returns `stills` (HTTP) and `files` (`file://`) for clients that can use either.

Because a `file://` page cannot list a directory, each still is written twice: a stamped
`f0-<stamp>-post.jpg` for evidence, and a stable `f0.jpg`..`f2.jpg` for the pane to ask for by a
name it can predict. `fresh()` returns only the stamped set. A probe `<img>` decides between the
live stills and the baked scene, so a state with nothing baked falls back instead of going blank.

**Status: PARTIAL.** The path is wired end to end (stills written, served, painted, with a
fall-through to the baked scene when nothing is firing), but it has not been seen in the running
desktop app: verification so far is the backend route, the harness mount and the stills
themselves. See §17.2.

### 10.7 Palette

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

**Current count: 905 tests** (`pytest -q`, 2026-11-08). This line is the only
authoritative number in this document; the blocks below are dated evidence from the
day they were taken, and later blocks are history, not claims. `tools/spec_audit.py
--counts` compares this line against the suite and fails when they disagree.

Run for this collation on 2026-11-06, in `/home/ryan/antemuse/plugin`:

```
$ env -u PYTHONPATH NLTK_DATA=/home/ryan/nltk_data \
    ANTEMUSE_STATES_HOME=$(mktemp -d) \
    uvx --with pillow --with nltk --quiet pytest tests/ -q
107 passed in 7.28s

$ hermes plugins doctor antemuse
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

### Verification record, 2026-11-08 (desktop backend and desktop half)

```
$ pytest tests/ -q
684 passed in 8.6s

$ hermes plugins doctor antemuse
registrations: 1 tool(s), 8 hook(s)

$ python -c "desktop_surface_hits(Path('.'))"
[]

$ node mount.mjs        # jsdom, the real desktop/plugin.js
mount: 9 properties PASS (label, counts, contract, frame text, decorative art,
       poll tick, unmount, idle, unavailable)
```

The desktop route was also exercised end to end over HTTP against a real state in a
temporary home: idle `active: null`; after `enter("daydream")` label `DAYDREAMING`,
`tools.mode: none`, 179 s, 2 turns; after `stop()` back to null. Not verified: the app.

### Verification record, 2026-11-08 (truncation made visible)

Run in `/home/ryan/antemuse-plugin` with the same hygiene:

```
$ pytest tests/ -q
669 passed in 8.53s
```

Records written by `evaluation/run.py` now carry `record_schema` (`record-2`),
each candidate's `finish_reason`, a per-candidate `truncated` flag, and a
record-level `truncated_candidates` list. The default selector passes over a
candidate that stopped at the token ceiling when a complete one exists. A cached
record from an older schema is treated as a miss and re-run, and
`tools/run_shard.py` refuses to count one as coverage — an old record cannot tell
a cut-off answer from a finished one, so replaying it would present half a cell as
whole. Nine tests bind this; the full run above is the single dated record.

### Verification record, 2026-11-08 (surface repair and Wave 3 J1)

Run in `/home/ryan/antemuse/plugin` with the hygiene above:

```
$ pytest tests/ -q
660 passed in 8.30s
```

Recorded 2026-11-08 after Wave 3 J2/J2b/J3 and its audit: 627 passed twice in a row (660 with Wave 4 K1/K2), and
`hermes plugins doctor antemuse` still reports `1 tool(s), 8 hook(s)`. The earlier
591-test record above this one belongs to the surface repair, not to this state.

One earlier run of the same suite failed `tests/test_walks.py::test_outer_hops_are_farther_than_wander_hops` — FLAKE-1, recorded below and predating this
work. Its sample was widened from 16 to 64 steps on 2026-11-08 after measuring the distribution
(it now holds 30/30 where it held 94% of the time); it is narrower, not proven gone. Two consecutive runs are not proof of stability.

```
$ hermes plugins doctor antemuse
manifest: antemuse 0.9.0 (standalone)
OK: runtime discovery, manifest parsing, import, and registration passed
registrations: 1 tool(s), 8 hook(s)
```

Surface measurements taken from the live scene banks (40×8 cells, the `discord`
profile):

| scene | non-space cells, before | after |
|---|---|---|
| walk | 1% | 18% |
| daydream | 8% | 23% |
| doomscroll | 19% | 32% |
| dream | 11% | 11% |

The card PNG grew from 84 bright pixels of 90,692 (0.09%) to 950 of 111,548
(0.9%) for the same walk state. Both numbers are well below a photograph; the
point is that the frame is now legible as a picture rather than a blank
rectangle.

---

## 14. Documentation drift and known defects found while collating

Documentation corrections made in this pass are marked resolved. Runtime files
were not changed; behavioural defects and owner decisions remain open.

Items 15–18 were added on 2026-11-08 from a live observation of the running
plugin (a real walk entered, rendered, and exited), not from reading the code,
and were repaired the same day under `specs/changes/surface-repair/`. 15–17 were
one class of defect: the model-facing surfaces were correct and the
human-facing ones were not, which is why four review passes over the code did
not find them.

1. **Resolved — test counts were stale in README.** (Recurred and re-resolved 2026-11-08: README had drifted to 564. It no longer carries a count at all; §13 is the only place a number is recorded, so it cannot rot out of step again.) README now says 107 tests and
   no longer claims a fresh clone runs 68 of 74.
2. **Partially resolved — hook count was stale.** README now says four hooks and
   includes `post_tool_call`. `__init__.py`'s runtime docstring still lists three;
   changing it is outside this documentation-only task.
3. **Partially resolved — `/dissociate` was documented but not registered.**
   `SKILL.md` no longer lists it. `__init__.py`'s docstring and skill-registration
   description still mention it, and `panel.debug()` lists it in the idle line.
   Only aliases resolve it, via the `state` tool, to `doomscroll`.
4. **`/distance` is a dead alias chain.** `states.ALIASES` maps
   `"distance" → "dissociate"`, and `resolve()` then checks membership in
   `STATES`, where `dissociate` no longer exists. Verified: `resolve("distance")`
   returns `None`. Proposed code fix, requiring a separate approved change: map
   directly to `doomscroll`.
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
9. **Resolved — README's first line and live scene list still said `dissociate`.**
   They now list the four live states. The retired generator scene and historical
   replacement note remain explicitly labelled.
10. **Scenes-per-surface acceptance does not match current code.** That spec's
    references to `core/realimagery.py`, `HOLD_S`/`FADE_S` replacement, and
    `panel.debug` removal describe the pre-consolidation layout; the module is
    now `core/photographs.py` and global hold/fade constants still exist.
11. **Photograph priority suppresses the parsed walk map.** Earlier README and
    §10.2 wording promised a side-scrolling takeover map. In the current code,
    `imagery_frame()` returns photographs before applying the map overlay, and a
    live renderer can own the screen when photographs are absent. **Docs resolved:**
    README and §10.2 now describe the map as a fallback. **Owner: Ryan** — accept
    that precedence or approve a separate code change to restore the map.
12. **BR-7 says “on this machine”; the generator defaults to a tailnet host.**
    `tools/gen_frames.py` uses `SD_SERVER=http://100.82.186.41:8089`, not
    localhost. **Owner: Ryan** — keep the same-machine requirement, or approve:
    “Real imagery, generated on operator-controlled infrastructure, with no
    per-image vendor service.”
13. **Matrix and Telegram are unverified against real clients.** Their surface
    profiles exist and are unit-tested as encoders, but no real-client acceptance
    evidence exists. Documentation must not claim validated support.
14. **Note/join typing conflicts with BR-5's absolute no-words wording.**
    `tui.run()` temporarily displays `note ›` or `your word ›` and the typed
    buffer. **Owner: Ryan** — allow text while explicitly entering text, or
    approve a separate code change to make the interaction wordless.
15. **Resolved 2026-11-08 — the chat card was an almost-empty frame, not a
    picture of the walk.** Fixed in `core/surfaces.py`: `art()` now normalises
    each frame against its own 2nd/99.5th luminance percentile before the ramp,
    so a scene bank with mean luminance ~13/255 is read against itself. Measured
    after: walk 1%→18%, daydream 8%→23%, doomscroll 19%→32%, dream 11%→11%
    non-space cells; card PNG 84/90,692 → 950/111,548 bright pixels. No caption
    was added: BR-5 forbids words on the human surface, and
    `test_card_is_only_a_picture` still passes. Evidence of the original defect
    kept below.
    Original observation: 2026-11-08 with a live walk: `state(action="image")`
    card body of 10 rows × 21 columns whose only content was two rows of two
    dots, and a PNG of 287×316 with **84 non-background pixels out of 90,692
    (0.09%)**. `card()` is picture-only by design — no status line, no contract,
    no step trail — and `art()` downsamples a 1600×420 frame to `art_rows`×40
    (8 rows on the `discord` profile) through `ASCII_RAMP = " .:-=+*#"`. Across
    40 sampled frames the five scene banks measure mean luminance 11.9–15.2
    against a `255/8 ≈ 32` first-visible-character threshold, so nearly every
    cell maps to a space. Frames verified present
    (`~/.hermes/plugin-data/antemuse/three_frames/<scene>/`, 8 PNGs per scene),
    so this is not a missing-asset failure. The model-facing `record()` carries
    full text, so the defect is human-only, and encoder unit tests cannot see it.
    The caption option was declined: the card stays wordless, and the picture was
    made visible instead.
16. **Resolved 2026-11-08 — the human card and the model card served the whole
    journal, not this state's.** Every journal entry now carries its `session`,
    and `engine._journal_window()` scopes what `watch_state()` hands to the
    renderers: inside a state, entries at or after `entered_at` from this
    session; outside one, this session's recent tail (the recent tail at large
    when no session id is known). `card()` and `record()` therefore no longer
    print another session's trail. Original evidence: `engine.inject()` filtered
    to events with `at >= entered_at` while `engine.watch_state()` returned
    `data["journal"]` unfiltered, so a walk started 2026-11-08 rendered
    `mouflon → aniline` steps recorded 2026-11-07 at 20:35 as if they were
    current.
17. **Resolved 2026-11-08 — card frames and card writes could resolve to
    different homes.** `snapshot_path()` now writes under `storage.data_dir()`,
    the same home `art()` reads frames from, for every environment. The original
    split: `art()` read `storage.data_dir()/three_frames` while `snapshot_path()`
    wrote to `storage.project_dir() or storage.data_dir()`, so with a working
    directory inside a git repository the PNG landed in `<repo>/.antemuse/`
    while frames were read from the plugin data dir. Observed live: the PNG went
    to `/home/ryan/.antemuse/state_card.png` (because `/home/ryan` is itself a
    git repository) while the scene bank lives in
    `/home/ryan/.hermes/plugin-data/antemuse/three_frames`. A test now pins the
    invariant with a monkeypatched `project_dir`.
18. **Resolved 2026-11-08 — the verification record was stale by a factor of
    five.** §13 now carries a dated 2026-11-08 record: 591 tests, doctor
    `1 tool(s), 8 hook(s)`, and the surface measurements. The original record
    said 107 tests and a 12-module table; the intermediate measurement of
    564 tests and 4 hooks was taken before Wave 3 J1 registered the session
    hooks.

---

## 15. Spec change log

All paths relative to `specs/changes/`.

| change | status | kind | outcome |
|---|---|---|---|
| `semantic-states` | **LIVE** | state lifecycle | a state ends when its act is complete; durations and turn budgets become ceilings rather than definitions. |
| `desktop-surfaces` | **LIVE** | desktop | state pane, ambient background (`idle` and `work` scenes from `core/screensaver.py`, one renderer for CLI, pane and proofs, `?busy=1` selects work) and a per-state settings page for Hermes Desktop, fed by the same state the CLI reads. Verified in the app. |
| `e2e-fixes` | **LIVE** | repair found by real sessions | `/return` exists; state-scoped material; account counts material; clock capped; `settle()` not `clear()`; dependency refused at the door. 80 tests then. |
| `state-return-report` | **LIVE** | ending behaviour | every ending builds an account from the journal; `[YOU JUST CAME BACK …]`; `nothing arrived` for an empty state. |
| `consolidate-naming` | **LIVE** | internal restructuring | `core/`; modules named by content; one terminal-imaging module; dead SQLite board removed; no stale identity. 74 tests then. |
| `break-and-mood` | **LIVE** | new surface + bookkeeping | recommends, never enters; mood is reported, never inferred; one offer then 45 minutes. The strain arithmetic was removed 2026-11-08 — see `pattern-recommendation`, one owner. The commands themselves were later consolidated into `state(action='break'|'mood')`. |
| `ambient-walk` | **LIVE** | walk semantics | tools stay open; walk supplies no material (`feeds: False`); return forces a different first step (`restart: True`); relation names in the trail. 107 tests now. |
| `surface-repair` | **LIVE** | repair found by running the plugin | `art()` normalises each frame to its own percentiles (cards were 0.09% bright); journal entries carry `session` and `watch_state()` windows them; `snapshot_path()` writes where frames are read; §13 refreshed. 591 tests now. |
| `scenes-per-surface` | **PARTIAL** | rendering contract | per-state motion, clock grade, dual scoring, 4:5 postcards, origin binding, idle renders nothing. Not implemented; tasks T0–T8 open. |
| `non-blocking-states` | **LIVE** | core/state policy |
| `immersive-visuals` | **PARTIAL** | desktop/rendering | the pane becomes the picture: the frame is a 44x12 thumbnail (264x120 px, 4.4% of a 700x746 pane) drawn at a fixed 10 px. Size negotiation (`?cols=&rows=`, clamped and echoed), cell-aspect correction, an 8-frame strip looped on the surface, dither, and a HUD-collapsed layout. Source is real imagery from Meshy through three.js, not procedural primitives. 14 acceptance items; nothing implemented. |
| `scene-assets` | **LIVE** | art source | per-state asset brief: walk = a place and a figure, daydream = two recognisable objects joining, doomscroll = a textured feed passing, dream = one impossible fused object. States no longer restrict tools unless the entry passes block: true (allow: narrows it); the injection, the hook and the panel read one decision. An abstract-geometry pack (302 credits, 50 assets) replaces the literal props. Roles, triangle budgets, prompts, storyboards, 52-116 credits total, build order doomscroll -> daydream -> walk -> dream. **Built 2026-11-08 for 43 credits**: four states draw Meshy assets (figure 15,810 tris, mug 3,164, stone 3,138, chair 8,366, card 1024px) through a 100-line GLB reader; seeded bakes; a rejected card kept on disk with its reason. The 40x8 density test caught a card that read as a solid block. |
| `scene3d-renderer` | **PROPOSED** | rendering source | render scenes in Python at destination resolution (z-buffer, fog) instead of downsampling Chromium screenshots; braille for chat, half-blocks for terminal. Prototype: 80×24 cells in 24 ms, stdlib only. Not implemented; two owner decisions open. |
| `runtime-wiring` (J2) | **LIVE** | runtime | `core/runtime.py`, now reached as `state(action='spark'|'keep')` (the `/spark`, `/keep`, `/again` commands were consolidated away); model gets candidates, person gets counts and never candidate text; session-bound injection, reply footer, branch path through `ctx.llm` behind the flag. Feedback steers selection through `deepen`/`refresh` (J2b); verdicts resolve candidate ids to source ids; branch provenance is the orchestrator's, not the model's. Reproducible: `python3 tools/walkthrough.py`. 627 tests. |
| `truncation-visibility` | **LIVE** | evaluation | candidates record `finish_reason` and a `truncated` flag; records declare `record_schema`; old-schema records are re-run rather than replayed; the default selector prefers a complete candidate. Motivated by a real `liquid/lfm-3-1.7b` cell whose 2500-token B answer ended mid-sentence and was counted as `ok` with nothing saying so. |
| `wave4-shards` (K1/K2) | **LIVE** | evaluation | development shard `73a00871…` frozen over 2 tasks × 2 models × conditions A–F (write-once manifest, drift caught by re-hashing the fixture) and run through `tools/run_shard.py` to `complete: true, 24/24 cells, 0 duplicates`; each shard owns a results directory and aggregation fails closed on any missing cell. Conditions: A baseline, B creative, C best-of-N + selector, D deterministic material, E plain branches, F branches + selection + synthesis. G not implemented. No judge yet, so these are records, not a quality result. 677 tests. |
| `wave3-audit` | **LIVE** | review repairs | two independent reviews (spec compliance APPROVED; code quality REJECTED twice). Repaired: a decorative branch timeout, a shared-slot handoff that could cross chats, own-goal fallbacks, an unlocked book, and an account appended to the wrong session's reply. 627 tests. |
| `origin-and-cleanup` (J3) | **LIVE** | runtime | `engine.current_origin()`; a run is stamped with the project that asked for it and dropped, not rerouted, when a turn arrives from another project; `runtime.release()` clears run, verdicts, goal, account, and bound material in one call, wired to all four session boundaries; `/return` leaves a waiting run alone. Ignorance is not a mismatch: an empty project on either side still delivers. 627 tests. |
| `creative-state-evidence` | **PROPOSED** | evaluation | approved by Ryan 2026-11-07; Waves 1–2 are library-only; runtime activation and method promotion remain unapproved. No creative-quality claim is made anywhere in this change. |
| `state-evidence-task-bank` | **PROPOSED** | evaluation data | proposed data layer; not approved. Requires provenance-backed samples; pseudo-label self-training and unlabeled crawls are not improvement evidence. |
| `hackathon-submission` | **PROPOSED** | external submission | nothing submitted, nothing pushed. `antemuse.catalog.yaml`, demo script and checklist are drafts. |
| `command-surface` | **LIVE** | public verbs | 14 commands → 5 (four states + `/return`), then 6 with `greenfield`; `/note`, `/break`, `/mood`, `/state`, `/states`, `/watch`, `/spark`, `/keep`, `/again` became automation or tool actions. `/break <state>` no longer enters, `/keep` numbering is published, and a test fails when a registered verb has no definition. |
| `pattern-recommendation` | **PARTIAL** | recommendation | names the state that fits the shape of the work from measured counters: loop, data wall, saturation, grind, rut. One line, one state, one piece of evidence, cooling, silent by default, never enters. `churn` and `return hangover` are NOT BUILT — the plugin keeps no signal for them and a guess is not a measurement. `core/recommend.py`, 13 tests. |
| `hermes-integration` | **LIVE** | host interfaces | audit of every mechanism against the host source: tool/commands/hooks/injection/ctx.llm/aux tasks/storage/dashboard/memory. Three defects fixed — automation read `messages` but the host passes `user_message`; three modules hardcoded `~/.hermes`; daydream read a memory file an external provider never writes. No provider override, no SDK, no key: any provider by its default interface. |
| `state-entry` | **PARTIAL** | entry + direction | each state now declares where it starts and which way it moves; walk and dream draw their seed from a 5:3:2 mix of project terms, conversation terms and deliberate randomness, chosen by a deterministic hash and recorded as `seed=<source>:<term>` in the journal. `core/seeding.py`, 9 tests; doomscroll stays undirected by design. |
| `plugin-updates` | **LIVE** | delivery | a recommendation is pushed as its own message through `ctx.post_message`, once per cooling window, instead of waiting for someone to type a slash command. Discord caps app commands at 100 and this machine already syncs 95, so a command-only channel is not a reliable one. |
| `unstuck-state` | **LIVE** | states | a fifth state for a repository that does not exist yet: 5 min, 3 turns, read-only (`read_file`, `search_files`), material is what the project actually contains, and the exit criterion is **one direction** named with the spec file it becomes. Recommended automatically while the project has fewer than 3 commits and no spec, then silent. `core/sources.greenfield_text`, `core/recommend._new_project`; 7 tests. Renamed from `greenfield` (kept as an alias) for a plainer, more current word. |
| `normal-baseline` | **PARTIAL** | measurement | records the ordinary condition — tool calls and failures per turn, and the minutes between states — in `normal.json` (200 turns / 50 stretches, counts only). Below 20 turns nothing is claimed. `long stretch` now uses the measured 75th percentile of this person's stretches (clamped 60–180) instead of the constant 90, and the line says which it used. Loop, wall and saturation keep fixed thresholds until the failure-rate distribution can support a calibration. `core/normal.py`, 8 tests. |
| `plugin-settings` | **LIVE** | configuration | six bounded keys declared in the manifest's `config_schema` (`recommend_enabled`, `recommend_cooling_minutes`, `long_stretch_minutes`, `picture_enabled`, `picture_narrow`, `journal_cap`), rendered as a form by the **desktop app's** Settings ▸ Plugins and written to `plugins.entries.antemuse.settings.*`; read through `ctx.get_config`, clamped and logged, never raising. The plugin's own settings page was removed so the host form is the only one. Nothing that defines a state is settable. `core/settings.py`, 11 tests. |
| `gap-closure` | **LIVE** | measurement + repair | the three gaps the review found, closed with numbers: dream **0/40 → 40/40** real connections (file names as material, project as document, thin day widens 24h→72h→7d and says so); walk **9.0 % → 7.8 %** repeated destinations with ledger steering over 600 steps; unstuck quotes clipped at word boundaries and recommendations no longer built on short dictionary nouns. `tools/measure_state_gaps.py`, 7 tests. |
| `session-scan` | **LIVE** | architecture | the ledger is filled once per session, in the background: first `pre_llm_call` of a session starts one bounded scan (300 messages, 2 s budget, 14 days) in a daemon thread, guarded by a 30-minute interval and a single-flight lock; the cursor advances only over messages actually read, so a spent budget loses nothing. Silent when there is nothing new; one journal line when it stores something. Off under `ANTEMUSE_NO_SCAN` so a test suite never scans. |
| `concept-history` | **LIVE** | architecture | a durable concept ledger (`core/history.py`, sqlite in the plugin data dir) records identity — term, kind, stable key, move, session, time — and never message text. It answers what no state could: where a concept was met before, which concepts keep circling across sessions, and which were served but never used. Past-session concepts come from Hermes' own `state.db`, read-only and incrementally via a cursor, user and assistant text only. Fail-open: a broken ledger logs one named failure and every state still delivers. Consumers wired: walk annotates and records, dream connects circling concepts, daydream and dream record what they serve, unstuck recommends from circling and unused. |
| `state-goals` | **LIVE** | product | the five states were material generators; all five now make the cognitive move Ryan defined on 2026-11-08. walk anchors on a task concept and reports the return path on every step; daydream attaches a possibility to each memory pair; doomscroll draws from seven satire lanes with a deterministic work exclusion; dream pairs the day's commit subjects across projects and says so when nothing connects (invention is the labelled fallback); unstuck recommends one thing from history plus one edge of the concept graph. Dream reads no transcripts — only local git subjects — so the privacy question never arises. |
| `state-settings-experiment` | **PARTIAL** | evaluation | the deterministic lane is measured: `tools/experiment_deterministic.py` runs each state's own provider and counts novel (against this repository's ~6,050-word vocabulary), fresh within a dose, and distinct lines across trials — 150 trials/cell, seconds, zero model calls. It found walk's freshness falling 87→78 % from dose 3 to 12, doomscroll's variety collapsing to 11 % distinct lines on a frozen feed, dream at 100 % distinct but 5–8 % novel (a template), and unstuck serving five identical lines at every dose. Rules frozen before the deciding run: a dose may not exceed the smallest k where fresh < 0.85; distinct < 0.30 is a source defect; novel < 0.20 with distinct = 1.00 is a generator defect. The model lane (`tools/experiment_run.py`) stays as the cost-and-plausibility check — one 6-turn entry measured ~4.0 M input tokens — and is exploratory, its three entries excluded. No dose has been changed from these numbers. |
| `spec-ledger-cleanup` | **LIVE** | spec record | one row per change (two were listed twice), four status words enforced by the audit, six pre-discipline rows named and allowlisted instead of hidden, and the audit scoped to §15 so it can see a suffixed row and name an orphan. |
| `concept-graph` | **LIVE** | architecture + tool | the ledger as a graph: concepts connected to the sessions they were met in (ids, never transcripts), to the files a repository's own commits touched (paths, never contents) and through those to their projects, plus co-served concept pairs. A session is a hub with at most four spokes; node caps are per kind. `tools/graph_export.py` draws it concentrically — concepts on a phyllotaxis spiral, files and projects on rings, sessions outside, labels pointing outward — and is deterministic: same ledger, same picture; `--semantic` projects the concepts by meaning instead (see `concept-projection`). 8 tests. |
| `concept-projection` | **LIVE** | tool | concepts placed by meaning: `tools/graph_embed.py` writes bge-small vectors as a data artefact (the plugin imports no torch), and the export projects them with PCA + SMACOF — agreement between 2D and embedding distance **0.34 → 0.57** over 600 pairs, deterministic. Edges are nearest-in-meaning; sessions and projects are absent because they have no semantic position, and session dates are gone from the structural view too. 6 tests. |
| `concept-evidence` | **LIVE** | architecture + tool | every sighting now records the **message id** or **commit sha** it came from, stamped with the message's own time; two concepts are linked only when they share a message (852 session-level pairs were a hairball, and `served beside` returned `source (1092)`). `tools/graph_inspect.py` prints the evidence — sessions, message ids, commits, files, siblings, nearest in meaning — and `--text` resolves excerpts on demand, never into the ledger. 9 tests. |
| `state-activation` | **PARTIAL** | architecture + tool | the concept map as a state visual: `core/activation.py` turns servings into decaying weights (180 s half-life, freshest sighting wins, future servings excluded) and `tools/activation_render.py` lights the semantic map frame by frame — 263 concepts, 66 lit at peak, no text on the picture. **Not wired into the pane**: that needs a scene in the desktop pipeline, which is mid-change elsewhere. 11 tests. |
Four status words, and nothing else: **LIVE** (built and verified), **PARTIAL** (built in part), **PROPOSED** (decided or drafted, not built), **NOT BUILT**. Rows without a `specs/changes/` directory predate that discipline and survive on their commit history alone.
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

### 17.1 Scene renderer — 3D straight to terminal pixels

From `scene3d-renderer` (status: proposed, 2026-11-08; full contract in
`specs/changes/scene3d-renderer/spec.md`). Not implemented.

Today the chat card is one of eight cached Chromium screenshots of a 1600×420
three.js frame, cropped and resized to 40×8 cells. At that size a scene's
geometry falls below one cell per feature: the walk's floor, path edges and
perspective disappear, and what remains is the point trail and the ring. §14.15
fixed the luminance ramp — the card is legible now — but sampling cannot put
back what it discarded. Producing those frames also needs a static server,
headless Chromium with SwiftShader, and ~0.7 s per frame.

Proposal: render the scene in Python at the resolution the destination actually
has, instead of photographing it and shrinking the photograph.

- `core/scene3d.py` — a deterministic software renderer with no third-party
  dependency: camera basis, perspective projection, z-buffer, distance fog, and
  a luminance buffer.
- Primitives mirror what `tools/scene.html` already draws: ground grid, luminous
  path, point trail, torus, per-state camera.
- Packing per surface: truecolor half-blocks for the terminal takeover (which
  the TUI already speaks), braille (2×4 dots per cell) for the wordless chat
  card, full-size pixels for the PNG attachment.
- `art()` gains a renderer choice; the frame bank stays the default until the
  live renderer is proven on both surfaces.

Prototype evidence (2026-11-08): the walk scene projected in Python and packed
2×4 into braille — **80×24 cells = 160×96 addressable dots in 24 ms**, stdlib
only, no browser, no PNG bank, deterministic for a given camera. The corridor,
the ring, and the trail were all legible. Reproducible with
`python3 tools/scene3d_probe.py`, which is the measurement and not the
implementation: it is not wired into runtime.

Two decisions are open and are Ryan's, not the implementation's:

- **source of truth** — port the scenes to Python and retire `scene.html` +
  `three_frames/`, or keep the JS authoritative and accept a second
  implementation that can drift (recommendation: port);
- **chat glyph set** — braille for 8× addressable resolution but monochrome and
  dependent on U+28xx coverage, versus block ramps (`▁▂▃▄▅▆▇█`) at 1× resolution
  and universal rendering (recommendation: braille, with a ramp fallback when
  the surface reports a glyph gap).

This is the same aspect problem `scenes-per-surface` already names: a 40×8 card
is 5:1 and a 4:5 postcard is not the same place. A live renderer makes the
two-crop requirement cheap — two cameras instead of two asset sets.

Brand decision still open upstream: the marketplace has no `cognition` category,
and `productivity` is not a valid category. Ryan must decide whether to accept
`general`, the only honest existing fallback, or propose `cognition` upstream.
The tags remain `cognitive`, `creativity`, `states`, `imagery`.

---

### 17.2 Activation in the pane — the remaining work

The renderer exists (§10.6); the surface does not. Registration and budget are the work:

1. ~~register the scene and paint it~~ — **done**: the backend serves `stills`, the pane paints
   them, and an empty list falls back to the baked art. Still to do: a look at it in the running
   app, and a decision on whether a state with no servings should say so on screen;
2. pick a frame budget per surface: the terminal takes quantised frames at ~2 fps like the baked
   scenes; chat takes a still and, at state edges, the strip; the desktop pane takes the GIF;
3. encode the same frames for the card path without letting any text in — the no-words rule in
   §10.1 applies, and `tests/test_activation.py` asserts the renderer draws none;
4. keep it derivable when the ledger is empty: a state with no servings falls back to the baked
   scene, named as a fallback rather than a blank.

Not started, and not claimed. `desktop/art` is carrying an unrelated reorganization that the
owner asked to leave alone, which is where the scene table lives.

## 18. Must-not-change constraints

Unless a change spec says otherwise and is approved:

- the `state` tool schema and its action set;
- the five state definitions: doses, ceilings, turn budgets, tool policy,
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
| `collide` walk as a `ManualGraph` over a domain bank (persona + mechanism + bridging question) | **partly implemented, not as a walk** — `collide` is still absent from `walks.BUILTIN`, but the bank (`core/collider.py`, six CC BY 4.0 artifacts), the deterministic collision (`core/collision.py`), and the branch runner (`core/orchestrator.py`) exist and run | `core/walks.py` if the walk form is still wanted; otherwise the module path is the implementation |
| Write the bank schema down before implementing | **done, elsewhere** — the bank schema and its licensing enforcement live in `core/collider.py` with the change record in `specs/changes/creative-state-evidence/`; there is no `collide-walk` spec because no collide walk was built | `specs/changes/creative-state-evidence/` |
| Two residue channels (`carried`, `arrived`) | **not implemented** — residue has only `report`/legacy kinds | `core/engine.py` |
| Threshold drift as a state-exit rule | **superseded** — exit is the dose (`semantic-states`), and the ceiling is a safety limit, not a schedule | `core/states.py`, `engine` |
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

A separate proposal for a generative "creative cognition engine" is recorded at
`../docs/research/creative-cognition-proposal.md`. It is **not adopted** and
conflicts with this spec's no-model-call and no-scoring contract; it is kept for
the record, not as a plan.
