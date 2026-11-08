# Command surface — five states, one way out, everything else automatic

Status: **implemented** 2026-11-08 (consolidated twice: 14 → 11 → 5; a fifth state, `greenfield`, added the same day and renamed `unstuck` — see `trailhead-state`). Owner: Ryan Cook.
Scope: the `antemuse` plugin's public verbs. No change to state semantics, timers, tool
policy, or rendering.

## The rule

A command is a thing only a person can decide: **which state to be in**, and **when to
stop**. Everything else the plugin can observe, compute from measured signals, or do
through the tool the agent already has — so it should not be a command.

That leaves five:

| Verb | Purpose | Contract | Not this |
|---|---|---|---|
| `/walk [min\|name]` | enter the walk: concept to concept, work continues | returns the entered frame; the walk supplies no material to the turn | not a lockout — tools stay open unless `block: true` |
| `/daydream` | enter: two stored memories, join only if it holds | returns the entered frame | not a search — it does not go looking |
| `/doomscroll` | enter: a random live feed | returns the entered frame | not research — nothing is retained or ranked |
| `/dream` | enter: recombine stored concepts into new things | returns the entered frame | not a plan — no decision is produced |
| `/unstuck` | start a project that does not exist yet | **one direction**, and the spec file that sentence becomes. Reads the repository (`read_file`, `search_files`), changes nothing, and refuses to offer a menu. | a scaffold generator, a plan, or a summary of the repository back to the person. |
| `/return` | leave the state and keep the account | three lines: where it went, what it touched, what is next | not a cancel — residue survives |

## What was removed, and where it went

| Removed | Replaced by | Why it is not a command |
|---|---|---|
| `/note <text>` | **automatic**: while a state runs, the person's own message is journalled as a `person` entry inside the state's window | it asked a person to retype what they had already said |
| `/break` | **automatic**: the recommendation line is already injected when strain trips, once per 45 minutes | a recommendation that arrives by itself beats one you must ask for |
| `/mood` | **natural language → tool**: a person says how it feels, the agent records `state(action='mood')` | mood is *reported, never inferred*; the mechanism belongs to the agent |
| `/state`, `/states`, `/state picture` | **the picture arrives with the state**: the reply carries the frame, the pane shows it, chat gets the still card | nothing to ask for — the state shows itself |
| `/watch` | the pane and the takeover redraw on their own | it was a blocking duplicate of the picture |
| `/spark`, `/again` | **tool actions**: `state(action='spark', goal=…)`, `state(action='spark', goal='again …')` | the person never saw candidates, so the run was never theirs to start |
| `/keep` | **tool action**: `state(action='keep', verdict='love', candidate='#2')` | a verdict on text the person cannot see is not a person's verb |

Earlier in the same session `/watch`, `/again`, `/states` and `/state picture` were
already collapsed once; that earlier table is in the change log. This is the second and
final pass: nothing that a state's own command or a tool action can do remains a command.

## Tool actions after consolidation

One tool, because an agent should not have to remember fourteen names. Fourteen actions,
each defined:

| Action | Purpose | Not this |
|---|---|---|
| `enter` | begin a state (`name`, `minutes`, `walk`, options) | not an override of a running state's clock |
| `exit` | the same path as `/return` | not a cancel |
| `status` | what is running now | not the picture |
| `list` | the states that exist | not the walks |
| `walks` | the walks that exist, built-in and the person's own | not the state list |
| `walk_new` | save a walk definition | does not enter it |
| `walk_del` | remove one of the person's walks | refuses built-ins |
| `break` | recommend a state | not entering — `enter` does that |
| `mood` | record how the work feels | not a state change |
| `spark` | one bounded run for a goal; counts to the person, candidates to the model | not a chat |
| `keep` | record a verdict on `#n` from the run account | not an edit of the candidate |
| `watch` | block a terminal redrawing until the state ends | not model-facing |
| `card` | render the chat card | not model-facing |
| `image` | render the card as a PNG | not model-facing |

## Automation that replaced commands

1. **Person journalling.** `pre_llm_call` reads the person's message from the turn and
   records it as `person` while a state is active, capped at 400 characters. A state's
   account is a page, not a transcript.
2. **The recommendation.** The injected block already carries one offer line, computed
   from measured strain (minutes + turns + failed tool calls), cooling for 45 minutes.
   It is a recommendation, never an entry: entering stays the person's decision. The
   patterns that trigger it are specified in `specs/changes/pattern-recommendation`.
3. **The picture.** The state's own reply carries the frame; the pane shows the moving
   picture; chat gets the still card.

## Acceptance criteria (all enforced by tests)

1. Exactly five registered commands: `walk`, `daydream`, `doomscroll`, `dream`, `return`.
2. Every registered command and every tool action has a row here with its "not this".
3. A person's message during a state appears in the journal as `person`, once per turn,
   and not at all when no state is running.
4. The offer line appears without any command being typed and repeats no more than once
   per 45 minutes.
5. No command exists that only duplicates a state's own command or a tool action.

## Must not change

State definitions, durations, turn budgets, cadences, directives, contracts, residue
labels, journal cap 60, residue cap 3, two-turn decay, `CONTROL_TOOLS`, `/return` as an
escape, and the rule that rendering never needs a model call.
