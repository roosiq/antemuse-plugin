# Idea states — the arithmetic

Blocks: 4 (model × brief × seed with a usable straight cell). Every number below is the paired difference state − straight inside a block.

## walk

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 4 | +0.000 | 0.000 | +0.00 | [+0.000, +0.000] | 1.000 |
| distinctiveness (distance from other conditions) | 4 | +0.007 | 0.019 | +0.38 | [-0.023, +0.038] | 0.500 |
| diversity (mean pairwise distance) | 4 | +0.007 | 0.028 | +0.25 | [-0.038, +0.052] | 0.750 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 4 | +109.500 | 99.148 | +1.10 | [-48.244, +267.244] | 0.125 |
| surprisal per token (nats) | 4 | +0.259 | 0.082 | +3.15 | [+0.128, +0.390] | 0.125 |
| type-token ratio | 4 | +0.001 | 0.022 | +0.03 | [-0.034, +0.036] | 1.000 |
| MTLD lexical diversity | 4 | +8.300 | 47.036 | +0.18 | [-66.534, +83.134] | 1.000 |
| distinct bigrams | 4 | +0.021 | 0.024 | +0.91 | [-0.016, +0.059] | 0.250 |
| hapax share | 4 | +0.008 | 0.021 | +0.38 | [-0.026, +0.042] | 0.625 |
| compression ratio | 4 | +0.008 | 0.017 | +0.45 | [-0.019, +0.034] | 0.500 |
| self bigram overlap | 4 | -0.000 | 0.002 | -0.15 | [-0.003, +0.003] | 1.000 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## daydream

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 4 | +0.000 | 0.000 | +0.00 | [+0.000, +0.000] | 1.000 |
| distinctiveness (distance from other conditions) | 4 | +0.108 | 0.096 | +1.12 | [-0.045, +0.260] | 0.125 |
| diversity (mean pairwise distance) | 4 | -0.077 | 0.090 | -0.85 | [-0.219, +0.066] | 0.250 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 4 | +275.375 | 384.590 | +0.72 | [-336.507, +887.257] | 0.125 |
| surprisal per token (nats) | 4 | +0.432 | 0.258 | +1.67 | [+0.021, +0.843] | 0.125 |
| type-token ratio | 4 | -0.091 | 0.048 | -1.91 | [-0.167, -0.015] | 0.125 |
| MTLD lexical diversity | 4 | -25.875 | 27.848 | -0.93 | [-70.181, +18.431] | 0.125 |
| distinct bigrams | 4 | -0.056 | 0.065 | -0.86 | [-0.160, +0.048] | 0.125 |
| hapax share | 4 | -0.036 | 0.036 | -0.98 | [-0.094, +0.022] | 0.125 |
| compression ratio | 4 | -0.029 | 0.019 | -1.50 | [-0.059, +0.002] | 0.125 |
| self bigram overlap | 4 | +0.006 | 0.007 | +0.84 | [-0.006, +0.018] | 0.125 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## doomscroll

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 4 | +13.250 | 26.500 | +0.50 | [-28.911, +55.411] | 1.000 |
| distinctiveness (distance from other conditions) | 4 | +0.099 | 0.124 | +0.79 | [-0.099, +0.296] | 0.125 |
| diversity (mean pairwise distance) | 4 | +0.047 | 0.092 | +0.51 | [-0.100, +0.194] | 0.500 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 4 | -19.500 | 181.215 | -0.11 | [-307.814, +268.814] | 0.875 |
| surprisal per token (nats) | 4 | +0.019 | 0.394 | +0.05 | [-0.607, +0.645] | 1.000 |
| type-token ratio | 4 | -0.032 | 0.012 | -2.56 | [-0.052, -0.012] | 0.125 |
| MTLD lexical diversity | 4 | -12.275 | 11.221 | -1.09 | [-30.127, +5.577] | 0.125 |
| distinct bigrams | 4 | -0.006 | 0.016 | -0.38 | [-0.032, +0.020] | 0.375 |
| hapax share | 4 | -0.010 | 0.030 | -0.35 | [-0.058, +0.037] | 0.625 |
| compression ratio | 4 | -0.014 | 0.013 | -1.06 | [-0.034, +0.007] | 0.250 |
| self bigram overlap | 4 | +0.001 | 0.002 | +0.28 | [-0.003, +0.004] | 0.750 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## Per model

| model | condition | Δ distinctiveness | Δ perplexity | Δ ideas | n |
|---|---|---|---|---|---|
| deepseek/deepseek-v4.1-flash-1017 | walk | +0.007 | +109.5 | +0.0 | 4 |
| deepseek/deepseek-v4.1-flash-1017 | daydream | +0.108 | +275.4 | +0.0 | 4 |
| deepseek/deepseek-v4.1-flash-1017 | doomscroll | +0.099 | -19.5 | +13.2 | 4 |

## What n would settle it

At the observed sd (0.124) on distinctiveness, a 95% interval of ±0.02 needs n ≈ 148 blocks per condition. Blocks here: 4.
