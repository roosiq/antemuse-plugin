# Idea states — the arithmetic

Blocks: 4 (model × brief × seed with a usable straight cell). Every number below is the paired difference state − straight inside a block.

## walk

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 0 | — | — | — | — | — |
| distinctiveness (distance from other conditions) | 0 | — | — | — | — | — |
| diversity (mean pairwise distance) | 0 | — | — | — | — | — |
| perplexity (Qwen3-0.6B, lower = more predictable) | 0 | — | — | — | — | — |
| surprisal per token (nats) | 0 | — | — | — | — | — |
| type-token ratio | 0 | — | — | — | — | — |
| MTLD lexical diversity | 0 | — | — | — | — | — |
| distinct bigrams | 0 | — | — | — | — | — |
| hapax share | 0 | — | — | — | — | — |
| compression ratio | 0 | — | — | — | — | — |
| self bigram overlap | 0 | — | — | — | — | — |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## daydream

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 3 | +9.000 | 15.588 | +0.58 | [-29.727, +47.727] | 1.000 |
| distinctiveness (distance from other conditions) | 3 | +0.052 | 0.017 | +3.09 | [+0.010, +0.094] | 0.250 |
| diversity (mean pairwise distance) | 3 | -0.008 | 0.043 | -0.18 | [-0.115, +0.099] | 1.000 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 3 | +83.667 | 148.794 | +0.56 | [-285.987, +453.320] | 0.750 |
| surprisal per token (nats) | 3 | +0.295 | 0.501 | +0.59 | [-0.950, +1.541] | 0.500 |
| type-token ratio | 3 | -0.034 | 0.133 | -0.25 | [-0.363, +0.296] | 0.750 |
| MTLD lexical diversity | 3 | +37.100 | 55.127 | +0.67 | [-99.855, +174.055] | 0.500 |
| distinct bigrams | 3 | -0.006 | 0.094 | -0.07 | [-0.239, +0.226] | 1.000 |
| hapax share | 3 | -0.021 | 0.031 | -0.67 | [-0.097, +0.056] | 0.500 |
| compression ratio | 3 | -0.017 | 0.060 | -0.29 | [-0.165, +0.130] | 0.750 |
| self bigram overlap | 3 | -0.001 | 0.007 | -0.21 | [-0.018, +0.015] | 1.000 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## doomscroll

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 4 | +6.750 | 13.500 | +0.50 | [-14.729, +28.229] | 1.000 |
| distinctiveness (distance from other conditions) | 4 | +0.012 | 0.013 | +0.91 | [-0.009, +0.032] | 0.250 |
| diversity (mean pairwise distance) | 4 | -0.045 | 0.069 | -0.65 | [-0.154, +0.065] | 0.500 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 4 | -28.400 | 53.636 | -0.53 | [-113.734, +56.934] | 0.375 |
| surprisal per token (nats) | 4 | -0.117 | 0.230 | -0.51 | [-0.483, +0.249] | 0.375 |
| type-token ratio | 4 | -0.076 | 0.106 | -0.72 | [-0.245, +0.093] | 0.375 |
| MTLD lexical diversity | 4 | -5.400 | 42.239 | -0.13 | [-72.602, +61.802] | 0.750 |
| distinct bigrams | 4 | -0.049 | 0.088 | -0.56 | [-0.188, +0.090] | 0.500 |
| hapax share | 4 | -0.055 | 0.060 | -0.92 | [-0.151, +0.040] | 0.250 |
| compression ratio | 4 | -0.029 | 0.045 | -0.64 | [-0.100, +0.043] | 0.375 |
| self bigram overlap | 4 | +0.002 | 0.008 | +0.29 | [-0.010, +0.014] | 0.625 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## Per model

| model | condition | Δ distinctiveness | Δ perplexity | Δ ideas | n |
|---|---|---|---|---|---|
| qwen/qwen3.8-max-prime | walk | — | — | — | 0 |
| qwen/qwen3.8-max-prime | daydream | +0.052 | +83.7 | +9.0 | 3 |
| qwen/qwen3.8-max-prime | doomscroll | +0.012 | -28.4 | +6.8 | 4 |

## What n would settle it

At the observed sd (0.013) on distinctiveness, a 95% interval of ±0.02 needs n ≈ 2 blocks per condition. Blocks here: 4.
