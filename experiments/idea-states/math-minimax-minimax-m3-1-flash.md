# Idea states — the arithmetic

Blocks: 4 (model × brief × seed with a usable straight cell). Every number below is the paired difference state − straight inside a block.

## walk

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 4 | -3.750 | 8.180 | -0.46 | [-16.765, +9.265] | 1.000 |
| distinctiveness (distance from other conditions) | 4 | +0.006 | 0.034 | +0.19 | [-0.048, +0.061] | 0.875 |
| diversity (mean pairwise distance) | 4 | -0.004 | 0.034 | -0.12 | [-0.058, +0.050] | 0.750 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 4 | -3.650 | 84.536 | -0.04 | [-138.148, +130.848] | 0.875 |
| surprisal per token (nats) | 4 | -0.159 | 0.520 | -0.31 | [-0.987, +0.668] | 0.625 |
| type-token ratio | 4 | -0.027 | 0.040 | -0.68 | [-0.090, +0.036] | 0.250 |
| MTLD lexical diversity | 4 | -47.150 | 38.036 | -1.24 | [-107.666, +13.366] | 0.250 |
| distinct bigrams | 4 | -0.019 | 0.043 | -0.45 | [-0.088, +0.049] | 0.625 |
| hapax share | 4 | +0.014 | 0.026 | +0.54 | [-0.027, +0.055] | 0.375 |
| compression ratio | 4 | -0.005 | 0.016 | -0.27 | [-0.031, +0.022] | 1.000 |
| self bigram overlap | 4 | +0.004 | 0.004 | +0.98 | [-0.002, +0.010] | 0.125 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## daydream

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 3 | +0.333 | 0.577 | +0.58 | [-1.101, +1.768] | 1.000 |
| distinctiveness (distance from other conditions) | 3 | +0.036 | 0.030 | +1.23 | [-0.037, +0.110] | 0.250 |
| diversity (mean pairwise distance) | 3 | +0.017 | 0.012 | +1.40 | [-0.013, +0.047] | 0.250 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 3 | +60.900 | 103.875 | +0.59 | [-197.160, +318.960] | 0.500 |
| surprisal per token (nats) | 3 | +0.148 | 0.545 | +0.27 | [-1.204, +1.501] | 0.750 |
| type-token ratio | 3 | -0.019 | 0.030 | -0.62 | [-0.093, +0.056] | 0.500 |
| MTLD lexical diversity | 3 | -22.233 | 57.665 | -0.39 | [-165.494, +121.027] | 0.500 |
| distinct bigrams | 3 | -0.015 | 0.042 | -0.35 | [-0.120, +0.090] | 1.000 |
| hapax share | 3 | +0.047 | 0.028 | +1.64 | [-0.024, +0.117] | 0.250 |
| compression ratio | 3 | +0.006 | 0.026 | +0.25 | [-0.057, +0.070] | 0.750 |
| self bigram overlap | 3 | +0.002 | 0.004 | +0.61 | [-0.007, +0.011] | 0.500 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## doomscroll

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 4 | +13.500 | 26.338 | +0.51 | [-28.403, +55.403] | 0.500 |
| distinctiveness (distance from other conditions) | 4 | +0.042 | 0.058 | +0.73 | [-0.050, +0.135] | 0.125 |
| diversity (mean pairwise distance) | 4 | +0.026 | 0.050 | +0.52 | [-0.053, +0.105] | 0.375 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 4 | +78.450 | 75.942 | +1.03 | [-42.374, +199.274] | 0.250 |
| surprisal per token (nats) | 4 | +0.312 | 0.294 | +1.06 | [-0.156, +0.779] | 0.250 |
| type-token ratio | 4 | -0.018 | 0.043 | -0.40 | [-0.086, +0.051] | 0.500 |
| MTLD lexical diversity | 4 | -27.500 | 5.452 | -5.04 | [-36.174, -18.826] | 0.125 |
| distinct bigrams | 4 | +0.004 | 0.018 | +0.23 | [-0.024, +0.032] | 0.875 |
| hapax share | 4 | +0.004 | 0.042 | +0.10 | [-0.062, +0.071] | 0.875 |
| compression ratio | 4 | -0.002 | 0.019 | -0.11 | [-0.032, +0.028] | 0.875 |
| self bigram overlap | 4 | -0.001 | 0.002 | -0.83 | [-0.004, +0.001] | 0.250 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## Per model

| model | condition | Δ distinctiveness | Δ perplexity | Δ ideas | n |
|---|---|---|---|---|---|
| minimax/minimax-m3.1-flash | walk | +0.006 | -3.6 | -3.8 | 4 |
| minimax/minimax-m3.1-flash | daydream | +0.036 | +60.9 | +0.3 | 3 |
| minimax/minimax-m3.1-flash | doomscroll | +0.042 | +78.5 | +13.5 | 4 |

## What n would settle it

At the observed sd (0.058) on distinctiveness, a 95% interval of ±0.02 needs n ≈ 32 blocks per condition. Blocks here: 4.
