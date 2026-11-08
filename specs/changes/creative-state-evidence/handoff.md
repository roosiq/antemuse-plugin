# Antemuse creative-state-evidence — execution handoff

You are the next implementation controller for Antemuse. Continue from the current repository state. Waves 1–2 are complete; do not restart their design or reimplement their libraries.

## 1. Repository state

- Repo: `/home/ryan/antemuse`
- Plugin: `/home/ryan/antemuse/plugin`
- Branch: `corporateslop-llm-reader-burden-model`
- HEAD: `0c80c2e` (`feat(scripts): measured harvest feasibility probe for the task bank`)
- Current Antemuse work is uncommitted. Nothing was pushed.
- The parent worktree contains unrelated site/scorer changes. Preserve them. In particular, `plugin/specs/changes/state-evidence-task-bank/spec.md` is separately modified and is not part of this Wave 2 change.

Relevant existing commits:

- `b716789` — offline A–C baselines, cache, metrics, judges, statistics, and reports.
- `faadb91` — six-artifact Collider bank, bounded auxiliary LLM adapter, and operational projections.
- `46dde3f` — creative-state-evidence spec, plan, and task register.
- `6642d8b` — business/operator documentation alignment.
- `5e41067` and `0c80c2e` — separate state-evidence task-bank proposal and harvest feasibility probe.

## 2. Accepted work

Gate 0 is approved. Ryan approved `spec.md`, `plan.md`, and `tasks.md` on 2026-11-07. That approval authorizes the bounded exploration library; it does not authorize default-on methods, creative-quality claims, or protected-evaluation promotion.

Wave 1 is complete and integrated:

| Lane | Delivered |
|---|---|
| A | Baseline A/B/C runner, immutable records, condition-aware cache, deterministic replay, and development fixtures |
| B | Semantic/structural metrics, blind judge projection, exact-rational sign test, cluster statistics, and fail-closed coverage |
| C | Six real Open Collider artifacts and seeded fresh/deepen/refresh selection |
| D | Bounded host-injected `ctx.llm` adapter with schemas, timeouts, failures, and usage |
| E | Deterministic surface-safe operational projections |

Wave 2 is complete and integrated:

| Lane | Delivered |
|---|---|
| F | Deterministic collision planning, source ablation, and collided/insights-without-collision channels |
| G | Independent structured branches, per-branch instructions, seeded source assignment, budget-skipped branches, and actual usage/cost accounting |
| H | Deterministic cleanup, optional selection-only judging, `love`/`like`/`trash`, deepen, and refresh |
| I | BR-15, BR-1…BR-15 traceability, revised operating requirements, and explicit library-only README/SKILL guidance |

C3 is resolved. The pinned upstream content is CC BY 4.0. All six Collider artifacts carry `license=CC-BY-4.0`, `license_url`, and upstream credit. `data/collider/ATTRIBUTION.md` and `data/collider/licensing/upstream-license.json` preserve the attribution and licensing evidence. Generated examples remain unverified scientific material.

The final independent integration review returned:

```json
{"verdict":"APPROVED","critical":[],"important":[],"minor":[]}
```

## 3. Verification evidence

Run from `/home/ryan/antemuse/plugin`:

```bash
env -u PYTHONPATH NLTK_DATA=/home/ryan/nltk_data \
  ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with pillow --with nltk --quiet pytest tests/ -q
```

Final results after the integration-review repairs:

```text
Focused collision/orchestrator/adapter suite: 89 passed in 0.79s
Full unrestricted suite: 563 passed, 1 failed in 7.49s
Full suite with FLAKE-1 deselected: 563 passed, 1 deselected in 6.17s
```

The unrestricted failure is the already-documented stochastic case:

```text
tests/test_walks.py::test_outer_hops_are_farther_than_wander_hops
```

FLAKE-1 is recorded in `tasks.md`. It predates the final Wave 2 repairs and is not fixed here. Do not describe the current unrestricted suite as green, and do not claim one green run proves stability.

Plugin doctor passed after integration:

```text
antemuse 0.9.0 (standalone)
runtime discovery, manifest parsing, import, and registration passed
1 tool, 4 hooks
```

Structural documentation checks passed:

- BR-1…BR-15 each have exactly one BRD definition and one traceability row.
- The original 39-message BRD appendix is byte-identical to HEAD.
- Referenced experimental spec/module paths exist.
- Revised operating docs contain no stale 107-test or blanket no-model/no-scoring claim.
- `git diff --check` passed.

## 4. Current runtime boundary

The four-state runtime remains unchanged. These library modules exist but are not registered or wired into runtime:

```text
evaluation/
core/collider.py
core/collision.py
core/llm.py
core/orchestrator.py
core/selection.py
core/feedback.py
core/presenter.py
data/collider/
```

There is no `/spark` command, feedback command, auxiliary hook, experimental runtime flag, or prepared-artifact runtime injection yet.

No changes were made to:

```text
plugin/__init__.py
plugin/plugin.yaml
plugin/core/engine.py
plugin/core/sources.py
plugin/core/storage.py
plugin/core/surfaces.py
plugin/core/tui.py
```

Non-negotiables:

- Entry, exit, expiry, rendering, tool restoration, and `/return` never require inference.
- Auxiliary exploration is opt-in and disabled by default.
- Runtime selection scores are selection aids, not evidence of improvement.
- No method is promoted without the protected comparative evidence in `spec.md`.
- No autonomous background delivery or always-on cognition layer.
- No fabricated sources, scores, usage, tests, adoption, pricing, or evaluation evidence.
- No chain-of-thought exposure.
- No commits or pushes without Ryan's explicit authorization.
- Do not modify unrelated parent-repo or site/scorer files.

## 5. Next work: Wave 3 only

The next implementation lane is a single integration worker, not another parallel library fleet. Tasks J1–J4 remain unchecked in `tasks.md`.

Owned runtime scope:

```text
plugin/__init__.py
plugin/core/engine.py
plugin/core/sources.py
plugin/core/storage.py
plugin/core/surfaces.py
plugin/core/tui.py
plugin/plugin.yaml
integration/origin/manifest tests
plugin/docs/spec.md
```

Required work:

1. Register auxiliary tasks and lifecycle hooks with explicit experimental controls.
2. Add optional method/budget/seed fields without changing existing defaults or the `state` escape hatch.
3. Wire the accepted collision, orchestration, selection, feedback, and presentation modules.
4. Add `/spark` and feedback commands only through the approved runtime path.
5. Preserve origin binding, session cleanup, tool restoration, expiry, `/return`, and current four-state behavior.
6. Reconcile `docs/spec.md` with the approved two-layer contract without weakening §18's protected invariants.
7. Add failing integration/origin/manifest tests before runtime wiring, then run focused and full suites.
8. Obtain independent specification and code-quality review before marking J1–J4 complete.

Wave 3 implementation is not evidence that creativity improved. Waves 4–5 still require immutable A–F shards, complete deterministic aggregation, runtime/Hermes/surface/evaluation QA, development-only tuning, and a frozen protected-final evidence bundle.

## 6. Token-efficient worker workflow

Use direct, evidence-scoped DeepSeek calls rather than full Hermes agent loops.

Verified route:

- Provider: Nous Portal through the verified local OpenAI-compatible proxy.
- Model: `deepseek/deepseek-v4.1-flash-1017`.
- Reasoning: `reasoning_effort=none`.
- Do not silently substitute another worker model.

Reusable driver:

```text
/home/ryan/antemuse/plugin/tools/direct_fleet.py
```

Invocation:

```bash
python3 /home/ryan/antemuse/plugin/tools/direct_fleet.py \
  TASK_FILE OUTPUT_FILE [CONTEXT_FILE ...] [--json] [--max-tokens N]
```

For each bounded task:

1. Supply goal, non-goals, exclusive owned files, acceptance criteria, and exact test commands.
2. Provide only the necessary files or focused diff.
3. Validate returned file scopes before materializing anything.
4. Run focused tests in the controller, then independent specification and quality reviews.
5. Repair only original-contract violations or demonstrated correctness/security defects.
6. Integrate only after both reviews and controller verification pass.
7. Use deterministic tools for mechanical edits, hashing, JSON validation, tests, and aggregation.

## 7. Artifacts and audit trail

Authoritative artifacts:

```text
/home/ryan/antemuse/plugin/specs/changes/creative-state-evidence/spec.md
/home/ryan/antemuse/plugin/specs/changes/creative-state-evidence/plan.md
/home/ryan/antemuse/plugin/specs/changes/creative-state-evidence/tasks.md
/home/ryan/antemuse/plugin/docs/brd.md
/home/ryan/antemuse/plugin/docs/requirements.md
/home/ryan/antemuse/plugin/docs/spec.md
```

Direct-call driver:

```text
/home/ryan/antemuse/plugin/tools/direct_fleet.py
```

Scratch worktrees, prompts, review responses, and usage metadata:

```text
/home/ryan/.hermes/cache/scratch/antemuse-fleet/
```

Scratch is pruned after inactivity. The repo task register and accepted files are the durable source of truth.
