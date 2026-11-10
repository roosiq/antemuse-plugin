# Straight lists of 100 ideas, asked 4 times

No state. Two ideas count as the same at embedding similarity 0.80. 'Twin' = share of a list's ideas that reappear in the other list.

## Same model, asked again

| model | lists | twin ideas | avg best match | distinct in the pooled set |
|---|---|---|---|---|
| DeepSeek v4.1 | 4 | 14% | 0.68 | 339 of 400 (85%) |
| Qwen3.8 Max | 4 | 15% | 0.69 | 330 of 400 (82%) |
| MiniMax M3.1 | 4 | 6% | 0.66 | 372 of 400 (93%) |
| GPT-6.1 Terra | 4 | 20% | 0.70 | 315 of 400 (79%) |
| GPT-6.1 Sol | 4 | 25% | 0.72 | 299 of 400 (75%) |
| Opus 5.5 | 4 | 28% | 0.72 | 287 of 400 (72%) |

Average across models: **18% of ideas are twins when the same model is asked again**, best match 0.69.

## Different models, asked once each

| | DeepSeek  | Qwen3.8 M | MiniMax M | GPT-6.1 T | GPT-6.1 S | Opus 5.5 |
|---|---|---|---|---|---|---|
| **DeepSeek v4.1** | — | 11% | 5% | 9% | 8% | 9% |
| **Qwen3.8 Max** | 11% | — | 4% | 9% | 5% | 9% |
| **MiniMax M3.1** | 5% | 4% | — | 8% | 2% | 6% |
| **GPT-6.1 Terra** | 9% | 9% | 8% | — | 20% | 8% |
| **GPT-6.1 Sol** | 8% | 5% | 2% | 20% | — | 4% |
| **Opus 5.5** | 9% | 9% | 6% | 8% | 4% | — |

Across models: **8% twins**, best match 0.65.

## Reading it

Re-asking the same model reproduces 18% of its ideas; a different model reproduces 8%. Anything a state changes by less than the first number is inside the noise of simply asking twice.
