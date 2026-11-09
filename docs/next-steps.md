# Next steps — spec review, 2026-11-08

Reviewed every change spec (23) plus `docs/spec.md`, `docs/architecture.md`. Ordered by
what is time-bound, then what unblocks a claim, then what is craft. Statuses are the
repository's four words: LIVE · PARTIAL · PROPOSED · NOT BUILT.

## P0 — the submission has a deadline: 2026-11-11 17:00 EST

`specs/changes/hackathon-submission` (planning). This is the only item with a clock on it,
and it gates nothing else — so it goes first, and it finishes or fails on its own merits.

Machine work, done or doing now:

- A13 README accuracy — **done**: the opening claimed four states and a clock-decided
  ending; `/break`, `/states`, `/note`, `/watch` were still listed after the consolidation;
  the strain paragraph survived the deletion of the strain score. Rewritten against the
  code, and a Settings section added.
- A6 catalog entry — **done**: `plugin-catalog/antemuse.yaml`, generated from the manifest
  by `tools/catalog_entry.py --check` so version, hook count and the pinned SHA cannot
  drift from the commit they describe.
- A3/A4 — **verified locally at HEAD**: `hermes plugins validate` 16/16 checks `ok: true`,
  `warnings: []`; `hermes plugins doctor` reports 1 tool, 8 hooks.
- A9/A10 — LICENSE is MIT (compatible with bundled MIT three.js and the CC BY 4.0 collider
  data); the Disclosures section already covers network reads, memory reads, writes, the
  child process, dev tools, credentials, telemetry and updates. Unchanged.
- A14 — named failures for the demo are already strings in the code (unavailable feed,
  missing `nltk`, expired state, blocked tool); the demo script must show at least two.

Human gates, cannot be done by an agent (spec §6):

1. `gh auth login -h github.com` — the stored `roosiq` token is invalid.
2. Creating the public repo and pushing (A1/A2 need it to exist).
3. The X post (A7, <90 s, tags `@NousResearch`) and the Typeform (A8).

## P1 — turn the doses from judgement into numbers

`specs/changes/state-settings-experiment` (PROPOSED). Nothing about the five doses or the
two crossed settings is evidence-based; the spec was written before the data, with the
"no measurable result" row included.

Done now, all of it inside the "no sessions run" line:

- `experiments/state-settings/preregistration.md` — hypotheses, arms and doses per state,
  the five block seeds derived deterministically and recorded as hashes, the frozen outcome
  definitions, the fixed exclusion list, the stopping rule and the unchanged decision rule.
- `tools/ledger_check.py` + `tests/test_ledger.py` (10 tests) — the ledger refuses the
  records that would make the analysis a lie: a guess in place of a boolean outcome, an
  excluded entry carrying an outcome, a control entry with a dose, `unstuck` with a half
  arm, zero tokens recorded, an unknown ending.

Next for P1: run the pilot (60 entries per arm) on request — **no cron, no unattended
spend**.

## P2 — art: the one thing Ryan has called out twice

`immersive-visuals` (PARTIAL) and `scenes-per-surface` (PARTIAL). The picture is real; the
composition is not finished. Specifically:

- `doomscroll` sits at 18 % ink in a 116×74 pane — the weakest of the four, and
  `slab_wall` was generated for exactly this.
- `unstuck` has no art at all and borrows the walk scene.
- The third Meshy wave is incomplete (`slab_wall`, `plate_stack_face`,
  `engraved_panel_large`, `hyperboloid_tall`, `square_arch_monolith`).

This is spend, not risk: it needs Meshy credits and a pane-sized verification pass. It is
P2 only because P0 has a deadline.

## P3 — decisions that are one paragraph each

1. **`scene3d-renderer` (PROPOSED) conflicts with the shipped bake pipeline.** Two
   renderers is one too many. Recommendation: mark it superseded, keeping its reasoning as
   a rejected alternative in `immersive-visuals`.
2. **`state-evidence-task-bank` is a draft for Ryan**, and it is what Path A (the judge)
   needs. Deferred by the earlier "B first then A" order; it should be approved or dropped
   rather than left open.
3. **`pattern-recommendation` PARTIAL** — churn and return-hangover remain NOT BUILT for
   stated reasons (no topic-shift counter; needs a model judgement). Either build a
   measured topic-shift counter or delete the rows. Recommendation: delete the rows until
   a counter exists.
4. **`normal-baseline` PARTIAL** — loop / wall / saturation keep fixed thresholds. The spec
   says why (no distribution yet). Leave it; the experiment in P1 is what will produce the
   distribution.
5. **`state-entry` PARTIAL** — doomscroll stays undirected by design; nothing to do.

## Not next

- No new states, no new commands, no settings beyond the six that exist.
- No claim anywhere that a state improves the work. The evidence is directional and
  underpowered (p = 0.17, n = 8), and the demo is required to say so by omission, not by
  insinuation.
