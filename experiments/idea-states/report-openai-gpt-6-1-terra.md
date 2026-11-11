# 50 ideas, straight vs with a state in the middle

Two briefs x 1 seed x 4 conditions, model `openai/gpt-6.1-terra`. In the state conditions the model holds the brief, answers a state turn, then returns to write the list.

All columns are deterministic - same text, same number, no judge.

| condition | ideas / 50 | distinctiveness | mean pairwise | perplexity | TTR | MTLD | dist-2 | state turn (words) |
|---|---|---|---|---|---|---|---|---|
| straight | 50.0 | 0.3185 | 0.7375 | None | None | None | None | 0.0 |
| walk | 50.0 | 0.3375 | 0.737 | None | None | None | None | 0.0 |
| daydream | 50.0 | 0.3585 | 0.725 | None | None | None | None | 0.0 |
| doomscroll | 50.0 | 0.345 | 0.732 | None | None | None | None | 0.0 |

Perplexity is Qwen3-0.6B over the list, lower = more predictable text. Distinctiveness is distance from the other conditions' ideas on the same brief. Neither measures quality; see math.md for the paired deltas and their intervals.
