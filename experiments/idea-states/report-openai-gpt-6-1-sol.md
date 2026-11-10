# 50 ideas, straight vs with a state in the middle

Two briefs x 2 seed x 4 conditions, model `openai/gpt-6.1-sol`. In the state conditions the model holds the brief, answers a state turn, then returns to write the list.

All columns are deterministic - same text, same number, no judge.

| condition | ideas / 50 | distinctiveness | mean pairwise | perplexity | TTR | MTLD | dist-2 | state turn (words) |
|---|---|---|---|---|---|---|---|---|
| straight | 50.0 | 0.2625 | 0.724 | None | None | None | None | 0.0 |
| walk | 50.0 | 0.2778 | 0.6985 | None | None | None | None | 27.75 |
| daydream | 50.0 | 0.291 | 0.7057 | None | None | None | None | 49.0 |
| doomscroll | 50.0 | 0.279 | 0.714 | None | None | None | None | 49.25 |

Perplexity is Qwen3-0.6B over the list, lower = more predictable text. Distinctiveness is distance from the other conditions' ideas on the same brief. Neither measures quality; see math.md for the paired deltas and their intervals.
