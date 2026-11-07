# Harvest feasibility probe (task bank T1)

Deterministic local scan, **no model calls**. Generated 2026-11-07 by
`plugin/scripts/probe_task_harvest.py` (stdlib only) over nine repos in
`/home/ryan`. Recount with:

```
python3 plugin/scripts/probe_task_harvest.py
```

Every number below is a count that script printed. Where a metric is misleading
I say so and give the checked sample.

## Counted

- **commits** — `git rev-list --count HEAD` on the checked-out branch.
- **fix-commits** — commit subjects matching `fix|fixes|fixed|repair|resolve|bug|regression`.
- **multifile** — commits touching ≥ 2 non-test, non-`.md/.json/.txt/.lock` files.
- **tests** — files matching test naming **and** living under a `test|tests|spec|__tests__` directory.
- **colocated** — same name match, not under a test directory.
- **messy** — `.csv/.json/.jsonl/.sql/.tsv` > 5 KB under a data-ish path.
- **docs** — `.md` under `docs/` or `specs/`.

| repo | commits | fix | multifile | tests | colocated | messy | docs |
|---|---|---|---|---|---|---|---|
| antemuse | 168 | 18 | 109 | 48 | 1 | 2 | 93 |
| toslop | 105 | 8 | 55 | 0 | 0 | 5 | 5 |
| concept.cooking | 192 | 9 | 162 | 0 | 45 | 2 | 10 |
| slopslingers-infra | 63 | 12 | 45 | 54 | 46 | 113 | 97 |
| toslop-model | 54 | 2 | 12 | 39 | 351 | 30 | 163 |
| ontology-embedding-experiment | 0 | 0 | 0 | 0 | 4 | 8 | 0 |
| brand-agents | 36 | 3 | 13 | 18 | 0 | 0 | 8 |
| ryancook.name | 98 | 6 | 39 | 0 | 0 | 0 | 20 |
| conceptcooking | 47 | 4 | 37 | 4 | 0 | 0 | 0 |
| **total** | **763** | **62** | **472** | **163** | **447** | **160** | **396** |

## Three metric corrections found while checking

1. **`.worktrees` inflate everything.** The first run counted
   `toslop-model/.worktrees/*` as separate source and reported 768 test files and
   1,183 docs for that repo. Worktrees duplicate an existing tree, so they are now
   skipped; toslop-model dropped to 39 + 351 and 163.
2. **An agent-home snapshot inside brand-agents.** `brands/<x>/memory/hermes-home/`
   holds vendored site-packages and other projects' skill tests —
   `.../cache/uv/archive-v0/.../fsspec/tests` and the like. 510 test-file hits came
   from there. Now skipped; brand-agents dropped from 510 to 18.
3. **Strict and loose both lie in opposite directions.** Requiring a test
   directory hides concept.cooking's colocated `src/*.test.ts` (45 of them,
   reported as 0 tests / 45 colocated). Requiring only the name inflated
   brand-agents to 1,134. Both columns are printed rather than picking the
   flattering one.

`has_suite` in the script means "a `pyproject.toml`/`package.json`/`pytest.ini`
exists" — **not** that a suite runs. toslop and ryancook.name report a suite
config and zero test files.

## What the counts actually say

**The independent unit is task × model, so the number to plan against is pairs,
not responses.** A paired sign test's power does not improve by collecting more
responses per cell — replicates reduce noise inside a cell, they do not add
degrees of freedom between conditions. So:

- 170 tasks × 2 models = **340 pairs** → 2,040 responses at 6 conditions, which
  satisfies the "≥ 2,000 provenance-backed protected responses" gate *and*
  resolves a 60/40 blind split at Bonferroni (§7 of the proposal).
- The gate is therefore a **170-task harvest problem**, not a 2,000-task one.
  That is the single most useful thing this probe found.

Against that:

| family | supply signal | measured ceiling | reach 170? |
|---|---|---|---|
| refactor | multifile commits | 472 | **yes** — strongest pool |
| explain | docs under docs/specs | 396 | plausible with curation |
| ideate | specs/brainstorms + 32 already-scored AUT items | unbounded but shallow | yes, weakest provenance |
| extract | messy data files | 160 | **no**, ceiling below 170 |
| diagnose / repair | fix-subject commits | **62** | **no** — hard ceiling |
| decide | claim + evidence pairs | **not demonstrated** | unknown |

`diagnose` is the surprise: only 62 commit subjects across all nine repos even
mention a fix, and yield is always below the subject-line ceiling. The obvious
route — mine the repos for real failures — cannot fill a family. Two ways out,
both honest: draw diagnose tasks from a public benchmark with recorded provenance
(SWE-bench-style, licensed and cited), or make the bank six families and let the
5-family minimum in §5 absorb the shortfall.

`ontology-embedding-experiment` has **zero commits** ("your current branch
'master' does not have any commits yet"), so it cannot supply harvestable
provenance at all under the record-a-commit-hash rule.

## Limits of this probe

- Subject-line matching is a **ceiling**, not a yield: it counts "fix typo" and
  misses squash-merged work.
- A usable `diagnose`/`repair` task needs the failure reproducible at the parent
  commit. Reproduction cost per task is the real harvest cost and is **not**
  measured here — T4's first batch must report wall-clock per usable task before
  anyone commits to 170.
- "messy" counts files, not questions. Several are machine caches with no human
  ask attached, which the harvest rule forbids.
- Nothing here proves any family reaches 170 *good* tasks. §5 stays marked
  target.

## Recommendation

Start harvest on **refactor + explain + ideate** (measured supply above the
floor), give `decide` one bounded pass over toslop-model's 163 evidence docs, and
decide `diagnose` by the external-benchmark question rather than by wishful
counting. Fix the harvest order to prove reproduction cost on the first 10 tasks
before committing to the protected size.
