# 50 ideas, straight vs with a state in the middle

Two briefs × 2 seed × 4 conditions, model `deepseek/deepseek-v4.1-flash-1017`. In the state conditions the model holds the brief, answers a state turn, then returns to write the list.

| condition | ideas / 50 | mean pairwise | distinctiveness | novelty | usefulness | state turn (words) |
|---|---|---|---|---|---|---|
| straight | 50.0 | 0.708 | 0.284 | 2.873 | 3.97 | 0.0 |
| walk | 50.0 | 0.715 | 0.291 | 3.212 | 3.697 | 16.75 |
| daydream | 50.0 | 0.632 | 0.391 | 3.13 | 3.485 | 55.75 |
| doomscroll | 63.25 | 0.755 | 0.382 | 2.96 | 3.41 | 34.0 |

Novelty and usefulness are a blind six-idea sample per cell, two judges that are not the model under test. Truncated cells make the idea count unreliable; the share is reported in the JSON.
