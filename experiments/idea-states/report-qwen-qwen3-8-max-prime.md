# 50 ideas, straight vs with a state in the middle

Two briefs × 2 seed × 4 conditions, model `qwen/qwen3.8-max-prime`. In the state conditions the model holds the brief, answers a state turn, then returns to write the list.

| condition | ideas / 50 | mean pairwise | distinctiveness | novelty | usefulness | state turn (words) |
|---|---|---|---|---|---|---|
| straight | 43.25 | 0.684 | 0.316 | 2.737 | 3.74 | 0.0 |
| walk | None (4/4 failed) | None | None | None | None | None |
| daydream | 50.0 (1/4 failed) | 0.651 | 0.334 | 2.81 | 3.763 | 54.0 |
| doomscroll | 50.0 | 0.639 | 0.328 | 3.112 | 3.655 | 219.5 |

Novelty and usefulness are a blind six-idea sample per cell, two judges that are not the model under test. Truncated cells make the idea count unreliable; the share is reported in the JSON.
