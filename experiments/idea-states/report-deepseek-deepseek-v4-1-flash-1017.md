# 50 ideas, straight vs with a state in the middle

Two briefs x 2 seed x 4 conditions, model `deepseek/deepseek-v4.1-flash-1017`. In the state conditions the model holds the brief, answers a state turn, then returns to write the list.

All columns are deterministic - same text, same number, no judge.

| condition | ideas / 50 | distinctiveness | mean pairwise | perplexity | TTR | MTLD | dist-2 | state turn (words) |
|---|---|---|---|---|---|---|---|---|
| straight | 50.0 | 0.2838 | 0.7083 | 361.725 | 0.51 | 137.15 | 0.899 | 0.0 |
| walk | 50.0 | 0.291 | 0.7152 | 471.225 | 0.5108 | 145.45 | 0.9205 | 16.75 |
| daydream | 50.0 | 0.3912 | 0.6318 | 637.1 | 0.4193 | 111.275 | 0.8427 | 55.75 |
| doomscroll | 63.25 | 0.3822 | 0.7553 | 342.225 | 0.478 | 124.875 | 0.8928 | 34.0 |

Perplexity is Qwen3-0.6B over the list, lower = more predictable text. Distinctiveness is distance from the other conditions' ideas on the same brief. Neither measures quality; see math.md for the paired deltas and their intervals.
