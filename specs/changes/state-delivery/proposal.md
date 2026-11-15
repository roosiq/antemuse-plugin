# State delivery — proposal

Change id: `state-delivery`
Status: **gate 1 — proposed, nothing built**
Source: `specs/changes/state-audit/audit.md` (v3)

## Why

The audit found that a state's bookkeeping and its material disagree in three ways, and each one
tells the person something untrue:

1. A failing source is counted as material. the walk with a dead provider closes with
   `2 of 2 pairs · feed unavailable`.
2. The final unit of every feed-enabled state is served and the state closed in the same call, so
   that unit never reaches the turn that is told to react to it. the walk's final unit is also
   its last, so it delivers nothing at all — and its real cause is separate: `unstuck_text()`
   inserts `starts from seed=…` at index 0 and the dose is one line, so the seed marker is served
   instead of the direction.
3. `GET /state` serves a unit per poll, so the pane spends a dose without a turn. Four polls took
   a walk from `served 1` to `served 5` with `turns == 1`.

## Goal

A state's dose counts only material that actually arrived, reaches the turn that needs it, and is
spent once.

## Non-goals

- No new states, no change to what any state says when it arrives.
- No change to the account's privacy rule (`test_the_account_never_quotes_the_material_it_was_given`
  stays green; accounts will not quote daydream or dream material).
- No change to the bystander rule, the `/return` residue window, or the concept ledger rows.
- The panes are untouched.

## Mechanics

1. **Failure lines are not units.** `_is_failure_line()` is consulted before `served` moves. A
   state whose source failed ends with reason `failed`, names the source in the account, and says
   `nothing arrived`. It must not report a dose it did not serve.
2. **Presentation, not serving, spends a unit.** `deliver_if_due()` gains a served-but-unpresented
   notion: the final unit is recorded as presented when `inject()` has built the block that
   contains it, and completion happens on that same turn after the block is assembled — so the
   last material is in hand and exactly one account is produced.
3. **The unstuck seed marker is not material.** `unstuck_text()` stops inserting it at index 0, or
   the delivery slice stops treating it as the unit; the direction (`direction 1 · … because … ·
   first: …`) is what gets served. The seeding line may still appear, appended after the
   direction, if the state's design wants it.
4. **A pane poll may serve, never complete.** `GET /state` keeps delivering so the picture stays
   live, but completion requires a turn to have presented the unit. A pane that drains the dose
   leaves the state ending on its next turn, not silently gone.

## Acceptance criteria

- `/daydream` with a provider that returns only `feed unavailable` completes with an account that
  says nothing arrived, does not claim `2 of 2 pairs`, and ends with reason `failed`.
- For `daydream`, `dream` and `doomscroll`, the final unit's line appears in the
  `[WHAT ARRIVED …]` block of the turn that consumes it, the state then closes, and exactly one
  account is produced.
- Removed-state delivery examples no longer define current behaviour.
  `starts from seed=`.
- Four `GET /state` polls with no turn leave the state open; the next turn presents the unit and
  closes it.
- `walk` still delivers no material by design; `/explore` still ends only on `/return`.
- Full suite green, including the existing privacy, hook-resilience, explore and docs guards.

## Verification

```
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) uvx --with-requirements requirements-test.txt \
  --quiet pytest tests/ -q
```

Plus the production-path probe (one `inject()` per turn) recorded in the acceptance file, with the
before/after block text for each of the five dose states.

## Risks

- Moving completion later could delay the notifier post or change the `/return` reason for a person
  who types it in the same breath as the final unit. The acceptance must record the observed
  reason, not assume it.
- The pane may still drain a state whose sources are slow; `served` stops being proof of anything.
  The invariant becomes "presented", and every reader of `served` has to be checked — HUD, pane,
  `status_line`, `_left_phrase`.

## Files

- `core/sources.py` — `unstuck_text()` ordering.
- `core/engine.py` — `deliver_if_due()`, `complete_if_dosed()`, `_expire()`, `inject()`,
  `_account()`, `_left_phrase()`.
- `dashboard/plugin_api.py` — `GET /state` serving without completing.
- `tests/test_states.py`, `tests/test_semantic_states.py`, `tests/test_explore_api.py`,
  `tests/test_state_delivery.py` (new).
- `README.md` — the `expired` ending that no longer exists goes with this change or the next one.
