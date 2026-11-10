# 50 ideas, straight vs with a state in the middle

Two briefs x 2 seed x 4 conditions, model `anthropic/claude-opus-5.5`. In the state conditions the model holds the brief, answers a state turn, then returns to write the list.

All columns are deterministic - same text, same number, no judge.

| condition | ideas / 50 | distinctiveness | mean pairwise | perplexity | TTR | MTLD | dist-2 | state turn (words) |
|---|---|---|---|---|---|---|---|---|
| straight | 50.0 | 0.2678 | 0.7258 | None | None | None | None | 0.0 |
| walk | 51.75 | 0.3127 | 0.7537 | None | None | None | None | 74.75 |
| daydream | 50.0 | 0.3315 | 0.7263 | None | None | None | None | 74.0 |
| doomscroll | 50.5 | 0.2958 | 0.75 | None | None | None | None | 72.0 |

Perplexity is Qwen3-0.6B over the list, lower = more predictable text. Distinctiveness is distance from the other conditions' ideas on the same brief. Neither measures quality; see math.md for the paired deltas and their intervals.
