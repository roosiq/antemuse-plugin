# The subtractive walk, tested the way the literature tests it

Human incubation works like this: attempt the problem, leave it, come back, and
the fixation has decayed. So the test has three beats, and the walk sits in the
gap rather than during the work.

**Design.** Same model, one session per row.
1. `Give me 5 unusual uses for a brick.` — establish the fixation.
2. A 3-minute walk (walk condition) or nothing (idle condition).
3. `Now give me 6 more uses for a brick, different from those five.`

Two measures: how many WordNet categories the second attempt spans, and how many
of its ideas reuse a noun from the first attempt.

## Result, n = 8 pairs per condition

| | first attempt | second attempt | gain | reused prior ideas |
|---|---|---|---|---|
| **with a walk** | 7.5 categories | **13.4** | **+5.9** (range +2…+9) | **19/48 (40%)** |
| without | 6.8 | 11.2 | +4.5 (range 0…+7) | 26/48 (54%) |

Walk gains `[2, 3, 4, 6, 7, 8, 8, 9]`, idle gains `[0, 2, 4, 5, 5, 6, 7, 7]`.
Permutation test on the difference of the gains: **one-sided p = 0.17**.

## What this is and is not

This is the **first configuration in the whole exercise with a positive
direction** — both measures lean the same way, and it is the only design where the
walk matches the mechanism it claims (subtract the frame, return, re-approach).

It is **not** evidence yet. p = 0.17 at n = 8; the proxy is WordNet categories in
a short list, which rewards breadth and not quality; and the second attempt gains
categories in both conditions simply because "different from those five" pushes
away from the first answer. The between-condition difference is the only part
that means anything, and it is +1.4 categories.

To settle it at this effect size: roughly **30 pairs per condition**, about 60
turns (two model calls per pair). That is a fresh session's budget, not this one's.

## Design consequence

Everything before this measured the walk *adding* material during the work, and
every one of those runs was null or slightly negative (11.4→9.4, 11.1→9.9,
12.3→10.7 categories; uptake 1 of 36 hops). The one version that does the opposite
of what those did — take material away, then force a different first step — is
the one that moved in the right direction.
