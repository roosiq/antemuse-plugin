# Changelog

All notable changes to Antemuse. The manifest version and this file move
together; the catalog entry is generated from the manifest at release time.

## 0.10.39 — 2026-11-11

- states: remove the clock, end on the act, and say so when it ends (2026-11-11)
- changelog: the empty pane is honest about a failed poll (2026-11-11)

## 0.10.38 — 2026-11-11

- change: delivery is paced by the clock — one unit a second from the moment the state exists —
  so the dose ends a state, not the ceiling. Per-turn pacing needed one of the person's messages
  per hop, a six-hop walk ran out of minutes first, and it expired at five of six. The pane's
  poll drives delivery while nobody is typing. The `deliver = "drip"` setting is gone: a setting
  may change how long a state is, never what a state is, and there was nothing left for it to do.
- fix: a walk entered from a chat now draws. `watch_state()` whitelists the active record and
  left out `origin` and `entered_at`, the two fields `graph()` reads; the pane lit nothing and
  its trail spanned every walk ever recorded. Both are already persisted — nothing new computed.
- fix: a state entered with no origin session (the app, a capture script) now lights the hops the
  ledger says fired, instead of one stale empty-session concept and a trail nobody walked.
- fix: an idle pane is not a dead end — it names the last state that ended and the one line that
  starts another, and with no state at all it names that same line. It used to say "no state"
  over a map still drawing that state's decaying firings.
- fix: the empty pane is honest about what it does not know. Before the first answer it names
  nothing instead of "no state", the corner is readable rather than 50 % grey, and a failed
  answer prints no clock, counts or contract — the pane was shipping a status line that read
  "the backend did not answer · 1:31 left".
- fix: one dropped poll no longer blanks a running state. The pane names a failure after three
  consecutive misses (under three seconds) and any answer clears it; a gateway restart used to
  replace a live walk with an error for every request it dropped.
- fix: drop the dead `peek()` fallback in `graph()`; a stripped `active` is truthy, so it never
  ran, and it made the shape mismatch invisible.
- test: `test_a_state_entered_from_a_chat_lights_the_pane`,
  `test_a_state_drains_its_dose_as_fast_as_the_clock_allows` and
  `test_a_turn_buys_no_extra_units` — all three fail against 0.10.37's engine, all three pass here.

## 0.10.37 — 2026-11-11

- chore: the plugin root is Python; the pane harness owns its npm manifest (2026-11-11)

## 0.10.36 — 2026-11-11

- fix: the pane harness runs again — real deps, self-provisioning, assertions that match the pane (2026-11-11)

## 0.10.35 — 2026-11-11

- docs: only what the plugin is — every document audited, the spec tree removed, dead tools gone (2026-11-11)

## 0.10.34 — 2026-11-11

- docs: stop advertising a takeover that 0.10.30 deleted, in the entry, TESTING.md and the spec (2026-11-11)
- docs(eval): the idea-states benchmark ships its report, plots, scripts and per-model aggregates (2026-11-11)

## 0.10.33 — 2026-11-11

- one unit per turn, so the pane shows each hop (2026-11-11)
- recommendations are a display setting, and off by default (2026-11-11)
- release (2026-11-11)
- nothing that ships imports a module the package dropped (2026-11-11)
- release (2026-11-11)
- the account ends where the walk landed (2026-11-11)
- the picture keeps what the state just did (2026-11-11)
- bind the quad program before setting its colour (2026-11-11)
- singularise the unit where every surface reads it (2026-11-11)
- one dose, reported the same way to the chat and the pane (2026-11-11)
- version, catalog and pane js agree with what /state reports (2026-11-11)
- the walk exists in the picture, and the pane draws whoever entered it (2026-11-11)
- a finished state always reaches the person (2026-11-11)
- the fixes 0.10.26 shipped without tests get the tests they were missing (2026-11-11)
- an entry promises its dose, not its ceiling (2026-11-11)
- the listing counts doses in their own unit, and three picture aliases become one (2026-11-11)
- the residue cap holds where residue is written (2026-11-11)
- the dose is counted in the state's own unit, everywhere it is printed (2026-11-11)
- every ending speaks in the state that ended (2026-11-11)
- a state answers in its own voice and finishes in the turn it is due (2026-11-11)
- release (2026-11-11)
- changelog: strip catalog-entry bullets from older sections too (2026-11-11)
- release (2026-11-11)
- release mechanics: one script, and a changelog that cannot name a sha it does not pin (2026-11-11)
- no home directory in anything that runs (2026-11-11)
- a walk that tells the model it is getting nothing (2026-11-11)
- the release pipeline and the documents it describes (2026-11-10)
- end-to-end every state, and the two that recorded nothing (2026-11-10)
- the seeding fix that was never applied, %-d, and honest environment skips (2026-11-10)
- dot size is how often a concept was met; colour stays activation (2026-11-10)
- the shipped suite passes from the shipped package (2026-11-10)
- the shipped suite runs from the shipped package (2026-11-10)
- an upgrade lands where a fresh install lands; tests ship (2026-11-10)
- every ending writes its moves row; desktop/ is one file (2026-11-10)
- doomscroll records what it served — and a failed write says so (2026-11-10)
- the web stops burying the dots (2026-11-10)
- edges you can see, and a camera you can steer (2026-11-10)
- a served concept writes, and a run leaves a record (2026-11-10)
- install where the plugin imports, and name the cause you established (2026-11-10)
- daydream and dream never answer nothing (2026-11-10)
- the model says what the state did, in the house voice (2026-11-10)
- the account is spoken — and the account is not the injection (2026-11-10)
- a first walk is not a rut; demo plan v2 (2026-11-10)
- ship the fallback frames; drop two tests of an unpublished document (2026-11-10)
- the tree a reviewer reads (2026-11-10)
- untrack data/meshy: generation records and .glb drafts nothing at runtime loads (2026-11-10)
- chat carries no visualization, and a state belongs to one chain (2026-11-10)
- the settings that were on the form but not in the code (2026-11-10)
- the installer is Python, so it runs where Hermes runs (2026-11-10)
- install, walk, and watch it light — end to end (2026-11-10)
- connections carry the activation (2026-11-10)
- the nodes say their names (2026-11-10)
- the camera goes to the concept that just fired (2026-11-10)
- the walk draws its path (2026-11-10)
- a running walk can finally light its own map (2026-11-10)
- the cloud was there all along, five layers down (2026-11-10)
- the stills stop ghosting through the cloud (2026-11-10)
- the corner says why, not what category (2026-11-10)
- release: never pack a bake's staging dir (2026-11-10)
- the bake stops eating itself (2026-11-10)
- a surface that wants numbers does not pay for a JPEG (2026-11-10)
- the map rides the route that was always mounted (2026-11-10)
- the pane counts its own round trips (2026-11-10)
- a failed poll says what failed (2026-11-10)
- the graph route is cached, timed, and patient (2026-11-10)
- the pane is a space you can turn (2026-11-10)
- a frame rotated away mid-read is not a failed picture (2026-11-10)
- the payload names the code that answered (2026-11-10)
- core is loaded off disk, not off whatever claims the name (2026-11-10)
- a diagnostic is not material, and a finished state still owes its account (2026-11-10)
- the router finds core when it is loaded as a bare module (2026-11-10)
- a fresh install has a picture (2026-11-09)
- a still kept in base/ is still reachable (2026-11-09)
- state: one shape for the payload, failure or success (2026-11-09)
- the router finds core however the host loads it (2026-11-09)
- install: the app owns its own directory (2026-11-09)
- pane: stop shipping and stop keeping the scenes we deleted (2026-11-09)
- install: read the doctor's counts with a counter that can be tested (2026-11-09)
- windows: the takeover no longer takes the plugin down with it (2026-11-09)
- install: the projection travels with the package, never inside the tree (2026-11-09)
- install: one script puts a full base install where Hermes reads from (2026-11-09)
- the activation is the only picture: the baked scenes are gone (2026-11-09)
- pane: a broken picture is worse than baked art, and a remote pane can carry its own bytes (2026-11-09)
- experiments: one table with every result (2026-11-09)
- experiments: lead with distinct concepts, not a similarity floor (2026-11-09)
- experiments: resampling floor folded into the results (2026-11-09)
- pane: a chat nothing was served in draws the profile instead of nothing (2026-11-09)
- a command is not a message: it carries the chat that asked (2026-11-09)
- pane: an absolute URL, because a remote desktop cannot read the host's disk (2026-11-09)
- experiments: variation floor — straight lists of 100 ideas, asked four times (2026-11-09)
- experiments: cross-model overlap of the idea lists (2026-11-09)
- docs: the qa record, including the caution the scan now reports (2026-11-09)
- catalog: pin the qa build (2026-11-09)
- qa: fix the seven defects a full pass turned up (0.9.1) (2026-11-09)
- experiments: call the column perplexity, drop the 'after a' prefix (2026-11-09)
- experiments: plain words in the benchmark write-up, tables and page (2026-11-09)
- experiments: benchmark outcome write-up and table image (2026-11-09)
- experiments: drop logprob-based metric from the shared tables; add opus 5.5 and sol 6.1 (2026-11-09)
- experiments: percent view across four models, gpt and qwen cells folded in (2026-11-09)
- experiments: idea-states measured by deterministic text statistics only (2026-11-09)
- experiments: 50-idea lists, straight vs with a walk/daydream/doomscroll in the middle (2026-11-09)
- experiments: cloud-model before/after with length control and parallel judging (2026-11-09)
- experiments: before/after demonstration of collider material vs baseline and placebo (2026-11-09)
- catalog: the drift check must ignore the pin inside image URLs (2026-11-09)
- catalog: pin the packaging commit, with the banner and four stills (2026-11-09)
- spec: record the packaging change in the ledger, and refresh the count (2026-11-09)
- submission: spec the missing artifacts, and render the catalog stills from the real surfaces (2026-11-09)
- packaging: audit against 763 admitted entries, and fix what it found (2026-11-09)
- catalog: emit the schema the loader accepts, with benign known issues (2026-11-09)
- packaging: manifest v2 fields, changelog, security, contributing, compatibility and limits (2026-11-09)
- catalog: declare the same Hermes floor as the manifest (2026-11-09)
- catalog: pin the verified commit, and stage the PR body (2026-11-09)
- kill the dead commands, correct the walk evidence, and record the owner's no-cut decision (2026-11-09)
- audit: two-model product review, and the acceptance path it broke open (2026-11-09)
- docs: generated assets are archived off-repo (2026-11-09)
- ship: correct the test-user install steps (2026-11-09)
- ship: a verification command that works, and notes for a test user (2026-11-09)
- look: a palette is a mood, and the house one is measured off the Nous site (2026-11-09)
- pane: it is called Antemuse, and the look is a parameter (2026-11-09)
- pane: the stills reach the desktop pane, and it is seen painting them (2026-11-09)
- test: the activation route over real HTTP, and the fallback it needed (2026-11-09)
- look: three.js post-processing on the activation stills, at bake time (2026-11-09)
- activation: the desktop pane draws it as an image, not as characters (2026-11-09)
- activation: the surfaces can show it — a glyph scene with a fall-through (2026-11-09)
- spec: the state visual is the activation map, and here is what is left to wire (2026-11-08)
- activation: the concept map can show a state firing (2026-11-08)
- graph: labels a person can read, and vectors out of the repo (2026-11-08)
- evidence: a concept now points at the messages and commits it came from (2026-11-08)
- projection: place the concepts by meaning, and stop showing dates (2026-11-08)
- graph: concepts are attached to sessions and files now, and it can be drawn (2026-11-08)
- spec: one row per change, four status words, and an audit that can see the table (2026-11-08)
- gap-closure: dream connects again, walk steers, unstuck stops quoting mid-word (2026-11-08)
- docs: the states do the moves now, so the spec says so (2026-11-08)
- history: fill the ledger once per session, bounded and out of the turn's way (2026-11-08)
- history: a concept ledger, so a move can know it has been here before (2026-11-08)
- states: make all five do the move they are defined as (2026-11-08)
- docs: the goals are Ryan's, and the code does not match three of them (2026-11-08)
- docs: what each state is for, written down before anything else gets tuned (2026-11-08)
- dream: stop conjugating a lexical unit that may not be a verb (2026-11-08)
- dream and daydream: fix the two states that were failing their own goals (2026-11-08)
- walk: one composite navigation that uses all of them, and says which each step took (2026-11-08)
- navigation: go further out, draw from a wider pool, ask memory for a direction (2026-11-08)
- experiment: measure the dose deterministically, in seconds, with no model (2026-11-08)
- experiment: run it, and let the first entries teach the design what it got wrong (2026-11-08)
- P0/P1: make the submission honest and the experiment checkable (2026-11-08)
- spec: the experiment that would earn each state's dose (2026-11-08)
- settings: the desktop app's plugins area is the settings page (2026-11-08)
- states end on their dose, not on a clock (2026-11-08)
- spec: plugin settings that cannot change what a state is (2026-11-08)
- normal: measure the ordinary condition, so a state has something to be a state against (2026-11-08)
- spec: one recommender. mood measures, recommend names (2026-11-08)
- unstuck: the state's real name, and a nudge that stops citing deleted commands (2026-11-08)
- greenfield: a trendier name, and the picture arrives in the chat (2026-11-08)
- trailhead: a state for the project that does not exist yet (2026-11-08)
- dream opens on a memory; recommendations arrive as messages (2026-11-08)
- entry: say where a state starts, and make it start somewhere different (2026-11-08)
- recommend: name the state that fits the work, from counters only (2026-11-08)
- specs: the record matches the five-command surface and the tool actions (2026-11-08)
- daydream: material that does not depend on which memory provider is loaded (2026-11-08)
- host: use Hermes' interfaces, and fix the three we were misusing (2026-11-08)
- surface: five commands, and the rest becomes behaviour (2026-11-08)
- verbs: consolidate 14 commands into 11 (2026-11-08)
- verbs: define the surface, and fix the three that were broken (2026-11-08)
- site: the architecture as a page, built from the document (2026-11-08)
- docs: the functional plan with status, not a memory of one (2026-11-08)
- specs: the record matches the repository, and a test says so (2026-11-08)
- tools: pane_gif bakes the strip so motion can be judged without a restart (2026-11-08)
- pane: a dither of black is a dot lattice (2026-11-08)
- bake: a picture or an error, never a silent success (2026-11-08)
- pane: the strip moves (2026-11-08)
- pane: paint it like a picture, not a page (2026-11-08)
- docs: demo asset inventory (2026-11-08)
- demo: visible keystrokes and pointer, and a one-command capture rig (2026-11-08)
- pack: 302 credits of abstract geometry (2026-11-08)
- demo: caption generator, human-pace typing, and the toolchain decision (2026-11-08)
- docs: demo production plan, and the states-open correction (2026-11-08)
- states: an aside is not a lock (2026-11-08)
- pane: the picture is the size of the pane (2026-11-08)
- docs: task register for the hackathon submission (2026-11-08)
- docs: hackathon submission plan, disclosures, and licence (2026-11-08)
- docs: record the asset pack, and what the plan missed (2026-11-08)
- art: dream is one impossible object, twice (2026-11-08)
- art: the walker is a person, not a capsule (2026-11-08)
- art: a real mug, a real stone, a real card (2026-11-08)
- spec: which pictures the states need (2026-11-08)
- spec: Meshy is installed here, and its key is a human step (2026-11-08)
- spec: real imagery through three.js, not primitives (2026-11-08)
- spec: the pane is the picture (2026-11-08)
- desktop: a pane needs a route, not just a dock (2026-11-08)
- desktop: a pane fed by a served frame (2026-11-08)
- register: close K1d, drop the duplicate K2 line, file K1f under Wave 4 (2026-11-08)
- evidence: re-run the development shard with finish reasons (2026-11-08)
- eval: record why every answer stopped (2026-11-08)
- spec: desktop surfaces, from a review of ascii-worlds (2026-11-08)
- fix: resolve the plugin root from this repository, not the old site path (2026-11-08)
- docs: give the standalone repository its own workspace notes (2026-11-08)
- import: antemuse plugin as a standalone repository (2026-11-08)
- feat(scripts): measured harvest feasibility probe for the task bank (2026-11-07)
- docs(specs): proposal for the evidence task bank the evaluator is missing (2026-11-07)
- docs(plugin): align the written contract with what the measurements support (2026-11-07)
- docs(specs): creative-state-evidence contracts and task register (2026-11-07)
- feat(plugin): collider source bank, bounded auxiliary llm adapter, event projections (2026-11-07)
- feat(evaluation): offline baselines A-C with cache-bound run records (2026-11-07)
- docs: BRD consolidated from the operator's messages (2026-11-06)
- feat(walk): origin binding (T0) — a state belongs to the session and repo it started in (2026-11-06)
- test: the subtractive walk's significant result was verbosity (2026-11-06)
- test: the subtractive walk is the first configuration that moved the right way (2026-11-05)
- feat(walk): subtract, don't add — no material while walking, a forced re-approach on return (2026-11-05)
- test: the far walk changes nothing either (2026-11-05)
- feat(walk): jump, don't step — the outer walk is what /walk does now (2026-11-05)
- docs: with the walk and without, in one table (2026-11-05)
- test: the fast walk changes nothing measurable (2026-11-05)
- feat(walk): three minutes, a step every nine seconds (2026-11-05)
- feat(walk): ten minutes, one step every thirty seconds (2026-11-05)
- test: the creativity sweet spot does not exist at these doses (2026-11-05)
- test: first creativity probe — 8 uses for a brick, idle vs walking (2026-11-05)
- plugin: a bench for what the plugin costs per turn and per frame (2026-11-05)
- plugin: declare the post_tool_call hook it registers (2026-11-05)
- plugin: the agent-facing states live in the project (2026-11-05)

## 0.10.32 — 2026-11-11

- recommendations are a display setting, and off by default (2026-11-11)

## 0.10.31 — 2026-11-11

- nothing that ships imports a module the package dropped (2026-11-11)

## 0.10.30 — 2026-11-11

- the account ends where the walk landed (2026-11-11)
- the picture keeps what the state just did (2026-11-11)
- bind the quad program before setting its colour (2026-11-11)
- singularise the unit where every surface reads it (2026-11-11)
- one dose, reported the same way to the chat and the pane (2026-11-11)
- version, catalog and pane js agree with what /state reports (2026-11-11)
- the walk exists in the picture, and the pane draws whoever entered it (2026-11-11)
- a finished state always reaches the person (2026-11-11)
- the fixes 0.10.26 shipped without tests get the tests they were missing (2026-11-11)
- an entry promises its dose, not its ceiling (2026-11-11)
- the listing counts doses in their own unit, and three picture aliases become one (2026-11-11)
- the residue cap holds where residue is written (2026-11-11)
- the dose is counted in the state's own unit, everywhere it is printed (2026-11-11)
- every ending speaks in the state that ended (2026-11-11)
- a state answers in its own voice and finishes in the turn it is due (2026-11-11)

## 0.10.20 — 2026-11-11

- changelog: strip catalog-entry bullets from older sections too (2026-11-11)

## 0.10.19 — 2026-11-11

- release mechanics: one script, and a changelog that cannot name a sha it does not pin (2026-11-11)

## 0.10.18 — 2026-11-11


## 0.10.17 — 2026-11-11


## 0.10.16 — 2026-11-10

- No commits since the last entry.

## 0.10.15 — 2026-11-10

- end-to-end every state, and the two that recorded nothing (2026-11-10)
- the seeding fix that was never applied, %-d, and honest environment skips (2026-11-10)
- dot size is how often a concept was met; colour stays activation (2026-11-10)
- the shipped suite passes from the shipped package (2026-11-10)
- the shipped suite runs from the shipped package (2026-11-10)
- an upgrade lands where a fresh install lands; tests ship (2026-11-10)
- every ending writes its moves row; desktop/ is one file (2026-11-10)
- doomscroll records what it served — and a failed write says so (2026-11-10)
- the web stops burying the dots (2026-11-10)
- edges you can see, and a camera you can steer (2026-11-10)
- a served concept writes, and a run leaves a record (2026-11-10)
- install where the plugin imports, and name the cause you established (2026-11-10)
- daydream and dream never answer nothing (2026-11-10)
- the model says what the state did, in the house voice (2026-11-10)
- the account is spoken — and the account is not the injection (2026-11-10)
- a first walk is not a rut; demo plan v2 (2026-11-10)
- ship the fallback frames; drop two tests of an unpublished document (2026-11-10)
- the tree a reviewer reads (2026-11-10)
- untrack data/meshy: generation records and .glb drafts nothing at runtime loads (2026-11-10)
- chat carries no visualization, and a state belongs to one chain (2026-11-10)
- the settings that were on the form but not in the code (2026-11-10)
- the installer is Python, so it runs where Hermes runs (2026-11-10)
- install, walk, and watch it light — end to end (2026-11-10)
- connections carry the activation (2026-11-10)
- the nodes say their names (2026-11-10)
- the camera goes to the concept that just fired (2026-11-10)
- the walk draws its path (2026-11-10)
- a running walk can finally light its own map (2026-11-10)
- the cloud was there all along, five layers down (2026-11-10)
- the stills stop ghosting through the cloud (2026-11-10)
- the corner says why, not what category (2026-11-10)
- release: never pack a bake's staging dir (2026-11-10)
- the bake stops eating itself (2026-11-10)
- a surface that wants numbers does not pay for a JPEG (2026-11-10)
- the map rides the route that was always mounted (2026-11-10)
- the pane counts its own round trips (2026-11-10)
- a failed poll says what failed (2026-11-10)
- the graph route is cached, timed, and patient (2026-11-10)
- the pane is a space you can turn (2026-11-10)
- a frame rotated away mid-read is not a failed picture (2026-11-10)
- the payload names the code that answered (2026-11-10)
- core is loaded off disk, not off whatever claims the name (2026-11-10)
- a diagnostic is not material, and a finished state still owes its account (2026-11-10)
- the router finds core when it is loaded as a bare module (2026-11-10)
- a fresh install has a picture (2026-11-09)
- a still kept in base/ is still reachable (2026-11-09)
- state: one shape for the payload, failure or success (2026-11-09)
- the router finds core however the host loads it (2026-11-09)
- install: the app owns its own directory (2026-11-09)
- pane: stop shipping and stop keeping the scenes we deleted (2026-11-09)
- install: read the doctor's counts with a counter that can be tested (2026-11-09)
- windows: the takeover no longer takes the plugin down with it (2026-11-09)
- install: the projection travels with the package, never inside the tree (2026-11-09)
- install: one script puts a full base install where Hermes reads from (2026-11-09)
- the activation is the only picture: the baked scenes are gone (2026-11-09)
- pane: a broken picture is worse than baked art, and a remote pane can carry its own bytes (2026-11-09)
- experiments: one table with every result (2026-11-09)
- experiments: lead with distinct concepts, not a similarity floor (2026-11-09)
- experiments: resampling floor folded into the results (2026-11-09)
- pane: a chat nothing was served in draws the profile instead of nothing (2026-11-09)
- a command is not a message: it carries the chat that asked (2026-11-09)
- pane: an absolute URL, because a remote desktop cannot read the host's disk (2026-11-09)
- experiments: variation floor — straight lists of 100 ideas, asked four times (2026-11-09)
- experiments: cross-model overlap of the idea lists (2026-11-09)
- docs: the qa record, including the caution the scan now reports (2026-11-09)
- catalog: pin the qa build (2026-11-09)
- qa: fix the seven defects a full pass turned up (0.9.1) (2026-11-09)
- experiments: call the column perplexity, drop the 'after a' prefix (2026-11-09)
- experiments: plain words in the benchmark write-up, tables and page (2026-11-09)
- experiments: benchmark outcome write-up and table image (2026-11-09)
- experiments: drop logprob-based metric from the shared tables; add opus 5.5 and sol 6.1 (2026-11-09)
- experiments: percent view across four models, gpt and qwen cells folded in (2026-11-09)
- experiments: idea-states measured by deterministic text statistics only (2026-11-09)
- experiments: 50-idea lists, straight vs with a walk/daydream/doomscroll in the middle (2026-11-09)
- experiments: cloud-model before/after with length control and parallel judging (2026-11-09)
- experiments: before/after demonstration of collider material vs baseline and placebo (2026-11-09)
- catalog: the drift check must ignore the pin inside image URLs (2026-11-09)
- catalog: pin the packaging commit, with the banner and four stills (2026-11-09)
- spec: record the packaging change in the ledger, and refresh the count (2026-11-09)
- submission: spec the missing artifacts, and render the catalog stills from the real surfaces (2026-11-09)
- packaging: audit against 763 admitted entries, and fix what it found (2026-11-09)
- catalog: emit the schema the loader accepts, with benign known issues (2026-11-09)
- packaging: manifest v2 fields, changelog, security, contributing, compatibility and limits (2026-11-09)
- catalog: declare the same Hermes floor as the manifest (2026-11-09)
- catalog: pin the verified commit, and stage the PR body (2026-11-09)
- kill the dead commands, correct the walk evidence, and record the owner's no-cut decision (2026-11-09)
- audit: two-model product review, and the acceptance path it broke open (2026-11-09)
- docs: generated assets are archived off-repo (2026-11-09)
- ship: correct the test-user install steps (2026-11-09)
- ship: a verification command that works, and notes for a test user (2026-11-09)
- look: a palette is a mood, and the house one is measured off the Nous site (2026-11-09)
- pane: it is called Antemuse, and the look is a parameter (2026-11-09)
- pane: the stills reach the desktop pane, and it is seen painting them (2026-11-09)
- test: the activation route over real HTTP, and the fallback it needed (2026-11-09)
- look: three.js post-processing on the activation stills, at bake time (2026-11-09)
- activation: the desktop pane draws it as an image, not as characters (2026-11-09)
- activation: the surfaces can show it — a glyph scene with a fall-through (2026-11-09)
- spec: the state visual is the activation map, and here is what is left to wire (2026-11-08)
- activation: the concept map can show a state firing (2026-11-08)
- graph: labels a person can read, and vectors out of the repo (2026-11-08)
- evidence: a concept now points at the messages and commits it came from (2026-11-08)
- projection: place the concepts by meaning, and stop showing dates (2026-11-08)
- graph: concepts are attached to sessions and files now, and it can be drawn (2026-11-08)
- spec: one row per change, four status words, and an audit that can see the table (2026-11-08)
- gap-closure: dream connects again, walk steers, unstuck stops quoting mid-word (2026-11-08)
- docs: the states do the moves now, so the spec says so (2026-11-08)
- history: fill the ledger once per session, bounded and out of the turn's way (2026-11-08)
- history: a concept ledger, so a move can know it has been here before (2026-11-08)
- states: make all five do the move they are defined as (2026-11-08)
- docs: the goals are Ryan's, and the code does not match three of them (2026-11-08)
- docs: what each state is for, written down before anything else gets tuned (2026-11-08)
- dream: stop conjugating a lexical unit that may not be a verb (2026-11-08)
- dream and daydream: fix the two states that were failing their own goals (2026-11-08)
- walk: one composite navigation that uses all of them, and says which each step took (2026-11-08)
- navigation: go further out, draw from a wider pool, ask memory for a direction (2026-11-08)
- experiment: measure the dose deterministically, in seconds, with no model (2026-11-08)
- experiment: run it, and let the first entries teach the design what it got wrong (2026-11-08)
- P0/P1: make the submission honest and the experiment checkable (2026-11-08)
- spec: the experiment that would earn each state's dose (2026-11-08)
- settings: the desktop app's plugins area is the settings page (2026-11-08)
- states end on their dose, not on a clock (2026-11-08)
- spec: plugin settings that cannot change what a state is (2026-11-08)
- normal: measure the ordinary condition, so a state has something to be a state against (2026-11-08)
- spec: one recommender. mood measures, recommend names (2026-11-08)
- unstuck: the state's real name, and a nudge that stops citing deleted commands (2026-11-08)
- greenfield: a trendier name, and the picture arrives in the chat (2026-11-08)
- trailhead: a state for the project that does not exist yet (2026-11-08)
- dream opens on a memory; recommendations arrive as messages (2026-11-08)
- entry: say where a state starts, and make it start somewhere different (2026-11-08)
- recommend: name the state that fits the work, from counters only (2026-11-08)
- specs: the record matches the five-command surface and the tool actions (2026-11-08)
- daydream: material that does not depend on which memory provider is loaded (2026-11-08)
- host: use Hermes' interfaces, and fix the three we were misusing (2026-11-08)
- surface: five commands, and the rest becomes behaviour (2026-11-08)
- verbs: consolidate 14 commands into 11 (2026-11-08)
- verbs: define the surface, and fix the three that were broken (2026-11-08)
- site: the architecture as a page, built from the document (2026-11-08)
- docs: the functional plan with status, not a memory of one (2026-11-08)
- specs: the record matches the repository, and a test says so (2026-11-08)
- tools: pane_gif bakes the strip so motion can be judged without a restart (2026-11-08)
- pane: a dither of black is a dot lattice (2026-11-08)
- bake: a picture or an error, never a silent success (2026-11-08)
- pane: the strip moves (2026-11-08)
- pane: paint it like a picture, not a page (2026-11-08)
- docs: demo asset inventory (2026-11-08)
- demo: visible keystrokes and pointer, and a one-command capture rig (2026-11-08)
- pack: 302 credits of abstract geometry (2026-11-08)
- demo: caption generator, human-pace typing, and the toolchain decision (2026-11-08)
- docs: demo production plan, and the states-open correction (2026-11-08)
- states: an aside is not a lock (2026-11-08)
- pane: the picture is the size of the pane (2026-11-08)
- docs: task register for the hackathon submission (2026-11-08)
- docs: hackathon submission plan, disclosures, and licence (2026-11-08)
- docs: record the asset pack, and what the plan missed (2026-11-08)
- art: dream is one impossible object, twice (2026-11-08)
- art: the walker is a person, not a capsule (2026-11-08)
- art: a real mug, a real stone, a real card (2026-11-08)
- spec: which pictures the states need (2026-11-08)
- spec: Meshy is installed here, and its key is a human step (2026-11-08)
- spec: real imagery through three.js, not primitives (2026-11-08)
- spec: the pane is the picture (2026-11-08)
- desktop: a pane needs a route, not just a dock (2026-11-08)
- desktop: a pane fed by a served frame (2026-11-08)
- register: close K1d, drop the duplicate K2 line, file K1f under Wave 4 (2026-11-08)
- evidence: re-run the development shard with finish reasons (2026-11-08)
- eval: record why every answer stopped (2026-11-08)
- spec: desktop surfaces, from a review of ascii-worlds (2026-11-08)
- fix: resolve the plugin root from this repository, not the old site path (2026-11-08)
- docs: give the standalone repository its own workspace notes (2026-11-08)
- import: antemuse plugin as a standalone repository (2026-11-08)
- feat(scripts): measured harvest feasibility probe for the task bank (2026-11-07)
- docs(specs): proposal for the evidence task bank the evaluator is missing (2026-11-07)
- docs(plugin): align the written contract with what the measurements support (2026-11-07)
- docs(specs): creative-state-evidence contracts and task register (2026-11-07)
- feat(plugin): collider source bank, bounded auxiliary llm adapter, event projections (2026-11-07)
- feat(evaluation): offline baselines A-C with cache-bound run records (2026-11-07)
- docs: BRD consolidated from the operator's messages (2026-11-06)
- feat(walk): origin binding (T0) — a state belongs to the session and repo it started in (2026-11-06)
- test: the subtractive walk's significant result was verbosity (2026-11-06)
- test: the subtractive walk is the first configuration that moved the right way (2026-11-05)
- feat(walk): subtract, don't add — no material while walking, a forced re-approach on return (2026-11-05)
- test: the far walk changes nothing either (2026-11-05)
- feat(walk): jump, don't step — the outer walk is what /walk does now (2026-11-05)
- docs: with the walk and without, in one table (2026-11-05)
- test: the fast walk changes nothing measurable (2026-11-05)
- feat(walk): three minutes, a step every nine seconds (2026-11-05)
- feat(walk): ten minutes, one step every thirty seconds (2026-11-05)
- test: the creativity sweet spot does not exist at these doses (2026-11-05)
- test: first creativity probe — 8 uses for a brick, idle vs walking (2026-11-05)
- plugin: a bench for what the plugin costs per turn and per frame (2026-11-05)
- plugin: declare the post_tool_call hook it registers (2026-11-05)
- plugin: the agent-facing states live in the project (2026-11-05)

## 0.9.1 — 2026-11-09

QA pass in a throwaway profile (34 checks, `docs/qa/2026-11-09-qa-pass.md`).

- A fresh install now shows a picture instead of a blank card: one 400x105 frame per
  state ships in `assets/frames/` and is used until a real bake exists.
- `python3 -m core.tui` opens the takeover. It had no entry point and exited silently.
- The takeover no longer draws nothing when the terminal reports 0x0, and the
  renderer's `THREE.SoftwareRenderer 82` banner no longer lands in the frame.
- The registered skill describes the five states that ship, not a retired one.
- A mistyped `state` action says which actions exist instead of returning the status
  picture.
- The retired-name test exempts recorded experiment output, so a working tree with
  experiment results does not fail the suite.

## 0.9.0 — 2026-11-09

First packaged build.

- Five states: `walk`, `daydream`, `doomscroll`, `unstuck`, `dream`, each with a
  duration, turn budget, reply contract, residue, and wordless imagery.
- States end on their dose, not the clock; minutes are a ceiling and an expiry
  says how much of the dose arrived.
- Host-enforced tool policy: `block: true` closes tools and a blocked call never
  runs; `allow:` narrows a block and is refused without it.
- `/return` produces an account from the journal without a model call, and keeps
  the residue.
- One recommendation line, emitted only when a counter justifies it (minutes,
  turns, repeated failed calls), always naming the counter.
- Terminal takeover (`python3 -m core.tui`), chat card, text record, and PNG card.
- Six settings rendered as a form by the desktop app; a setting may change how
  loud or long a state is, never what a state is.
- Exploration library (spark/keep, collider, selection) present but runtime-gated
  behind `experimental.enabled`; it makes no quality claim.

Known limits are recorded in `README.md` and in the catalog entry's
`known_issues`.

## Unreleased

- Nothing. Open work lives in `specs/changes/` with an explicit status per item.
