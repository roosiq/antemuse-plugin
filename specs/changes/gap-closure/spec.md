# Change: close the three gaps the spec review found

Status: **LIVE** · opened 2026-11-08 · built 2026-11-08

## Intent

The spec review of 2026-11-08 found that four of the five states had been rebuilt to do Ryan's
cognitive move and then never re-measured, and that two of them failed on contact with real
material: dream produced **zero** real connections (`no connection today` then `inventing
instead`, 20/20 trials), and a walk repeated destinations across sessions because nothing
steered it away from a concept the ledger already had. Unstuck delivered quotes cut mid-word
(`'… Worker 'toslop-tem'`), which reads as a defect to the person reading it.

This change closes those three gaps and records the numbers before and after.

## Non-goals

- No new state, command, or setting; no change to doses, ceilings, endings, tool policy, `/return`.
- No claim that a move improves the person's output. These are properties of the material.
- No new input source: dream still reads the repositories' own git history, nothing else.

## What changed

**dream — the day was too thin to connect, and quietly said nothing.** `day_work` counted commit
subjects only, and a word had to appear in fewer than *all* projects to count as a bridge; with
two or three active projects that excluded everything. Now:

- the material is each project's commit subjects **and the file names those commits touched**
  (still local git, still no transcript);
- the document is the **project**, not the commit, so "in every project" means boilerplate and
  "in two of them" is the connection;
- with two projects active, everything they share counts — the old rule made a two-project day
  unable to connect at all;
- a day that is too thin widens the window 24h → 72h → 7 days and **says which window it used**:
  `· window: 7 days (today had too few projects to connect…)`.

**walk — the ledger now steers.** `far`, `orbit`, `vault` and the ordinary step prefer a node
the ledger has not seen, and fall back to a known one rather than stalling (a dead walk is worse
than a repeated one). When it does repeat, the line already says `seen N days ago in M other
sessions`.

**unstuck — quotes are clipped at a word boundary** (`_clip`), and short dictionary nouns that
older ledger rows contain (`drops`, `part`, `rake`) are no longer offered: `unused()` and
`circling()` filter through the same specificity rule that governs extraction.

## Acceptance criteria

1. **dream** produces a connection naming a task on each side when two projects have commits in
   the window, and `note · no connection today` when fewer than two do.
2. dream's window is stated whenever it is wider than a day, and never silently.
3. A walk with a ledger holding all its candidates still delivers every requested step.
4. Walk destinations repeat less with steering than without, measured on the same graph, the
   same dose and the same number of destination steps.
5. No delivered quote ends mid-word.
6. No recommendation is built on a word the extraction rule would reject.
7. Every number below comes from `tools/measure_state_gaps.py` — no model, no tokens.

## Measured (2026-11-08, `tools/measure_state_gaps.py`, archived in `experiments/state-settings/gaps.json`)

| state | before | after |
|---|---|---|
| dream | **0/40** real connections (20 trials × 2 steps, every one `no connection today` then `inventing instead`) | **40/40** real connections, both sides named, shared terms; a thin day now names its window |
| walk | **9.0 %** of 600 destination steps repeated a concept from the previous session (steering off) | **7.8 %** with steering — the effect is real but small, and the repeats that remain are mostly the fixed anchor |
| unstuck | quotes cut mid-word; recommendations over words like `drops` | **100/100** directions carry evidence, **28 %** distinct at dose 1, every quote ends on a word |

The walk number is reported as a small effect on purpose: the graph is large, the baseline
repeat rate is low, and the honest finding is that the *anchor* — every walk starting from the
task's own concept — accounts for most of what repeats.

## Verification

- `tests/test_gap_fixes.py` (7): two-project connection, thin day names its window, one project
  is not a connection, a fully-known graph still delivers, steering avoids a known neighbour,
  a clip ends on a word, a short dictionary noun is not a recommendation.
- `tests/test_state_moves.py`'s two dream tests now patch the seam they actually exercise
  (`_day_window`), because `day_work` no longer controls the connection path.
- Suite: **857 passed, 1 skipped**; `spec_audit` 0 drift.

## Must not change

§18's protected set, the six settings keys, the ledger's identity-only rule (no message text),
and the rule that no state reads a transcript.
