# Semantic states — a state ends when its act is complete, not when a clock runs out

Status: **implemented** 2026-11-08 (v1). Owner: Ryan Cook. This changes the state
lifecycle, which §18 protects: durations and turn budgets stop being the *definition* of a
state and become its **ceiling**. The revision is the point of the change.

## Why

A state was a duration: `walk` for 3 minutes, `dream` for 30. That assumed every model
needs the same wall-clock to make the same cognitive move. It does not. A fast model
completes the move in a fraction of the time and then sits inside a state it no longer
needs; a slow model is cut off mid-move. The clock measured the plugin's patience, not
the work.

A state is an **act with a dose**: a walk is a number of moves through the graph, a
daydream is a pair (or two) of memories confronted with whether they join, a doomscroll is
a handful of feed items, a dream is recombinations that land, an unstuck is one direction
named. When the dose is delivered, the state is over — whatever the clock says.

## The rule

**A state ends when its dose is delivered, or when the agent says it is done. A clock may
only end it as a ceiling, and that ending is reported as an unfinished dose.**

Three endings, and they are distinguishable in the record:

| ending | trigger | residue |
|---|---|---|
| `complete` | the dose count reached, or `state(action="complete")` | the act, in its own terms |
| `returned` | the person typed `/return` | the account so far |
| `expired` | the ceiling passed before the dose | `expired before its dose: 3 of 6` |

`/return` remains the person's decision and is unchanged. What changes is that nobody has
to wait for a timer to be told the state is finished.

## Doses, v1

| state | unit | dose | why that many |
|---|---|---|---|
| `walk` | turns worked while the frame is elsewhere | 6 | the walk supplies nothing (it is subtractive); the dose is *time spent working in the changed frame*, counted in turns because turns are work and seconds are not |
| `daydream` | memory pairs confronted | 2 | one join attempt is an accident; two is a daydream |
| `doomscroll` | feed items consumed | 3 | enough to be noise, few enough to stay unserious |
| `dream` | recombinations that land | 2 | one is a novelty; two is a pattern |
| `unstuck` | a direction named | 1 | there is exactly one thing to produce |

Delivery is **per turn, not per second**: while a state is active and its dose is
unfinished, one item arrives at the top of each turn. That is what makes duration track
the model instead of the clock — the same dose costs a fast model fewer seconds and a
slow model more, and neither is short-changed.

## Measured, so the claim is checkable

Every completion records `turns-to-dose` and `seconds-to-dose` per state in
`core/normal.py`'s baseline. That is the number that answers "which models break the state
faster": not an assertion, a distribution per state per model, comparable across sessions.

## What stays

- No model call on the state path. Counting deliveries is arithmetic; the explicit
  `complete` action is a decision the agent makes in its normal turn, not a scoring call.
- Directives, contracts, residue labels, tool policy, `/return`, `CONTROL_TOOLS`, the
  wordless card, the residue and journal caps.
- The ceilings: 3 min walk, 3 min daydream, 8 min doomscroll, 30 min dream, 5 min unstuck.
  They are now safety limits, not schedules, and the picture still moves on its own clock
  (`FRAME_SECONDS`) because art is not a cognitive act.

## Acceptance criteria

1. A state ends as `complete` when its dose count is reached, without any further command.
2. `state(action="complete")` ends a state early and is recorded as `complete`, not as an
   expiry.
3. `expired` reports how much of the dose was delivered: `expired before its dose: 3 of 6`.
4. Material arrives at most once per turn and never by wall clock while the state is
   active.
5. `/return` still ends any state immediately, and the account still describes the window.
6. Turns-to-dose and seconds-to-dose are recorded per state.
7. A model that takes twice as long per turn receives the same dose. (Asserted on
   deliveries, not on seconds.)

## Not built in v1

- **Per-model comparison tables.** The baseline records the numbers; a report that groups
  them by model is a separate, later artefact. Recording is not claiming.
- **Adaptive doses.** A dose could grow for a model that finishes immediately; that is a
  product decision and needs the distribution above first.
- **A clock-free ticker.** The background ticker is removed from the state path in v1;
  art frames still advance from the wall clock.

## Must not change

Directives, contracts, residue labels, tool policy defaults, `CONTROL_TOOLS`, `/return`,
residue cap 3, journal cap 60, two-turn report decay, the wordless card, and the rule that
entry, exit, expiry, tool restoration and rendering never require a model call.
