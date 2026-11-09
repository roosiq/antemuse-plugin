# Change: make the states do the moves they are defined as

Status: **LIVE** · opened 2026-11-08 · built 2026-11-08

## Intent

Ryan defined what each state is for (2026-11-08, recorded verbatim in `docs/goals.md`). Measured
against those definitions, the built states are material generators: they deliver concepts,
memories or feed items, and stop before the cognitive move the state exists for.

| state | definition | what it does now | gap |
|---|---|---|---|
| walk | distant **and connected** concepts that may improve the current task | jumps far, no chain back; directive says "no ideas" | anchor to the task, report the chain, rewrite the directive |
| daydream | process, synthesize, introduce new possibilities | recalls and joins memories | the synthesis step is missing entirely |
| doomscroll | distraction via social-media stupidity and comedy | randomised general feeds | comedy pool + a "is this work?" exclusion |
| dream | process the day, connect tasks across projects | invents cross-frame objects | consolidation interface + a cross-project input |
| unstuck | recommend one new thing from history + the concept graph | one direction from thin repo facts | graph input, history input |

## Non-goals

- No new states. Five is the surface.
- No change to doses, ceilings, endings, turn budgets, `/return`, `CONTROL_TOOLS`, the
  wordless card, or the tool-policy default (§18).
- No claim that any state improves output. `walk`'s "may improve" is a hypothesis, not a
  result, and the plugin never reports otherwise.
- No model call added to entry, exit, expiry, tool restoration or rendering.

## Acceptance criteria

1. **walk** — every delivered concept names the current task's concept it started from and the
   hop count back; the directive no longer says the walk supplies no ideas; a walk with no
   task-anchored start is a named failure, not a random jump.
2. **daydream** — every delivered item carries one possibility, phrased as something to try or
   consider, and a pair that does not join still yields one.
3. **doomscroll** — the pool is comedy/shitpost sources only; professional-looking material is
   excluded deterministically, and the exclusion is visible in the delivered line.
4. **dream** — a connection names a task on each side and the shared evidence; invention is the
   fallback when the day is thin, and says so.
5. **unstuck** — exactly one recommendation, citing history and a concept-graph path.
6. Each state's own measure is computed by `tools/experiment_deterministic.py` or a successor
   with no model call, and recorded before and after.

## How #4 was resolved without a privacy change

Dream reads each project's **own commit subjects** (`git log --since=24h`) for the configured
repos — local, already the kind of material this plugin reads, and no transcripts. Hermes
session history and hindsight are deliberately **not** read: that would be a scope change
needing an explicit decision, and it is not needed to find cross-project connections.

## Verification (2026-11-08)

- `tests/test_state_moves.py` — 11 tests, one per acceptance criterion, including "a
  possibility is a hypothesis not an instruction", "the scroll pool is comedy not news",
  "a dream connection names a task on each side across projects", and "a thin day says so".
- End-to-end through the engine with a temp `ANTEMUSE_STATES_HOME`: each state entered and
  delivered, every item carrying its move.
- Deterministic lane re-measured on the new pools: doomscroll distinct 80/72/70 % at dose
  1/3/6 (was 90/83/83 % across 14 general feeds, which no longer qualify).
- Suite: 826 passed, 1 skipped; `spec_audit` 0 drift.

## Must not change

`docs/spec.md` §18's protected set, the six settings keys, `complete`/`returned`/`expired`
endings, the journal cap of 60, the residue cap of 3, and the recommend-never-enter rule.

## Amendment 2026-11-08 — session history is now read, for concepts only

The paragraph above stood when it was written: dream's cross-project input was the day's own
commit subjects, and Hermes session history was deliberately out of scope. Ryan then asked for
the ledger directly — *"also need to be able to identify concepts from past sessions"* — which
is the explicit decision that paragraph said would be needed. `concept-history` reads the
`messages` table of Hermes' own `state.db`, read-only and with a cursor, and `session-scan`
fills it once per session.

What stays true, and is what the paragraph was protecting: **dream itself still reads commit
subjects**, and no state reads a transcript. The ledger stores identity — a term, its kind, a
stable key, the move, the session, the time — and never a message body. No provider and no
`MEMORY.md` is written. Dream now additionally connects concepts that circle across sessions,
which is a second input drawn from the ledger, not a transcript read.

## Acceptance #6 closed, 2026-11-08 — every state now has a number after the rebuild

Criterion 6 asked for each state's own measure, computed deterministically, before and after.
`gap-closure` supplies the three that were missing, and `tools/measure_state_gaps.py` keeps the
numbers reproducible without a model:

- **walk** — 9.0 % of 600 destination steps repeated a concept from the previous session with
  steering off; 7.8 % with it. Small effect, reported as small: most repeats are the fixed task
  anchor, which is the walk's whole point.
- **dream** — 0/40 real connections before (every trial fell through to `no connection today`
  and then `inventing instead`); 40/40 now, both sides named.
- **unstuck** — 100/100 directions carry evidence and 28 % are distinct at dose 1, up from a
  reading where the measurement had been picking the `starts from seed=` header instead of the
  direction.
