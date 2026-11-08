# Evidence task bank — proposal

Status: **draft for Ryan. Not approved.** This change proposes the data layer the
`creative-state-evidence` harness needs. It changes no code and supersedes no
approved contract. Two decisions in §8 are yours, not the controller's.

Owner: Ryan Cook. Scope: `plugin/evaluation/tasks/`, a harvest script, and this
spec. Nothing here activates runtime behaviour.

## 1. Why this exists

`creative-state-evidence` built a careful evaluator and gave it two things to
evaluate: `dev-lighthouse-door` and `dev-late-bus-ticket`, both "write the next
paragraph" of fiction. `run_condition` is called only from tests; no driver talks
to a provider. Conditions D–G — the Antemuse conditions — do not exist yet.

Meanwhile the promotion gate in that spec (§9) requires at least **2,000
provenance-backed protected responses** replicated across at least two generator
families. The distance between two invented prose prompts and 2,000
provenance-backed samples is the whole project, and no artifact budgets it.
Building collision and orchestration (waves 2–3) on top of a two-prompt fiction
set means reshaping it later. The data layer is the binding constraint, so it
comes first.

There is a second reason, from our own measurement. `break-and-mood`
`incubation-test.md` reached p = 0.027 on a pre-declared metric and lost the
entire effect when the walk arm's 43 extra words were regressed out
(+0.15 categories, CI [−0.70, +1.00]). Judge preference on prose is where models
reward flourish. A task bank that keeps that lesson unaddressed will produce the
same false positive with a bigger n.

## 2. Goal and non-goals

**Goal.** A versioned task bank with real-work tasks, harvested provenance,
objective success checks where they exist, predeclared splits, and a stated
power/cost budget, so that a measured difference between conditions means
something about the agent's work rather than about a fiction prompt.

**Non-goals.** No new states or methods. No runtime activation. No dashboard. No
composite creativity score. No scraped or pseudo-labelled task set — an
unlabelled crawl is not improvement evidence.

## 3. What a task is

Every task is a `TaskArtifact`:

| field | rule |
|---|---|
| `id` | `fam-<family>-<seq>` |
| `family` | one of §4 |
| `brief` | the ask, self-contained, no reference to Antemuse |
| `provenance` | where it was harvested from: repo + commit + path + content hash, or public source + URL + retrieval date. **Harvested, never authored.** |
| `oracle` | how success is checked: `test` (a command passes/fails), `diff` (a stated constraint is verifiable), `rubric` (blind judge only), `none` (counts against the §6 rubric-only ceiling) |
| `reference_artifact` | the real thing that answered it before, if one exists (a commit, a merged fix, a written explanation). Context for judges only; never shown to the condition. |
| `word_budget` | predeclared target band for the response, and the recorded actual length |
| `difficulty` | `short` (≤ 8 tool calls), `medium`, `long` |
| `forbidden` | explicit exclusions (secrets, credentials, real named people, irreversible actions) |
| `split` | `dev` \| `calibration` \| `protected` |

**Harvest rule.** A task must come from work that already happened — a failing
test and its fix, a real refactor, a messy extraction someone actually needed,
a question Ryan actually asked and got an answer to — or from a public benchmark
with a recorded source. Tasks invented to be creative-looking are the failure
mode this spec exists to prevent. Tasks with no derivable oracle are allowed but
capped (§6).

**Feasibility was measured, not assumed.** T1 in `tasks.md` ran a deterministic
scan over nine repos (`plugin/scripts/probe_task_harvest.py`, results in
`plugin/docs/research/task-harvest-probe.md`). It showed which families have
supply and which do not — see the note under §5. Counts in §5 remain targets,
because supply is not yield: yield needs reproduction, which T4 measures.

## 4. Families

Seven families, chosen so that at least four of them have an objective check and
so that the one family with a measured history (divergent ideation) is kept
rather than dropped.

1. **diagnose** — a real failing test, traceback, or wrong output; find the
   cause. Oracle: `test`.
2. **repair** — a real defect with a stated constraint; make it pass without
   widening scope. Oracle: `test`.
3. **refactor** — restructure with behaviour preserved. Oracle: `diff`.
4. **extract** — turn a messy real artifact into a stated structured shape.
   Oracle: `diff`.
5. **decide** — is this claim supported by this evidence? Verdict plus reason.
   Oracle: `diff` against the recorded ground truth.
6. **explain** — a real thing explained to a stated audience at a stated length.
   Oracle: `rubric`.
7. **ideate** — divergent options under stated acceptance criteria. Oracle:
   `rubric` plus the WordNet-category and reuse measures already used in
   `break-and-mood`, so the one comparable history stays comparable.

`explain` and `ideate` are where a walk or a dream could plausibly help, and also
where a judge is weakest. They are never the only evidence for promotion.

## 5. Splits and the independent unit

The independent unit is **task × model**, paired within task, clustered by task
(that design is already in `evaluation/statistics.py` and is kept).

| split | tasks | final responses at 2 models × 6 conditions | use |
|---|---|---|---|
| dev | 40 | 480 | design, tune, debug |
| calibration | 60 | 720 | source-diverse held-out; thresholds |
| protected final | 170 | **2,040** | the promotion claim |

Protected rules inherited from `creative-state-evidence` §9: freeze
prompts, sources, thresholds and analysis before viewing; viewing protected
results after any change requires a new protected set.

**Pairs, not responses.** Power for a paired contrast depends on the number of
task × model *pairs*, not the number of responses collected — replicates shrink
noise inside a cell and add nothing between conditions. 170 tasks × 2 models is
340 pairs and 2,040 responses at 6 conditions, so the "≥ 2,000 responses" gate is
a **170-task harvest problem**, not a 2,000-task one. Plan the harvest against
pairs; the response count is a consequence.

Measured supply against that (see `docs/research/task-harvest-probe.md`, same
repo, recountable): refactor 472 multi-file commits and explain 396 docs clear
the bar; extract tops out at 160 files; **diagnose has a hard ceiling of 62
fix-subject commits across all nine repos** and cannot be filled internally;
`decide` is not yet demonstrated at all.

The 170 protected tasks must span at least five families and be drawn from at
least four distinct provenance sources per family, so a win cannot be an
artifact of one repo's shape.

## 6. Measurement rules added here

1. **Length is a predeclared covariate, not a post-hoc excuse.** Every
   comparison reports words per response per cell, and the primary contrast is
   reported both raw and length-adjusted within task. A promotion claim that only
   survives the raw number is not a promotion claim. This is the direct
   generalisation of the incubation lesson.
2. **Oracle-first.** At least 60% of protected tasks must carry a `test` or
   `diff` oracle. A method may not be promoted on rubric-only evidence, and a
   rubric win that coincides with an oracle regression fails the guardrail.
3. **Judge discipline.** Blind pairwise only, condition names never in the
   judge-facing projection (already implemented in `evaluation/judges.py`), two
   judge families, concordance reported, and any judge disagreement larger than
   the predeclared margin voids that contrast rather than averaging it away.
4. **Guardrails.** task success, instruction following, and refusal to invent
   facts, each with a predeclared maximum acceptable regression.

## 7. Arithmetic and cost (so the budget conversation is explicit)

Power for a paired sign test at 80%:

| blind win-rate | α = 0.05 | α = 0.01 (Bonferroni over 5 contrasts) |
|---|---|---|
| 0.55 | 783 pairs | 1,165 pairs |
| 0.60 | 194 pairs | 289 pairs |
| 0.65 | 85 pairs | 127 pairs |
| 0.70 | 47 pairs | 70 pairs |

At 170 protected tasks × 2 models the design resolves a **65/35** blind split at
Bonferroni and a **60/40** split uncorrected. Smaller true effects are invisible
here; that must be said in the report rather than discovered later.

Call volume for the protected run (6 conditions, best-of-N=3 on C, 5 contrasts,
2 judges): 2,720 generation calls + 3,400 judge calls = **6,120 calls, ≈ 10M
tokens**. The pilot that sizes variance is 20 tasks × 2 models × 6 = 240 final
responses, ≈ 720 calls.

For scale: the Nov 6 lane session exhausted a daily usage window in about 2.2
hours of single-worker work. The protected run is a multi-day, multi-model
budget, not a session. Decide it deliberately (§8, D3).

## 8. Decisions that are Ryan's

**D1 — Primary outcome.** The current spec's primary is blind best-overall judge
quality. My read is that on fiction prompts that is the weakest available signal,
and it is exactly the metric that manufactured our one false positive. Proposal:
primary becomes oracle-verified task success plus judge quality **on real-work
tasks**, with prose quality secondary. Alternative: keep judge quality primary
and accept that Antemuse is being evaluated as a creative-writing product.

**D2 — Harvest-only provenance.** Adopt "harvested, never authored" (§3). Cost:
harvest is slower and caps the bank at what real work produced. Alternative:
allow authored tasks and accept that the bank can drift toward whatever a model
thinks a good task looks like.

**D3 — Budget and schedule for the protected run** (§7), including which two
generator families.

**D4 — Collider licensing** — **RESOLVED** as `C3` in the other register: the six
artifacts are `OC_data/` material, licensed CC BY 4.0 upstream (MIT covers
`script/` only). Artifacts now carry `license=CC-BY-4.0`, a licence URL, and the
credit line, and `core/collider.py` rejects a record that omits or alters any of
them. Public distribution needs `data/collider/ATTRIBUTION.md` to travel with them.

**D5 — `diagnose` provenance.** Internal supply has a measured ceiling of 62
fix-subject commits, so this family cannot be filled from Ryan's own repos.
Options: pull diagnose tasks from a public benchmark with recorded source and
license (keeps seven families, adds an external dependency), or drop the family
and run six (the §5 five-family minimum survives it). Do not pad it with authored
failure scenarios — that is precisely the drift §3 exists to block.

## 9. Must not change

- `evaluation/` stays provider-free and deterministic; the driver is a separate
  script that injects transport, so tests keep running offline.
- Nothing registers a model call on the state path; entry, exit, expiry, tool
  restoration and rendering stay LLM-free.
- No method becomes default-on.
- Existing dev fixtures stay in the tree for regression, marked
  `split: dev, oracle: rubric`, and are never quoted as evidence.
