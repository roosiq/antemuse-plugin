# Straight lists of 50 ideas, asked 4 times

No state. Two ideas count as the same at embedding similarity 0.80. 'Twin' = share of a list's ideas that reappear in the other list.

## Same model, asked again

| model | lists | twin ideas | avg best match | distinct in the pooled set |
|---|---|---|---|---|
| DeepSeek v4.1 | 4 | 20% | 0.70 | 157 of 200 (78%) |
| Qwen3.8 Max | 4 | 17% | 0.69 | 164 of 200 (82%) |
| MiniMax M3.1 | 4 | 10% | 0.67 | 184 of 207 (89%) |
| GPT-6.1 Terra | 4 | 24% | 0.71 | 149 of 200 (74%) |
| GPT-6.1 Sol | 4 | 27% | 0.73 | 144 of 200 (72%) |
| Opus 5.5 | 4 | 36% | 0.75 | 129 of 200 (64%) |

Average across models: **22% of ideas are twins when the same model is asked again**, best match 0.71.

## Different models, asked once each

| | DeepSeek  | Qwen3.8 M | MiniMax M | GPT-6.1 T | GPT-6.1 S | Opus 5.5 |
|---|---|---|---|---|---|---|
| **DeepSeek v4.1** | — | 8% | 6% | 12% | 12% | 12% |
| **Qwen3.8 Max** | 8% | — | 6% | 8% | 6% | 8% |
| **MiniMax M3.1** | 6% | 6% | — | 8% | 6% | 6% |
| **GPT-6.1 Terra** | 12% | 8% | 8% | — | 14% | 12% |
| **GPT-6.1 Sol** | 12% | 6% | 6% | 14% | — | 14% |
| **Opus 5.5** | 12% | 8% | 6% | 12% | 14% | — |

Across models: **9% twins**, best match 0.67.

## Reading it

Re-asking the same model reproduces 22% of its ideas; a different model reproduces 9%. Anything a state changes by less than the first number is inside the noise of simply asking twice.
