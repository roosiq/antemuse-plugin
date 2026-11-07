# Evidence task bank — task register

Statuses: `[ ]` pending, `[~]` active, `[x]` verified complete, `[!]` blocked.
A task is `[x]` only with in-scope diff, specification review, code-quality
review, and reproduction of its verification by the controller.

T0 and T1 are deterministic and local. They need no provider and no quota.

## Stage 0 — feasibility and contract

- [ ] T0 Freeze this proposal after Ryan answers D1–D5 (§8). Nothing downstream
      starts before that. *Verification: answers recorded in §8 with dates.*
- [x] T1 Harvest feasibility probe — done 2026-11-07, local and deterministic,
      no provider calls. `plugin/scripts/probe_task_harvest.py`; results and
      metric corrections in `plugin/docs/research/task-harvest-probe.md`.
      Measured across nine repos: 763 commits, 62 fix-subject commits, 472
      multi-file commits, 163 + 447 test files, 160 messy data files, 396 docs.
      Findings that changed this spec: the gate is a **170-task** problem rather
      than a 2,000-task one (paired power counts task × model pairs, not
      responses); `extract` ceilings at 160; `diagnose` ceilings at **62** and
      cannot be filled internally, which opened D5; `decide` is undemonstrated;
      `ontology-embedding-experiment` has zero commits so it cannot supply a
      provenance hash at all.
      Explicitly not measured by T1: reproduction cost per usable task, and
      whether a multi-file commit makes a good refactor task — both move to T4.
      *Verification: `python3 plugin/scripts/probe_task_harvest.py` reproduces
      the table; three metric corrections are documented with checked samples.*

## Stage 1 — bank and loader

- [ ] T2 `TaskArtifact` schema and strict offline loader in
      `evaluation/tasks.py`, mirroring `core/collider.py` discipline: missing
      field, unknown family, unknown split, missing provenance, hash mismatch,
      or an oracle value implying more verification than it has all raise by
      field name. *Verification: focused tests covering each failure by name,
      plus a loader test that rejects a task with no `provenance.source`.*
- [ ] T3 Split manifest: `dev` / `calibration` / `protected` with disjoint task
      ids, disjoint provenance sources per family across splits, and a recorded
      freeze hash. *Verification: a test that fails on any id in two splits and
      on any provenance source shared between calibration and protected.*
- [ ] T4 Harvest scripts, one per family, writing artifacts with provenance, in
      measured-supply order: refactor, explain, ideate, extract. No script may
      synthesise a brief that does not exist in its source.
      **First batch is 10 tasks, and must report wall-clock per usable task plus
      the rate at which a candidate survives its oracle check.** Protected size
      is not committed until that rate is known.
      *Verification: re-running a script reproduces identical artifacts and
      hashes; spot-check five artifacts per family against their recorded commit
      and path; the 10-task batch reports cost and survival rate.*

## Stage 2 — measurement contract

- [ ] T5 Length covariate: record words per response in every run record, and
      add paired raw plus within-task length-adjusted contrast to
      `evaluation/statistics.py`. *Verification: a fixture where the raw
      difference is positive and the adjusted difference is null, reported as
      such — the incubation case, encoded as a regression test.*
- [ ] T6 Oracle runners for `test` and `diff` oracles, provider-free, emitting
      per-task pass/fail with the command and exit status recorded.
      *Verification: an oracle run against two known responses, one correct and
      one wrong, producing opposite verdicts.*
- [ ] T7 Coverage and guardrail report: fail closed on a missing
      task × model × condition cell, on oracle share below 60%, and on any
      guardrail regression beyond the predeclared margin. Extends
      `evaluation/report.py`.
      *Verification: a shard with one removed cell and one removed oracle task
      both fail with named errors.*

## Stage 3 — driver (the missing piece)

- [ ] T8 Provider driver script that injects transport into `run_condition` and
      writes immutable records to a per-run directory. Keeps `evaluation/`
      offline. Refuses to run protected shards without the freeze hash.
      *Verification: one dev-shard run with real calls producing complete,
      replayable records — a second run reports cache hits and zero calls.*
- [ ] T9 Pilot: 20 tasks × 2 models × 6 conditions (≈ 720 calls). Report
      per-cell variance, per-cell cost, per-cell words, and abstentions.
      *Verification: no missing cells; the numbers land in
      `docs/research/task-bank-pilot.md`.*

## Not in scope here

Conditions D–G implementation, collider/orchestrator wiring, runtime
registration, `/spark`, and anything requiring D4 licensing sign-off.
