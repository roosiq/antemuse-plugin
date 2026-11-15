# State delivery — acceptance

Change id: `state-delivery`
Status: **implemented and verified**
Tests: `tests/test_state_delivery.py` (9), plus the suite and harness below.

## Criterion → evidence

| Criterion | Evidence |
| --- | --- |
| The final unit reaches the turn that spends it | `daydream` t2, `dream` t2, `doomscroll` t3 now carry the last unit in `[WHAT ARRIVED …]` and only then close. Measured: arrival lines per turn `1, 2` and `1, 2, 3`; before, the closing turn carried the account alone. |
| Removed state | `unstuck` was removed in the one-state cut; its delivery contract no longer applies. |
| A failed source claims no dose | With the provider returning `feed unavailable · nothing to read`, the closing block reads `nothing arrived. Name the source that failed …` and the account `daydream · nothing arrived · nothing to read`. Before: `1 of 2 pairs · feed unavailable`. `/return` afterwards ends `The source failed, so nothing was carried.` |
| A pane poll cannot spend a state | Five `deliver_if_due()` calls with one turn: `served 1 → 5`, `active` still set, `seen` unchanged. The next `inject()` shows them and closes the state. Before, delivery itself closed it. |
| A failure is never presented as material | Arrival stream filters `_is_failure_line`; `[WHAT ARRIVED` does not appear at all for a dead source. |
| Walk still withholds its path | `[WHAT ARRIVED` absent from every walk block; guarded by `test_a_walk_still_withholds_its_material`. |
| `/explore` still never completes | Four turns and four deliveries leave it active; guarded by `removed-state coverage`. |
| The account keeps its privacy rule | `test_the_account_never_quotes_the_material_it_was_given` still passes; no account quotes daydream or dream material. |
| Suite and harness | `933 passed, 1 skipped` (was 924/1) and harness `26/26`. |

## What the fix changed, mechanically

- `complete_if_dosed()` and `_expire()` now require `seen >= served`: a unit is spent when it has
  been put in front of a turn, not when it was fetched.
- `inject()` records `seen = served` when its block carries the material.
- `deliver_if_due()` no longer completes; it splits material from failure lines, counts only
  material, and remembers the last failure. Two empty deliveries, or a dry turn with nothing
  served, ends the state as `failed` with an honest account.
- The arrival stream excludes failure lines.
- `sources.unstuck_text()` appends the seed marker instead of prepending it, so the single served
  line is the direction.
- Copy: the arrival header no longer claims "the person only sees pictures"; the walk's closing
  says the path is there to show the route; the README lists the four endings that exist
  (`complete`, `returned`, `dry`, `failed`) instead of the removed `expired`.

## Tests that encoded the old behaviour, and what they now assert

Five existing tests drove `deliver_if_due()` and expected the state to close without a turn ever
seeing the material — the defect, written down as a contract. They now present the material with
`inject()` before asserting closure, which is the behaviour they were trying to protect:

- `test_semantic_states.py::removed-state coverage`
- `test_semantic_states.py::removed-state coverage`
- `test_semantic_states.py::test_the_account_is_posted_when_the_dose_lands`
- `test_moves_ledger.py::test_a_state_that_finishes_its_dose_records_a_different_ending`
- `test_states.py::removed-state coverage`

## Limits

- The closing turn re-shows the whole journal window for that state, so with a full dose the model
  sees every unit again when it hears the close. That is deliberate (nothing is lost) but it is
  more text than before.
- `dry` is still the stall guard: one turn that serves nothing ends a machine-led state. A
  transient feed failure therefore ends the state as `failed` rather than retrying.
- Accounts still report counts, never quotes; the "name what arrived" question is a separate
  decision (`state-audit`, bucket C).
- The pane can still outrun the agent: a poll serves a unit, and the agent sees it on its next
  turn. The dose can no longer vanish, but the timing can still feel ahead of the conversation.
- Nothing committed, nothing released; `plugin.yaml` stays `0.10.44`.
