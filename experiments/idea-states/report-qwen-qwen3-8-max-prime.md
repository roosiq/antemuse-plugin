# 50 ideas, straight vs with a state in the middle

Two briefs x 2 seed x 4 conditions, model `qwen/qwen3.8-max-prime`. In the state conditions the model holds the brief, answers a state turn, then returns to write the list.

All columns are deterministic - same text, same number, no judge.

| condition | ideas / 50 | distinctiveness | mean pairwise | perplexity | TTR | MTLD | dist-2 | state turn (words) |
|---|---|---|---|---|---|---|---|---|
| straight | 43.25 | 0.316 | 0.6835 | None | None | None | None | 0.0 |
| walk | None (4/4 failed) | None | None | None | None | None | None | None |
| daydream | 50.0 (1/4 failed) | 0.3343 | 0.651 | None | None | None | None | 54.0 |
| doomscroll | 50.0 | 0.3278 | 0.6388 | None | None | None | None | 219.5 |

Perplexity is Qwen3-0.6B over the list, lower = more predictable text. Distinctiveness is distance from the other conditions' ideas on the same brief. Neither measures quality; see math.md for the paired deltas and their intervals.
