# Self-perplexity from the model's own logprobs

Model `openai/gpt-6.1-terra`, 1 seed × 2 briefs × 4 conditions. Per-token negative log-likelihood of the model's own output.

| condition | ideas | mean NLL/token | self-perplexity | sd across ideas |
|---|---|---|---|---|
| straight | None | None | None | None |
| walk | None | None | None | None |
| daydream | None | None | None | None |
| doomscroll | None | None | None | None |

Lower NLL means the model was more on rails. Not comparable across models; compare conditions within a model.
