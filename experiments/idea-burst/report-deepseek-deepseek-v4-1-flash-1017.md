# Idea burst — 50 ideas, with and without material

Two briefs × 2 seeds × 3 conditions, model `deepseek/deepseek-v4.1-flash-1017`. Each cell is one call returning a numbered list of 50 ideas.

| condition | ideas | mean pairwise | distinctiveness | novelty | usefulness | truncated |
|---|---|---|---|---|---|---|
| A — baseline | 50.0 | 0.723 | 0.307 | 2.797 | 3.86 | 0.0 |
| B — placebo | 50.0 | 0.692 | 0.337 | 3.23 | 3.76 | 0.0 |
| D — antemuse material | 50.75 | 0.698 | 0.324 | 2.865 | 3.812 | 0.0 |

Ideas = number parsed out of the 50 asked for; truncated = share of cells that fell short or ended mid-sentence, which invalidates the quantity comparison for those cells. Distinctiveness = mean distance to the nearest idea from the other conditions on the same brief. Judged axes are a blind sample of six ideas per cell, two judges, neither the model under test.
