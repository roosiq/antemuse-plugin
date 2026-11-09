# Idea burst — 50 ideas, with and without material

Two briefs × 2 seeds × 3 conditions, model `qwen/qwen3.8-max-prime`. Each cell is one call returning a numbered list of 50 ideas.

| condition | ideas | mean pairwise | distinctiveness | novelty | usefulness | truncated |
|---|---|---|---|---|---|---|
| A — baseline | 50.0 | 0.657 | 0.328 | 2.683 | 3.85 | 0.0 |
| B — placebo | 38.25 | 0.694 | 0.363 | 3.4 | 3.558 | 0.25 |
| D — antemuse material | 23.5 | 0.651 | 0.315 | 2.913 | 3.77 | 0.75 |

Ideas = number parsed out of the 50 asked for; truncated = share of cells that fell short or ended mid-sentence, which invalidates the quantity comparison for those cells. Distinctiveness = mean distance to the nearest idea from the other conditions on the same brief. Judged axes are a blind sample of six ideas per cell, two judges, neither the model under test.
