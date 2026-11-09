# Idea burst — 50 ideas, with and without material

Two briefs × 2 seeds × 3 conditions, model `openai/gpt-6.1-terra`. Each cell is one call returning a numbered list of 50 ideas.

| condition | ideas | mean pairwise | distinctiveness | novelty | usefulness | truncated |
|---|---|---|---|---|---|---|
| A — baseline | 50.0 | 0.722 | 0.299 | 2.697 | 3.865 | 0.0 |
| B — placebo | 50.0 | 0.729 | 0.326 | 3.013 | 3.598 | 0.0 |
| D — antemuse material | 50.0 | 0.735 | 0.324 | 2.743 | 3.825 | 0.0 |

Ideas = number parsed out of the 50 asked for; truncated = share of cells that fell short or ended mid-sentence, which invalidates the quantity comparison for those cells. Distinctiveness = mean distance to the nearest idea from the other conditions on the same brief. Judged axes are a blind sample of six ideas per cell, two judges, neither the model under test.
