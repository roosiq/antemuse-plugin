# Self-perplexity from the model's own logprobs

Model `deepseek/deepseek-v4.1-flash-1017`, 1 seed × 2 briefs × 4 conditions. Per-token negative log-likelihood of the model's own output.

| condition | ideas | mean NLL/token | self-perplexity | sd across ideas |
|---|---|---|---|---|
| straight | 50 | 0.264 | 1.3 | 0.287 |
| walk | 44 | 0.339 | 1.4 | 0.331 |
| daydream | 50 | 0.391 | 1.45 | 0.373 |
| doomscroll | 50 | 0.329 | 1.4 | 0.371 |

Lower NLL means the model was more on rails. Not comparable across models; compare conditions within a model.
