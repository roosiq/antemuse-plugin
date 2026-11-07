# Creative state evidence — execution plan

## Controller and worker route

The controller owns contracts, task DAG, shared files, integration, and final evidence. Implementation uses fresh DeepSeek workers with independent review. Every editing worker gets an isolated worktree and exclusive file set. No commits or pushes without Ryan's explicit instruction.

Verified worker route: Nous Portal through `http://127.0.0.1:8645/v1`, model `deepseek/deepseek-v4.1-flash-1017`, `reasoning_effort=none`. Direct `hermes chat --provider nous` failed `invalid_params`; the OpenAI-compatible proxy route returned `ROUTE_OK` from the requested model.

## Efficiency supervision

Measure verified accepted work per dollar and elapsed hour. Track first-pass specification acceptance, independent test confirmation, review cycles, tokens/cost/wall time per accepted task, retries, scope violations, duplicate work, and evaluation coverage.

Use deterministic tools for mechanical work. One focused repair cycle is allowed before a fresh narrower task or escalation. Rate limits back off; deterministic contract failures stop the lane. Self-reported success is not completion evidence.

## Wave 0: contracts

Create and approve the spec, public interfaces, event/result schemas, experimental conditions, file ownership, and promotion rules. Two canaries validate worker suitability without runtime activation.

## Wave 1: disjoint lanes

- A Evaluation runner: `evaluation/run.py`, `evaluation/cache.py`, `evaluation/tasks/`, focused tests.
- B Metrics/statistics: `evaluation/metrics.py`, `judges.py`, `statistics.py`, `report.py`, focused tests.
- C Collider bank: `core/collider.py`, `data/collider/`, `tests/test_collider.py`.
- D Hermes LLM adapter: `core/llm.py`, `tests/test_llm.py`.
- E Operational projections: `core/presenter.py`, `tests/test_presenter.py`.

A–C baselines run before runtime integration. B uses known-effect synthetic fixtures. C validates provenance and seeded source selection. D uses fake-host tests before any approved live call. E deterministically excludes private reasoning.

Each task receives specification-compliance review followed by code-quality review. Shared files remain untouched.

## Wave 2: dependent lanes

- F deterministic collision, after C: `core/collision.py`, `tests/test_collision.py`.
- G branch orchestration, after C/D: `core/orchestrator.py`, `tests/test_orchestrator.py`.
- H selection/feedback, after B/C contracts: `core/selection.py`, `core/feedback.py`, focused tests.
- I documentation, after Gate 0: BRD, operating requirements, README, SKILL, traceability.

F needs no inference. G fans out only through D. H's scores are selection aids only.

## Wave 3: single integration lane

Only one worker touches `__init__.py`, `core/engine.py`, `core/sources.py`, `core/storage.py`, `core/surfaces.py`, `core/tui.py`, `plugin.yaml`, integration/origin/manifest tests, and `docs/spec.md`.

Register auxiliary tasks and lifecycle hooks; add optional method/budget/seed fields; wire modules; add `/spark` and feedback; preserve existing defaults, `/return`, tool exemption, expiry, and origin binding; run the full suite.

## Wave 4: evaluation and QA

Run immutable task/model shards into independent result directories. Aggregate deterministically and fail on missing cells. In parallel, review runtime, Hermes integration, surfaces, and evaluation validity.

## Wave 5: pilot and protected final

Freeze development configuration; run A–F; estimate variance; tune only development data. Then freeze tasks, code, prompts, sources, thresholds, and analysis for protected-final evaluation. Scientific, engineering, and product reviews are independent. Ryan decides promote/revise/reject per method.

## Integration rule

Parallelize by artifact and immutable shard. Contract changes never originate independently inside a lane. No two workers edit the same file or result artifact.
