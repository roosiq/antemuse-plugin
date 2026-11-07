# Creative state evidence — governing specification

Status: Gate 0 draft for Ryan's review. The two DeepSeek canaries validate worker suitability only; they do not authorize runtime activation.

Owner: Ryan Cook. Controller: Hermes fleet supervisor. Scope: `/home/ryan/antemuse/plugin` and its local evaluation artifacts.

## 1. Goal

Make Antemuse an evidence-gated cognitive-state engine for Hermes. States and methods must improve the agent's final response, diversity, or creativity under predeclared comparative measurements before they are promoted beyond experimental opt-in use.

The person receives surface-appropriate imagery and steering; the model receives actual source material, candidates, and instructions. The final response must still solve the originating task.

## 2. Contract change

The blanket `no model calls, no scoring` rule is superseded for the exploration layer.

- Auxiliary LLM generation and selection are permitted behind an experimental flag.
- Runtime scores are selection aids, never evidence of improvement.
- Entry, exit, expiry, tool restoration, and rendering never require an LLM.
- `/return` and the `state` control tool remain available under every state.
- No method becomes default-on. Each method is promoted independently after protected evaluation.

## 3. Experience and exploration layers

Experience layer: existing walk, daydream, dream, and doomscroll states; expiry; tool policy; imagery; journal; residue; origin binding.

Exploration layer:

- `collide`: transfer mechanisms between distant domains.
- `deep`: decomposition, recombination, and elaboration.
- `chaos`: external randomness and separated contexts.
- `spark`: one bounded diverge → select → synthesize run for one goal.

Collider is a source strategy, not a separate product. Spark is a bounded run, not an always-on middleware layer.

## 4. Real sources

Every source is a `SourceArtifact` with `id`, `kind`, `family`, `title`, `mechanism`, `bridge_question`, `body`, `provenance`, `content_hash`, and `verification_status`.

Sources: WordNet, FrameNet, operator-approved Hermes memory, named public feeds, previous kept Antemuse artifacts, and real Open Collider generated examples.

Initial Collider provenance is `CL-ML/open-collider-research`, commit `6ed948a`, under `OC_data/creativity_engine/`. Initial examples cover acoustic niches, Lombard dynamics, acoustic daylight, mycelial networks, fairy-ring expansion, and selective autophagy.

These are generated prompt artifacts, not verified scientific authority. `verification_status=generated_example` is mandatory. Final factual claims need independent verification. Redistribution licensing for research artifacts must be decided before public distribution.

No invented fallback content. Missing sources produce named failure events and reduced or aborted runs.

## 5. Runtime flow

1. Explicit entry records state, method, origin `{session_id, platform, project}`, source policy, seed, call/token/time limits, expiry, and configuration hash.
2. A deterministic planner selects sources and excludes prior families for `fresh` or kept mechanisms for `deepen`/`refresh`.
3. LLM-enabled runs create independent structured branch contexts. Branches never see one another's candidates.
4. Deterministic cleanup validates schemas, provenance, duplicates, and constraints.
5. Optional LLM selection assesses novelty, usefulness, coherence, surprise, and potential. These scores are not proof.
6. Selection keeps collided insights and an `insights_without_collision` channel for strong candidates that do not depend on the collision.
7. Human `love`/`like`/`trash` feedback drives `deepen` and `refresh`.
8. Prepared artifacts enter the originating Hermes turn. The agent answers the task and may use, combine, or reject candidates.
9. The run returns an account with sources, branches, selection, failures, and actual usage.
10. Exit and expiry are deterministic and safe without inference.

## 6. Hermes integration

- `ctx.register_auxiliary_task()` for generation, selection, and refresh routes.
- `ctx.llm.acomplete_structured()` for host-owned structured auxiliary calls.
- `pre_llm_call` for origin capture and prepared-artifact injection.
- `llm_request` only for bounded active-state request settings; preserve tools and frozen system-prompt sections.
- Do not fan out through `llm_execution.next_call()`; downstream execution is single-use.
- `post_llm_call` for final-response association.
- Existing tool hooks and output transform remain intact.
- Primary and auxiliary API hooks measure actual attempts, models, usage, latency, and failures.
- Session end/finalize/reset/delete hooks prevent delayed artifacts crossing sessions.
- `ctx.session_cwd()` and `ctx.session_surface()` improve project and surface identity.
- `ctx.emit()` publishes typed operational events, not private reasoning.
- Initial delivery rides the originating turn; no home-channel routing or background send service.

A future dashboard may show sources, branches, candidates, selection, and usage. It must not expose chain-of-thought or private source material.

## 7. Evaluation conditions

- A: ordinary Hermes baseline.
- B: length-matched `be creative` instruction.
- C: baseline best-of-N with the same selector.
- D: deterministic Antemuse sources without auxiliary inference.
- E: separated branches without Collider sources.
- F: separated branches with Collider sources and selection.
- G: F plus human feedback and refresh, evaluated only after F survives.

Use fresh isolated sessions, frozen sources, recorded seeds, and model/condition/task/prompt/source/seed-aware caches. Run equal-final-response and equal-total-inference comparisons.

## 8. Outcomes

Primary: blind best-overall response quality against the appropriate control, with task-success and instruction-following guardrails.

Secondary: semantic diversity with two embedder families; structural diversity; novelty against baseline responses; usefulness/coherence; source-dependent emergence; blind human preference and judge concordance; exploration efficiency per token, dollar, and second; robustness across tasks and generator families.

Candidate-pool diversity is not final-response quality.

## 9. Evidence and promotion

Split by task family and source domain. Tune only on development data. Keep source-diverse held-out calibration and protected-final sets. Viewing protected results after a change requires a new protected set.

Treat task × model as the independent unit. Pair conditions, report effect sizes and confidence intervals, cluster by task, correct multiple comparisons, and fail on missing coverage.

Promotion requires:

1. Predeclared primary effect with a confidence interval excluding no effect.
2. Protected-task replication across at least two generator families.
3. Predeclared diversity support.
4. Human judgment not contradicting model judges, with concordance reported.
5. No guardrail regression beyond predeclared margins.
6. Cost and latency below the approved operational ceiling; no token budget is imposed on the low-cost worker fleet, but runtime call/token/time bounds remain mandatory.
7. At least 2,000 provenance-backed protected responses with cells powered from pilot variance.
8. Independent scientific, engineering, and product approval.

Pseudo-labels and unlabeled crawls are not improvement evidence. Failed methods remain experimental, are revised on development data, or are removed.

## 10. Privacy and failure boundaries

- Private memory sources have explicit remote-egress policy.
- Runtime and evaluation storage are separate; raw evaluation artifacts remain protected and local.
- Invalid output discards only its branch.
- Selector failure returns an explicitly unjudged deterministic subset.
- Exhaustion returns `partial`, never a claimed complete run.
- No API keys enter source, prompts, logs, or public reports.
- Public reports contain aggregates and approved examples only.

## 11. Non-goals for initial implementation

No always-on cognition layer, autonomous background delivery, model-weight training, single composite creativity score, dashboard mutation API, sixel/kitty dependency, or public release without separate approval.
