# Preregistration — Antemuse state settings experiment

Committed **before the first session**. Governing spec:
`specs/changes/state-settings-experiment/spec.md`. If this file and the spec disagree,
the spec governs the design and this file governs the numbers.

Status: **preregistered, no sessions run.** Ledger: `experiments/state-settings/ledger.jsonl`
(empty until the first run).

## Hypotheses, per state

- **H1** — the state's primary outcome rate is higher under `default` dose than under the
  no-state `control` arm.
- **H2** — the outcome is dose-sensitive: `double` > `default` beyond the margin, or
  `half` is equivalent to `default` within the margin (0.10 absolute).

Stated direction is one-tailed for H1 in prose, tested two-sided at α = 0.05 with the
interval reported, because a negative effect is a finding worth publishing (it would say
the state costs turns and buys nothing).

## Arms and doses

| state | half | default | double | ceiling (all arms) |
|---|---|---|---|---|
| `walk` | 3 turns | 6 turns | 12 turns | 3 min (6 min for double) |
| `daydream` | 1 pair | 2 pairs | 4 pairs | 3 min (6) |
| `doomscroll` | 1 item | 3 items | 6 items | 8 min (16) |
| `dream` | 1 recombination | 2 | 4 | 30 min (60) |
| `unstuck` | 0 directions ≠ a state | 1 direction | 2 directions | 5 min (10) |

`unstuck`'s half arm is not a state: a direction is the state. Its `half` arm is
**dropped**, leaving three arms (default, double, control) and 160 entries per arm for
that state only.

`control` never enters a state. Its material is generated and logged with the same
seeding mix and discarded unshown, so the control's cost is comparable to the arms'.

## Block seeds

Each state draws its block permutation from a seed derived deterministically from
`antemuse-state-settings-2026-11-08:<state>` — the SHA-256 prefixes are recorded here so
the assignment can be reproduced without trusting a machine's PRNG state:

| state | block seed | sha256 prefix |
|---|---|---|
| `walk` | 3497679622 | `d07a5b069d73cdda` |
| `daydream` | 18095054 | `01141bce921c517d` |
| `doomscroll` | 751586276 | `2ccc4be4e93cef39` |
| `dream` | 3399968528 | `caa767100e9c04c0` |
| `unstuck` | 1739374009 | `67acbdb9acd7cf0e` |

Blocks are 8 entries: two per arm, `random.Random(seed).shuffle` of the arm list, then
consecutive 8s. A block's seed and permutation are written to the ledger on every entry.

## Crossed settings

Held fixed per block, alternated between blocks: `recommend_cooling_minutes` ∈ {45, 120},
`long_stretch_minutes` ∈ {0 (measured), 90}. A block records which pair it used.

## Primary outcome definitions (frozen)

A primary outcome is a boolean computed by `tools/experiment_outcome.py` from material the
plugin already logs, within the stated window. No human or model judgement enters the
primary outcome; ambiguity at the edge is handled by the two-coder check described in the
spec (κ reported, exploratory only).

| state | outcome | window |
|---|---|---|
| `walk` | the seeded term or its WordNet hypernym/hyponym appears in the next 6 turns' text or file diffs | 6 turns |
| `daydream` | a delivered pair appears together in one later turn's output | 4 turns |
| `doomscroll` | a delivered URL or domain is fetched, cited, or acted on | 6 turns |
| `dream` | a recombination is kept (`state(action="keep")`) or the compound appears in a spec/doc | 2 sessions |
| `unstuck` | a spec or plan written whose subject matches the recommended direction | 2 sessions |

## Exclusions (fixed)

1. Sessions where the user typed the state command by hand (not block-assigned).
2. Entries whose dose was not delivered as declared (provider failure), kept in the ledger
   but excluded from the primary analysis, reported in the same table.
3. Truncated answers: `finish_reason` not `stop`, or `truncated: true`.
4. Control entries with any state entry in the preceding 24 hours.
5. Blocks abandoned for platform failure — the block is reported, not dropped.

## Stopping rule

A state's arm stops at 160 entries, or when the declared per-state budget cap is reached,
or when the user ends the run — whichever first. No peeking: the repository's analysis
script runs once per state after its final entry, and its output is committed unedited.
An interim look is allowed only for the safety question "is this costing budget with no
signal", and if taken it is disclosed alongside the result.

## Decision rule (unchanged from the spec, restated so it is in one place)

| observation | action |
|---|---|
| H1 holds, `half` ≈ `default` | half-dose becomes the default; ceiling unchanged |
| H1 holds, `default` ≈ `double` | default stays |
| H1 holds, `double` > `default` beyond margin | double becomes the default |
| H1 fails | ship the default and **say in the docs that no measurable result was found** |
| negative effect | propose disabling the state |

## Amendments

### 2026-11-08 — outcome coding fixed before any kept outcome existed (not exploratory)

`carry` first took the longest word of each delivered line, which made "Japanese" the
subject of a line about a lilac and would have scored a walk as carried only when the
adjective reappeared. Fixed to take the head word of each arrow-headed segment and to
ignore a small set of structural words ("system", "list", …). Nine tests pin the
behaviour.

Three entries were produced while the earlier code was live. None of their outcomes is
kept: all three are excluded with `outcome-definition-changed`. **The fix happened before
any kept outcome existed**, which is the only reason it does not void the state.

### 2026-11-08 — state ceilings doubled for every arm (not exploratory)

Measured in the first block: one real `hermes chat` turn costs ~40–70 s, so `walk`'s
3-minute ceiling truncated a 6-turn dose at 3 turns (`expired before its dose: 3 of 6`).
The ceiling is a **safety limit, not the treatment**; the treatment is the dose. An entry
truncated by its ceiling measures the ceiling, not the dose, so the run would have
collected nothing about the thing it is about.

Amendment: every arm runs with the state's ceiling at **2× its default** for the duration
of this experiment. The ledger records the ceiling actually used, so no reader has to
trust this paragraph. Entries collected before the amendment that were truncated by the
old ceiling are excluded with `dose-not-delivered`.

This does not touch a hypothesis, an outcome definition, or an exclusion, so it is not
marked exploratory — but it is a change to how an arm runs, and it is written down here
rather than fixed silently.

### 2026-11-08 — the ceiling finding itself belongs in the product record

`walk`'s 3-minute ceiling cannot contain a 6-turn dose at real turn latency. Either the
dose falls to ~3 turns or the ceiling becomes ~8 minutes; that decision waits for the
experiment, and is recorded here because it was found by running, not by reading.

---

## v2 — the primary outcome is deterministic (2026-11-08)

The model lane was preregistered first and priced second. One six-turn entry measured
~4.0 M input tokens; the 60-per-arm floor for a single state is ~150 M. The lane is kept
for cost and plausibility, and **its outcomes are exploratory**.

The primary analysis is now `tools/experiment_deterministic.py`: the state's own provider,
the poles of each delivered line, and three counts — `novel` against this repository's
6,011-word vocabulary, `fresh` within a dose, and `distinct lines` across trials. Fifteen
cells, 150 trials each, seconds, zero model calls.

Frozen in this revision, before the deciding run:

- **Margin:** a dose may not exceed the smallest k where `fresh < 0.85`.
- **Source defect:** `distinct lines < 0.30` — a frozen source is not a dose finding.
- **Generator defect:** `novel < 0.20` with `distinct = 1.00` — a template is not invention.
- **Reproduction:** no dose changes until 150 trials/cell reproduce in a clean tree, by
  someone who did not write the tool.

Exploratory findings from the first pass (not decisions): walk's freshness falls from 87 %
at dose 3 to 78 % at 12; doomscroll's variety falls to 11 % distinct lines at dose 6 because
its feed is frozen; dream is structurally varied and lexically boilerplate; `unstuck` serves
five lines at any dose and says the same thing every session, so its dose is meaningless
until its direction source is real.
