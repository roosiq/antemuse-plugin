# Command surface — one verb, one name, one definition

Status: **implemented** 2026-11-08. Owner: Ryan Cook. Scope: the `antemuse` plugin's
public verbs (slash commands and `state` tool actions). No change to state semantics,
timers, tool policy, or rendering.

## Problem

The surface grew by accretion. There are **14 commands** and **12 tool actions** for
about nine verbs, and several of the duplicates are not synonyms — they disagree about
what the verb means.

| Command | Current description | The defect |
|---|---|---|
| `/state` | "What state the agent is in" | Names the *concept*; a person expects the picture. |
| `/states` | "List every agent state" | One letter from `/state` and means the opposite: one of them is singular-current, the other is plural-catalogue. |
| `/watch` | "Watch the state in the CLI, redrawing until it ends" | Exists again as `state(action='watch')`, which an agent cannot meaningfully call — it blocks a terminal. |
| `/break` | "Recommend a state to step away into, or take the one you name" | Two verbs. "Take the one you name" is exactly `/walk`. |
| `/keep` | "Record what you thought of a candidate: love, like, or trash" | Takes `#1`/`#2` "from the run's account", but **the account line shows counts, never a numbered list** — so `#1` refers to nothing a person can see. The command is unusable as documented. |
| `/again` | "Re-run the last goal with the sources your verdicts point at" | Depends on `/keep` verdicts, so it is downstream of a command nobody can successfully call. |
| `state(action='card' / 'image' / 'list' / 'status')` | — | Four actions that are views, not decisions: the model never needs to render the human's card. |

Also stale: the module docstring still advertises `/dissociate`, a retired name, and
describes the tool as `state(action=enter|exit|status|list)` when the schema has twelve.

## What a verb has to answer

Every public verb must state, in one line each, all four of these. A verb that cannot
answer all four is not defined and should not ship:

1. **Purpose** — the change in the world it makes.
2. **Trigger** — who calls it: the person, the agent, or both.
3. **Contract** — what it returns or changes, in one sentence.
4. **Not this** — the nearest thing it must not be confused with, named explicitly.

## Proposed surface: nine verbs

| Verb | Purpose | Who | Contract | Not this |
|---|---|---|---|---|
| `/walk [min\|name]` | enter the walk: concept to concept, work continues | both | returns the entered frame; a walk supplies no material | not a lockout — tools stay open unless `block: true` |
| `/daydream` | enter: two stored memories, join only if it holds | both | returns the entered frame | not a search — it does not go looking for new material |
| `/doomscroll` | enter: a random live feed | both | returns the entered frame | not research — nothing is retained or ranked |
| `/dream` | enter: recombine stored concepts into new things | both | returns the entered frame | not a plan — no decision is produced |
| `/return` | leave the state, keep the account | both | returns three lines: where it went, what it touched, what is next | not a cancel — residue survives |
| `/state picture` | show the picture now | person | tty: takeover until the state ends; otherwise: the chat card | not a catalogue — it does not list states |
| `/states` | **deprecated shim** | person | same as `/state picture`, kept so old fingers work | not a catalogue despite the name |
| `/state` | one text frame of the current moment (not the catalogue) | person | returns the state strip as text | not the picture — that is `/frame` |
| `/note <text>` | put the person's observation into the same state | person | appends a `person` journal entry inside the state's window | not a message to the model unless the state feeds |
| `/break` | recommend a state to step away into | person | returns one recommendation with the reason | **not** a way to enter — entering is the state's own command |
| `/mood <feeling> [note]` | record how the work feels, reported never inferred | person | appends a mood entry and returns the strain arithmetic | not a state change |
| `/spark <goal>` | one bounded run for that goal | person | returns counts and statuses; candidates go to the model only | not a chat — the person never sees candidate text |
| `/keep love\|like\|trash <#n\|id>` | record a verdict on one candidate | person | stores the verdict and returns the updated counts | not an edit of the candidate |
| `/spark again [deepen\|refresh]` | re-run the last goal from what survived | person | returns the new run's account | not a re-selection of the same candidates |

That is **nine state/observation verbs plus four exploration verbs**. Two cuts are
load-bearing:

- **`/break <name>` is removed.** It duplicated `/walk` while claiming to be a
  recommendation, which is the only thing that made it a separate verb. `/break` with
  no argument stays.
- **`/states` becomes `/frame`.** A one-letter difference between "what I am doing" and
  "the picture, now" is a naming bug, not a feature.

And two additions that make an existing verb real:

- **`/keep` needs numbering that exists.** The run account must read
  `3 candidate(s) #1–#3` so that `#2` refers to something the person can see. Counts
  stay counts; no text crosses over.
- **`state(action='card'|'image'|'watch')` are removed from the model-facing schema.**
  A model does not render the person's card and cannot watch a terminal.

## Migration

1. Add `/frame`; keep `/states` as a deprecated alias for one release, returning the
   picture and a line saying it was renamed.
2. Make `/break <name>` return "that is `/walk <name>`" instead of entering.
3. Publish the numbering in `Run.account()`; `/keep #n` becomes usable without any
   other change.
4. Drop the three view actions from `STATE_SCHEMA`; keep them handled (so an old caller
   does not crash) but undescribed.
5. Update the module docstring: no `dissociate`, twelve actions listed once.

## Acceptance criteria

1. Every registered command and every tool action appears in the table above, with all
   four answers — enforced by a test that reads the registrations from the plugin.
2. No two verbs differ only by plurality or by an auxiliary (`state`/`states`).
3. `/keep #2` succeeds against a real run account line, on a surface that shows `#1–#3`.
4. `/break walk` does not enter a state; it names the command that does.
5. The docstring names no retired state and no action count that disagrees with the
   schema.

## Must not change

State definitions, durations, turn budgets, cadences, directives, contracts, residue
labels, journal cap 60, residue cap 3, two-turn decay, `CONTROL_TOOLS`, `/return`'s
existence as an escape, or the rule that rendering never needs a model call.

## Tool actions

The `state` tool is one tool because an agent should not have to remember twelve names;
its actions still have to be defined one at a time.

| Action | Purpose | Contract | Not this |
|---|---|---|---|
| `enter` | begin a state | `engine.enter(name, minutes, walk, options)` → the entered frame | not an override of a running state's clock |
| `exit` | leave the state | same path as `/return` | not a cancel |
| `status` | what is running now | the state dict for the current moment | not the picture |
| `list` | the states that exist | names, durations, turn budgets, contracts | not a catalogue of walks — that is `walks` |
| `walks` | the walks that exist | built-ins plus the person's own | not a state list |
| `walk_new` | save a walk definition | writes one JSON walk, returns the report | not entering it |
| `walk_del` | remove one of the person's walks | refuses built-ins | not a reset of every walk |
| `break` | recommend a state | one recommendation with a reason | not entering — `enter` does that |
| `mood` | record how the work feels | appends a mood entry and returns strain | not a state change |
| `watch` | block a terminal redrawing until the state ends | returns when the state ends | not a model action — a person's surface, kept for parity |
| `card` | render the chat card | text frame, no words | not model-facing: the model does not publish the person's card |
| `image` | render the card as a PNG | path to the PNG | not model-facing either |

**`watch`, `card` and `image` are surfaces, not decisions.** They stay handled so an
older caller does not crash, but they are removed from the description a model reads:
a model cannot watch a terminal and should not be publishing the human's picture.

## What was consolidated

| Before | After | Why |
|---|---|---|
| `/state` (text) + `/states` (picture) + `/watch` (picture, blocking) | `/state` and `/state picture` | Three names, two answers; one of them described as a catalogue. |
| `/again [deepen\|refresh]` | `/spark again [deepen\|refresh]` | The same run with a different source set is a mode of `/spark`, not a verb. |
| `state(action='card'|'image'|'watch')` | handled, undescribed | Surfaces, not decisions. A model does not publish the person's card and cannot watch a terminal. |

**14 commands → 11** (10 verbs plus one deprecated shim that answers to `/states`).
`/watch` and `/again` are gone rather than aliased: both were pure duplicates, and a
redirect that still exists as a command is not a consolidation.

Implemented 2026-11-08; the five parity tests in `tests/test_command_surface.py` were
turned to the new names, so a verb without a definition fails the suite.
