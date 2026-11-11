# Every result in one table

Rows are model × condition. Changes are against that model's own plain list for the same brief and seed; 'different ideas', 'perplexity' and 'word variety' are median percent changes, 'distance' is an absolute score where lower means further away.

| model | condition | ideas written | distinct concepts | different ideas | perplexity | word variety | distance |
|---|---|---|---|---|---|---|---|
| Opus 5.5 | no state | 50 | 85% | 0 | 0 | 0 | 0.757 |
| Opus 5.5 | walk | 52 (+4%) | 92% | +18% | +38% | +1% | 0.673 |
| Opus 5.5 | daydream | 50 (+0%) | 98% | +28% | +20% | -4% | 0.639 |
| Opus 5.5 | doomscroll | 50 (+1%) | 91% | +12% | +40% | +3% | 0.673 |
| DeepSeek v4.1 | no state | 50 | 93% | 0 | 0 | 0 | 0.710 |
| DeepSeek v4.1 | walk | 50 (+0%) | 96% | +4% | +29% | +2% | 0.694 |
| DeepSeek v4.1 | daydream | 50 (+0%) | 100% | +37% | +41% | -16% | 0.550 |
| DeepSeek v4.1 | doomscroll | 63 (+26%) | 95% | +14% | +13% | -7% | 0.562 |
| MiniMax M3.1 | no state | 50 | 96% | 0 | 0 | 0 | 0.668 |
| MiniMax M3.1 | walk | 46 (-8%) | 98% | -1% | -5% | -3% | 0.650 |
| MiniMax M3.1 | daydream | 50 (+1%) | 99% | +9% | +49% | -2% | 0.606 |
| MiniMax M3.1 | doomscroll | 64 (+27%) | 97% | +4% | +38% | -4% | 0.642 |
| GPT-6.1 Sol | no state | 50 | 85% | 0 | 0 | 0 | 0.713 |
| GPT-6.1 Sol | walk | 50 (+0%) | 89% | +5% | +2% | -2% | 0.722 |
| GPT-6.1 Sol | daydream | 50 (+0%) | 95% | +11% | +15% | -1% | 0.677 |
| GPT-6.1 Sol | doomscroll | 50 (+0%) | 90% | +12% | +11% | +1% | 0.700 |
| GPT-6.1 Terra | no state | 50 | 81% | 0 | 0 | 0 | 0.715 |
| GPT-6.1 Terra | walk | 50 (+0%) | — | +5% | +7% | -3% | 0.718 |
| GPT-6.1 Terra | daydream | 50 (+0%) | — | +14% | +9% | -2% | 0.687 |
| GPT-6.1 Terra | doomscroll | 50 (+0%) | — | +7% | +36% | -1% | 0.710 |
| Qwen3.8 Max | no state | 43 | 95% | 0 | 0 | 0 | 0.696 |
| Qwen3.8 Max | walk | no list | — | — | — | — | — |
| Qwen3.8 Max | daydream | 50 (+39%) | 98% | +18% | +5% | -5% | 0.618 |
| Qwen3.8 Max | doomscroll | 50 (+29%) | 93% | +4% | -15% | -11% | 0.693 |

`distance` on the no-state row is one plain list against another plain list — the model's own spread. `distinct concepts` needs two lists, so Terra's state rows and Qwen's walk row have none.

## Cross-model agreement

Same brief and seed, six lists compared with each other (`overlap.md`):

| condition | ideas that match another model's | average best match | distinct in the pooled set |
|---|---|---|---|
| no state | 11% | 0.66 | 243 of 300 (81%) |
| walk | 6% | 0.64 | 228 of 253 (90%) |
| daydream | 1% | 0.57 | 293 of 300 (98%) |
| doomscroll | 5% | 0.63 | 275 of 302 (91%) |

Food waste brief, seed 11, the models that produced a list for that condition.
