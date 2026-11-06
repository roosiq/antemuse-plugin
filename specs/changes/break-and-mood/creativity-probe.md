# Probing for a sweet spot: dose and direction

Question: does the walk help ideation, and if so at what dose? Two Cheap
Alternate-Uses runs, same model, WordNet over the nouns each answer uses.

## 1. Dose sweep (n = 1 per cell, exploratory)

Four doses of real WordNet hops injected into the turn (0, 1, 3, 6), two prompts.

| dose | brick: categories / similarity | paperclip: categories / similarity | hops used |
|---|---|---|---|
| 0 | 9 / 0.37 | 9 / 0.36 | 0 |
| 1 | 9 / 0.31 | 5 / 0.37 | 0 |
| 3 | 10 / 0.32 | 9 / 0.29 | 0 |
| 6 | 13 / 0.31 | 7 / 0.38 | 1 |

The brick column looks monotone, the paperclip column does not. n = 1, so this is
a shape worth testing, not a finding.

## 2. Paired repeat at the extremes (n = 5 pairs)

Idle vs six hops, same prompt, alternating within each pair.

| pair | categories idle→walk | similarity idle→walk | hops used |
|---|---|---|---|
| 0 | 10 → 12 | 0.28 → 0.31 | 0 |
| 1 | 13 → 7 | 0.28 → 0.36 | 0 |
| 2 | 14 → 8 | 0.27 → 0.36 | 0 |
| 3 | 11 → 11 | 0.30 → 0.36 | 1 |
| 4 | 9 → 9 | 0.29 → 0.35 | 0 |

Mean categories **11.4 idle vs 9.4 walking** (paired difference −2.0; walking won
1 of 5, tied 2, lost 2). Mean similarity **0.29 vs 0.35** — the walking answers
are *more* clustered, i.e. less divergent on this proxy.

The earlier single-run signal (walking wider: 12 vs 7 categories) did not
replicate. That is the point of running pairs: one run is a coin flip.

## What this says about a sweet spot

At these doses there is no curve to find. The effect is indistinguishable from
noise, and in the direction that exists it is slightly negative.

The sharper observation is uptake: **1 of 30 delivered hops appeared in any
answer.** The material is not being used at all, so dose cannot matter yet. The
directive currently permits ignoring it ("say nothing about it if it does not
[belong]"), which is honest but makes the state decorative for ideation.

Before tuning length or cadence, the dial worth testing is whether the step must
be engaged — e.g. "use one step or say why none fits" — and whether that raises
uptake without wrecking the answer. That is one variable, and it can be measured
with the same instrument.

## Standing limits

- Proxy measures word spread, not quality; an incoherent answer can score well.
- n = 5 pairs is enough to kill the n = 1 claim, not enough to establish the
  reverse.
- One model, one task shape, one session's budget.

## 3. Same test against the fast walk (3 min, 9 s, n = 4 pairs)

Natural delivery — no seeded steps, the walk itself supplies them — otherwise the
same prompt and the same instrument.

| pair | categories idle→walk | similarity idle→walk |
|---|---|---|
| 0 | 10 → 11 | 0.35 → 0.34 |
| 1 | 12 → 8 | 0.32 → 0.37 |
| 2 | 10 → 12 | 0.34 → 0.30 |
| 3 | 14 → 9 | 0.29 → 0.32 |

Mean categories **11.5 idle vs 10.0 walking** (paired −1.5, walk won 2 of 4);
similarity **0.323 vs 0.335**. Same direction as the 9-minute-cadence test, same
magnitude, same conclusion: indistinguishable from noise, if anything slightly
negative.

Delivery did work — three steps nine seconds apart inside a twenty-second window
(`partition→structure [hypernym] → structure→signboard [hyponym] → signboard→
sandwich board [hyponym]`). The first run of this test reported "0 steps
delivered"; that was a bug in the counter (it sliced a journal capped at 60
events), not in the walk.

**So the speed-up is free.** Ten times faster cadence and a tenth of the wall
clock changed nothing measurable, which is exactly what the earlier nulls
predicted. The expense of a walk is now a state entry, a few hundred characters
per turn, and three minutes — not half an hour.
