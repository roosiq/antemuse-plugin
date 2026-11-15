# Audit v4 — the user path, observed

Run 2026-11-14 against the working tree (uncommitted), after the Sonnet 5.5 review fixes.
This one is not a code reading: every line below is something a scripted host and a scripted
person did, with the observed output recorded.

Probes (kept, so the run is repeatable):

- `~/.hermes/cache/scratch/user_audit.py` — a fake host that registers the plugin the way the
  gateway does, then drives commands and turns as a person would. **54/54 checks observed.**
- `~/.hermes/cache/scratch/twosession.py`, `blockdump.py` — the session-ownership probe and a
  full dump of an injected block.
- `~/.hermes/cache/scratch/api_audit.py` — the three HTTP routes through `TestClient`, plus
  four error paths.
- `tools/cockpit_harness.py` — the desktop half, **26/26**.
- `pytest tests/ -q` — **945 passed, 1 skipped**.

## What was observed, surface by surface

### Boot

| Claim | Observed |
| --- | --- |
| One tool, `state` | registered, schema carries `action` |
| Seven commands | `walk, daydream, dream, doomscroll, unstuck, explore, return` |
| Eight hooks | `pre_llm_call, pre_tool_call, transform_llm_output, post_tool_call` + four session boundaries |
| Auxiliary tasks + skill | declared; `antemuse` skill registered |

### Commands

| Call | Observed |
| --- | --- |
| `/walk` | `WALKING · 6 hops · work continues · the frame is elsewhere · different on return` |
| `/daydream` | `DAYDREAMING · 2 pairs · two memories · what they touch · one possibility` |
| `/dream` | `DREAMING · 2 recombinations · the day across projects · connections between tasks` |
| `/doomscroll` | `DOOMSCROLLING · 3 items · random feed · stupidity and comedy · nothing to take away` |
| `/unstuck` | `UNSTUCK · 1 direction · one recommendation · from history and the concept graph` |
| `/explore` | `EXPLORING · 0 picks · you fly · you choose · it ends when you end it` |
| `/return` (idle) | `not in a state.` |
| `/walk 5` | `states are not timed. /walk takes no number; it ends when its dose is delivered.` |
| `/daydream foo` | `only /walk takes a walk name (got 'foo')` |
| `/walk Bad!!` | `walk names are lowercase letters, digits, '-' and '_' (got 'Bad!!')` |
| `/walk audit-walk` | enters and names the walk |

### The turn path

- First turn carries an **866–929 character block**: the contract, the tool rule, and
  `[WHAT ARRIVED WHILE YOU WERE THERE …]` with the material.
- One unit per turn: `served` goes `0 → 1 → 2` across two turns, then the state closes.
- The closing account lands in **residue** and is spoken in the *next* turn
  (`[YOU JUST CAME BACK — the daydream is over …]`), not printed by the plugin.
- The account text is honest: `daydream · 2 of 2 pairs · JOINED · joined ×2`.

### Endings

| Ending | Observed |
| --- | --- |
| `complete` | after the dose is both served and shown |
| `returned` | `WALKING ended · walk · 1 of 6 hops · …` — names what had arrived |
| `dry` | `daydream · 1 of 2 pairs · … · nothing new arrived` |
| `failed` | `daydream · nothing arrived · daydream produced nothing`, and never `complete` |

### `/explore`

No dose (`dose.n = 0`), no turn budget, block opens `[STATE: EXPLORING · open · they end it,
not you]`. Three picks were counted (`served=3`) and `/return` reported
`3 shot(s) on 2 concept(s) · design ×2, planning ×1`.

### The `state` tool — every action

`enter` (unknown name → list of valid states), `status`, `list`, `walks`, `break`, `mood`
(unknown feeling → the four valid ones), `spark`, `exit`, `keep`, and an unknown action
(`no such action: 'nonsense'. try: …`). None raised.

### Sessions

- A state entered in A delivers only into A's turns.
- **A turn from B used to spend A's unit** (see D1). After the fix: `served 1 → 1`, B gets a
  0-character block, and A's second turn still carries the second pair.

### HTTP

Three routes exist — `/state`, `/graph`, `/picks`. `/art`, `/art_b64`, `/versions` are gone
(404), which matches the pane drawing from `/graph`.

- `GET /state` idle → `active: null`, `picture: "pane"`, `plugin: "0.10.44"`.
- `GET /state?session=…` with a walk → `active.dose 6`, `served 1`, `dose_left 5`.
- `GET /graph?limit=5` → nodes + `path`.
- `POST /picks` while not exploring → `{"ok": false, "reason": "not exploring"}` (200).
- `POST /picks` with `{}` → 400 `picks must be a list of concept labels`; with invalid JSON → 422.

## Defects found and fixed in this pass

**D1 — another session's turn advanced a state it did not own.** Observed: a daydream entered
as `A` lost a pair to a turn in `B`; the block was empty for B, the unit was spent anyway, and
`turns` and `_expire` both ran against A's state. Fixed with `engine._owns_state(session)`,
applied in `note_turn()`, `tick()` and `inject()`. Guard:
`test_a_turn_from_another_session_does_not_spend_the_dose`.

**D2 — daydream contradicted itself about tools.** The directive said "No tools, no
instructions, nothing to execute", and the same block said "Tools are open in this state."
Tools *are* open unless the entry asks otherwise (`block=True`), which is the designed
behaviour and is tested; the directive was wrong. Reworded.

**D3 — dream had the same contradiction** ("No tools, no ranking"). Reworded.

**D4 — a stale comment claimed "Five commands"** above a loop that registers seven. Fixed.

**D5 — the pane's walk trail was not the walk.** `GET /graph` returned
`path: ["bowfin","project","bowfin","primitive","freshwater","session"]` after a single hop:
serving rows are every term the line mentioned (relation words, generic words) and a revisit put
the same concept in twice. Dedupe (first occurrence, order kept) removed the repeat.

**D6 — and the trail started one node late.** Hop rows were recorded from the material rather
than from the hop, so the concept the walk left *from* was missing and the pane drew a route with
no beginning. A walk hop is now recorded as itself — `move="walk:hop"`, both ends, part-of-speech
suffix stripped — while the term bag stays as it was for activation. Observed after:
`path: ["design","planning","city planning","zoning"]` for a three-hop walk, in order.

Two tests had encoded the old behaviour and were corrected: `test_a_walk_reports_its_path_in_order`
(counted duplicate rows as path length) and `test_a_state_entered_from_a_chat_lights_the_pane`
(compared a half-label, `morris`, against a full one, `morris dance`). New guard:
`removed-state coverage`.

## Observed, not fixed (and why)

| Observation | Why it stands |
| --- | --- |
| `/walk` on a cold store produced `idea→beef [far]` — a real WordNet path that means nothing | The walk graph's seed and jump quality is `specs/changes/interchangeable-graphs` (R5). Not a regression: it is what `far()` does today. |
| A walk hop is `move="walk:hop"` for the path, but the lighting still comes from the wider term bag | Deliberate: the pane should glow around what the agent is thinking about, and only the *path* has to be the route. |
| The injected block carried notes from the person's real `MEMORY.md` (their own project notes) | Correct: the plugin reads the memory it is documented to read. Worth knowing that any screenshot of a block is private. |
| `transform_llm_output` appends `— daydreaming · 0 pairs left · /return to come back` while the dose is already spent | Cosmetic; the state closes on the next turn. |
| `/return` with nothing running says `not in a state.` | Terse, correct. |
| `/art`, `/art_b64`, `/versions` 404 | Intended: the pane draws from `/graph`. |
| Catalog entry still stale | Release-time regeneration (S6). |

## Verdict

Everything a person can reach behaves as its own spec says, after five fixes in this pass: the
cross-session dose leak (D1), two copy contradictions (D2, D3), the duplicated trail (D5) and the
trail that started late (D6). The remaining rough edge is the
quality of walk hops on a cold store, which is an open spec, not a defect in this build.
