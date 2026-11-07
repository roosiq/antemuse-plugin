# The subtractive walk, tested properly — and why the first positive result was fake

Human incubation: attempt, leave, return, the fixation has decayed. So the walk
goes in the gap, not during the work.

**Design.** One session per pair. `Give me 5 unusual uses for a brick.` → a
3-minute walk (or nothing) → `Now give me 10 more, different from those five.`
Two measures: WordNet categories spanned by the second list, and how many of its
ideas reuse a noun from the first.

## Result, n = 32 pairs per condition

| | categories (raw) | words per list | categories per 100 words | reuse of prior ideas |
|---|---|---|---|---|
| **with a walk** | **16.38** | 162 | 10.1 | 131/320 (41%) |
| without | 14.41 | 119 | **12.1** | 103/320 (32%) |

Raw: **+1.44 categories**, 95% CI [+0.04, +2.83], one-sided permutation
**p = 0.027**. On the pre-declared metric that is a significant result.

## Why it is not one

The walk arm's second list is **+43 words longer** (162 vs 119). Category count
rises with length — 0.043 categories per word — so most of the "gain" is
verbosity. Regressing length out:

| | length-adjusted categories |
|---|---|
| with a walk | 15.47 |
| without | 15.32 |

**Difference +0.15 categories, 95% CI [−0.70, +1.00], p = 0.365.** Nothing.

Density tells the same story in reverse: 10.1 distinct domains per 100 words with
the walk against 12.1 without. The walk makes the answer **longer**, not broader.

## What is actually established

- **A real, reproducible side effect:** the "take a different first step"
  instruction produces ~36% more words. If the goal were a more expansive answer,
  that would be the finding.
- **No creativity effect:** four configurations (six seeded hops, fast wander,
  fast outer, subtractive-plus-restart), raw effects that vanish under length
  control or were never positive, and uptake of injected material at 1 of 36
  before the feed was removed altogether.

## The lesson worth keeping

The p = 0.027 was sitting in a metric that a length confound could manufacture
entirely. Any future run of this test must report words per answer alongside
categories, and test the length-adjusted difference, not the raw one.
