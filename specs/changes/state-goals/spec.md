# Change: make the states do the moves they are defined as

Status: **PROPOSED** · opened 2026-11-08

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

## Open decision (blocking #4)

Dream needs cross-project evidence. Candidates: Hermes session history, hindsight memory, or a
repo-activity source. Reading other projects' transcripts from a plugin is a privacy and scope
change and needs Ryan's explicit approval.

## Must not change

`docs/spec.md` §18's protected set, the six settings keys, `complete`/`returned`/`expired`
endings, the journal cap of 60, the residue cap of 3, and the recommend-never-enter rule.
