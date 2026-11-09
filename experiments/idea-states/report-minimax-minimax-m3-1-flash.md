# 50 ideas, straight vs with a state in the middle

Two briefs × 2 seed × 4 conditions, model `minimax/minimax-m3.1-flash`. In the state conditions the model holds the brief, answers a state turn, then returns to write the list.

| condition | ideas / 50 | mean pairwise | distinctiveness | novelty | usefulness | state turn (words) |
|---|---|---|---|---|---|---|
| straight | 50.0 | 0.704 | 0.36 | 2.963 | 3.737 | 0.0 |
| walk | 46.25 | 0.7 | 0.366 | 2.95 | 3.552 | 34.75 |
| daydream | 50.333 (1/4 failed) | 0.697 | 0.362 | 2.953 | 3.707 | 94.667 |
| doomscroll | 63.5 | 0.73 | 0.402 | 3.143 | 3.502 | 355.5 |

Novelty and usefulness are a blind six-idea sample per cell, two judges that are not the model under test. Truncated cells make the idea count unreliable; the share is reported in the JSON.
