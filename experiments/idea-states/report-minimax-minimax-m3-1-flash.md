# 50 ideas, straight vs with a state in the middle

Two briefs x 2 seed x 4 conditions, model `minimax/minimax-m3.1-flash`. In the state conditions the model holds the brief, answers a state turn, then returns to write the list.

All columns are deterministic - same text, same number, no judge.

| condition | ideas / 50 | distinctiveness | mean pairwise | perplexity | TTR | MTLD | dist-2 | state turn (words) |
|---|---|---|---|---|---|---|---|---|
| straight | 50.0 | 0.36 | 0.7038 | None | None | None | None | 0.0 |
| walk | 46.25 | 0.3665 | 0.6998 | None | None | None | None | 34.75 |
| daydream | 50.3333 (1/4 failed) | 0.3623 | 0.697 | None | None | None | None | 94.6667 |
| doomscroll | 63.5 | 0.4025 | 0.7298 | None | None | None | None | 355.5 |

Perplexity is Qwen3-0.6B over the list, lower = more predictable text. Distinctiveness is distance from the other conditions' ideas on the same brief. Neither measures quality; see math.md for the paired deltas and their intervals.
