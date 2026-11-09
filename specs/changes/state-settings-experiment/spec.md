# State settings experiment — what dose of a state actually produces results

Status: **PARTIAL** 2026-11-08. Owner: Ryan Cook. The deterministic lane has been measured
(`tools/experiment_deterministic.py`: 150 trials/cell, zero model calls). The model lane is
exploratory and its three entries are excluded. **No dose has been changed from these
numbers**, and no number here is a claim that any state improved anyone's work.

## The question

Every state now has a **dose** and a **ceiling** (`specs/changes/semantic-states`), and
both were chosen by judgement: walk 6 turns, daydream 2 pairs, doomscroll 3 items, dream 2
recombinations, unstuck 1 direction. The settings surface exposes the cooling window and
the long-stretch threshold. None of those numbers has been shown to produce anything.

This experiment asks one question, five times: **does a larger or smaller dose of this
state change what the work produces, and where does it stop paying?**

It does not ask whether the states are creative, pleasant, or worth having. Those are not
measurable here, and stating them would be a claim without evidence.

## What counts as a result, per state

A result must be checkable by a script that never sees a model's opinion. Each state gets
one primary outcome and a stated window.

| state | primary outcome (deterministic) | window | why this is the outcome |
|---|---|---|---|
| `walk` | **carry**: the seeded concept — or a WordNet hypernym/hyponym of it — appears in the work produced after the state (a file diff, or the assistant's own text) | next 6 turns | a walk supplies nothing; its whole claim is that the *next* work moves differently. If the seed never surfaces, the walk did nothing |
| `daydream` | **landing**: a stated pair appears together in one later turn's output; a **kept** pair is one the agent marks with `state(action="keep")` | next 4 turns | a pair that never co-occurs was decoration |
| `doomscroll` | **adoption**: a URL or domain from the delivered items is fetched, cited, or acted on | next 6 turns | the only defensible product of noise is material the agent then uses |
| `dream` | **kept recombination**: `state(action="keep")` naming a recombination, or the compound appearing in a spec/doc written within two sessions | 2 sessions | a dream that changes no artefact changed nothing |
| `unstuck` | **adopted direction**: a spec file or plan written within two sessions whose subject matches the recommended direction | 2 sessions | the direction's only purpose is to become work |

Secondary, recorded for every arm and never used as the primary: turns, tokens in/out,
seconds-to-dose, tool failures, tool blocks, provider errors, and whether the state ended
`complete`, `returned`, or `expired`.

## Arms

Per state, four arms, assigned per **state entry**, not per turn:

| arm | dose | ceiling | purpose |
|---|---|---|---|
| `half` | ⌊n/2⌋ (min 1) | state default | is the default too generous |
| `default` | n | state default | the number that ships today |
| `double` | 2n | 2× default | does more buy more |
| `control` | 0 — the state is not entered; its material is still *generated and logged*, never shown | — | what the same turn looks like with no state at all |

The control is the load-bearing arm. Without it, any result is indistinguishable from the
work happening anyway.

Two settings are held fixed inside a block and crossed between blocks:
`recommend_cooling_minutes` ∈ {45, 120} and `long_stretch_minutes` ∈ {0 (measured), 90}.
They are not crossed at the same time as dose — a factorial of 4 × 2 × 2 per state is a
sample nobody will finish, and a half-finished cell is a guess with a table around it.

## Design

- **Unit of assignment**: one state entry. **Unit of analysis**: one session. Turns inside
  a session are not independent, so a per-turn A/B is arithmetic theatre.
- **Blocking**: sessions are grouped into blocks of 8 entries, two per arm, order
  determined by a pre-registered seeded permutation. Each block records its seed and the
  permutation, so the assignment is reproducible and not chosen after seeing outcomes.
- **Balance across models**: every block runs on one model; the block list cycles the
  available models so each arm meets each model. Model identity is a recorded dimension,
  never a nuisance to be averaged away — the reason for this whole change is that models
  differ.
- **No self-selection**: an entry is assigned by the block, not by the agent's mood, the
  time of day, or the recommender's suggestion. A state the *user* types by hand is
  logged and **excluded** from the analysis, because it was not randomised.
- **Preregistration file** before the first session: hypotheses, arms, block seeds, primary
  outcome code, exclusion rules, and the stopping rule, committed to the repo. Anything
  added afterwards is labelled exploratory and reported separately.

## Pre-registered hypotheses and the decision rule

For each state, against `control`:

- **H1 (present)**: primary outcome rate is higher in `default` than in `control`.
- **H2 (dose-sensitive)**: `double` beats `default`, or `half` is no worse than `default`
  within the equivalence margin.

Decision rule, fixed in advance, per state:

| observed | setting ships |
|---|---|
| H1 holds, H2 shows `half` ≈ `default` | half-dose becomes the default, ceiling unchanged |
| H1 holds, `default` ≈ `double` | default stays |
| H1 holds, `double` > `default` beyond the margin | double-dose becomes the default |
| H1 fails (CI includes 0 or is negative) | **the state's default dose is reported as producing no measurable result**, and the recommendation is to say so on the site and in the docs |
| effect negative | the state is a cost with no benefit; propose disabling it |

The last two rows are the honest ones and they are written down before the data exists,
which is the only time writing them is worth anything.

## Sample size

Primary outcomes are per-entry. Assume a control rate of 0.30 and a target detectable
difference of 0.15 absolute at 80 % power, α = 0.05, two-sided
(n = (z₀.₉₇₅ + z₀.₈)²·(p₁(1−p₁) + p₂(1−p₂)) / (p₂−p₁)² = 7.849 · 0.4575 / 0.0225):
**160 entries per arm**, 640 per state, 3,200 across all five. That is the number the power calculation gives; it is
also more than this machine will run by hand, which shapes the plan below.

Minimum reported sample: **60 entries per arm**. Below that, results are labelled a pilot
and no setting changes. **A pilot is not a result** and will not be cited as one.

## Cost and conduct

- Sessions are run by the user, in batches, on request. **No cron, no background loop, no
  unattended spend.**
- Per-state budget cap is declared before the block starts; exceeding it stops the block
  and is reported as a truncated block, not silently extended.
- An arm may be abandoned only for a platform failure (provider outage, truncation storm),
  never for disappointing outcomes. Every abandonment is logged with its reason.
- Truncated answers (`finish_reason`, `truncated`) are recorded and excluded from the
  primary outcome: a cut-off answer is not a finished one.
- Nothing in this experiment records or publishes prompt text, transcript content, or
  personal data outside the local run ledger. The ledger stores: session id, model,
  provider, arm, block seed, dose, ceiling, entry timestamp, ending reason, the primary
  outcome's boolean, and the counters — never the material itself.

## Analysis

1. Per state, per arm: rate with Wilson CI. Rate difference vs control with bootstrap CI
   (10,000 resamples, resampling *sessions*, not turns).
2. Mixed-effects logistic model with a random intercept per session and fixed effects:
   arm, model, block seed, hours-since-last-state. Reported as an appendix, not as the
   headline — the headline is the rate difference, which a person can check by hand.
3. Equivalence is tested with a pre-declared margin of 0.10 absolute, not inferred from a
   non-significant difference.
4. Withdrawals and abandoned blocks are reported in the same table as the result.
5. Every table states N, the number of excluded entries and why, and the date range.

## What would make this invalid

Named so the run can be stopped rather than argued about afterwards:

- outcome coding changed after seeing outcomes;
- control arm entries that were actually preceded by a state within 24 h;
- sessions where the plugin failed to deliver the declared dose but the entry was kept;
- two arms with materially different model mixes;
- reporting the best block.

If any of these happens, the affected state's result is void for this run and is re-run
from a fresh block.

## Deliverables

1. `experiments/state-settings/preregistration.md` — committed before the first session.
2. `experiments/state-settings/ledger.jsonl` — one line per entry, the fields above.
3. `experiments/state-settings/report.md` — per-state table, decision-rule outcome, and a
   plain paragraph per state saying what the data did and did not show.
4. Settings changes, if any, applied only through the manifest `config_schema` defaults,
   with the report linked from `specs/changes/plugin-settings`.

## Not this

- Not an evaluation of the artwork, the aesthetics, or whether a state "feels" like a walk.
- Not a creative-quality benchmark: no judged "quality" score, no LLM grader as the
  primary outcome.
- Not live auto-tuning. The plugin never adjusts a dose from its own measurements; a dose
  changes when a person changes the default after reading a report.
- Not a claim that a result here generalises past these five states, this machine, or these
  models.

## Open decisions

1. **Is `walk`'s "carry" the right primary outcome?** It is the only state whose product is
   the *absence* of supply, so its outcome is the weakest of the five. Alternative: measure
   divergence of the next work from a no-state baseline by edit-set overlap — more
   expensive, more confounded.
2. **How many models.** Two is the minimum to say anything about model variance; three is
   what makes the claim worth printing. Recommendation: two for the pilot, three for the
   main run.
3. **Who codes ambiguity.** `landing` and `adopted direction` need a judgement at the edge.
   Recommendation: two blind coders on a 10 % sample, Cohen's κ reported; below 0.7 the
   outcome definition is revised before the main run.
4. **Whether `unstuck` belongs here at all.** Its outcome is one spec file within two
   sessions — rare enough that 145 entries per arm may be years of use.

## Acceptance criteria (for the run, not the code)

1. Preregistration committed before session 1, with block seeds.
2. Every entry has all ledger fields; missing fields fail the ledger check.
3. Control entries are verified to have no state within the prior 24 h.
4. Every state's report states N per arm, CI, exclusions, and the decision-rule row it hit.
5. No setting default changes without a report and a linked decision.
6. If H1 fails for a state, the docs say so in the same release.

## Revision 2026-11-08 — the primary outcome is deterministic, and the model lane is exploratory

Run first, then redesigned. `tools/experiment_run.py` executes real `hermes chat -q` turns,
and one six-turn entry costs **~4.0 M input tokens**; a 60-per-arm floor for one state would
have cost ~150 M. A design that cannot be run is not a design.

The question the model lane was built to answer — *does the sixth item earn its keep?* — is
a question about the **material**, and the material is produced by code. `tools/experiment_deterministic.py`
runs the state's own provider, parses the poles of every delivered line, and measures, per
state and dose, with no model and no tokens:

| metric | means | catches |
|---|---|---|
| `novel` | share of poles whose head word is not in this repository's own vocabulary (6,011 words) | the state handing back what the project already says |
| `fresh` | share of poles not already served earlier in the same dose | one item repeated at positions 3–6 |
| `distinct lines` | unique lines / lines across trials | a frozen source (the same six items every session) |

150 trials per cell, all five states, fifteen cells: **seconds, zero tokens.** Results are in
`experiments/state-settings/deterministic.json`.

### What the numbers say (measured 2026-11-08)

| state | dose | novel | fresh | distinct lines | reading |
|---|---|---|---|---|---|
| walk | 3 / 6 / 12 | 70 / 70 / 72 % | 87 / 80 / 78 % | 84 / 85 / 74 % | novelty is flat with dose; **freshness falls** — at 12, one item in five is a repeat |
| daydream | 1 / 2 / 4 | 63 / 70 / 63 % | 100 / 100 / 98 % | 89 / 80 / 62 % | 2 is inside the knee; 4 buys repetition |
| doomscroll | 1 / 3 / 6 | 81 / 86 / 85 % | 100 / 99 / 97 % | 48 / 22 / 11 % | freshness is fine and **variety is not**: the feed is frozen, so six items are near-duplicates across sessions |
| dream | 1 / 2 / 4 | 5 / 8 / 7 % | 100 / 91 / 83 % | 100 / 100 / 100 % | structurally varied, lexically boilerplate: the forms are template, not invention |
| unstuck | 0 / 1 / 2 | 0 / 0 / — | 100 / 100 / — | 1 / 1 / — | **dose does nothing** (5 lines at any dose) and every session says the same thing |

### Decision rule (replaces the model-lane table)

1. A dose may not exceed the smallest k at which `fresh` falls below **0.85**.
   On this data: walk 6 → **4 or fewer**, daydream 2 → **2**, doomscroll 6 → keep, dream 2 → **2**.
2. `distinct lines < 0.30` is a **source defect**, not a dose problem. It fails doomscroll at
   dose 6 and unstuck at any dose; the fix is more feed or a real direction source, not a
   smaller dose.
3. `novel < 0.20` with `distinct = 1.00` is a **generator defect** (dream): the dose is
   irrelevant while the forms are template sentences.
4. No dose changes on this data until the run is at **≥ 150 trials/cell in a clean tree** and
   the numbers are reproduced by someone other than the person who wrote the tool.

### The model lane is now exploratory

`tools/experiment_run.py` stays, with its ledger, as the *cost and plausibility* check: does
the material reach a real turn at all, and what does a turn cost. Its outcomes are reported
as exploratory, never as the decision. The three entries it produced are excluded, and the
reason is recorded per entry.

### What this revision refuses

- It does not claim a state makes anyone more creative. Novelty is a property of the
  generator; usage is a property of a mind. The deterministic lane answers the first, and
  explicitly not the second.
- It does not treat "more novel" as "better" without a human reading the sample.
