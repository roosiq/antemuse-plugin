# Idea states — the arithmetic

Blocks: 4 (model × brief × seed with a usable straight cell). Every number below is the paired difference state − straight inside a block.

## walk

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 4 | +1.750 | 2.062 | +0.85 | [-1.530, +5.030] | 0.500 |
| distinctiveness (distance from other conditions) | 4 | +0.045 | 0.041 | +1.11 | [-0.020, +0.110] | 0.250 |
| diversity (mean pairwise distance) | 4 | +0.028 | 0.037 | +0.77 | [-0.030, +0.086] | 0.500 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 4 | +54.650 | 56.041 | +0.98 | [-34.511, +143.811] | 0.250 |
| surprisal per token (nats) | 4 | +0.233 | 0.308 | +0.76 | [-0.257, +0.722] | 0.250 |
| type-token ratio | 4 | +0.001 | 0.026 | +0.06 | [-0.040, +0.043] | 1.000 |
| MTLD lexical diversity | 4 | +2.250 | 30.512 | +0.07 | [-46.295, +50.795] | 0.625 |
| distinct bigrams | 4 | +0.013 | 0.021 | +0.63 | [-0.020, +0.046] | 0.375 |
| hapax share | 4 | -0.013 | 0.013 | -1.01 | [-0.034, +0.008] | 0.250 |
| compression ratio | 4 | +0.003 | 0.017 | +0.17 | [-0.025, +0.031] | 0.750 |
| self bigram overlap | 4 | -0.000 | 0.002 | -0.13 | [-0.003, +0.003] | 0.875 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## daydream

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 4 | +0.000 | 0.000 | +0.00 | [+0.000, +0.000] | 1.000 |
| distinctiveness (distance from other conditions) | 4 | +0.064 | 0.055 | +1.16 | [-0.023, +0.151] | 0.250 |
| diversity (mean pairwise distance) | 4 | +0.001 | 0.033 | +0.02 | [-0.052, +0.053] | 1.000 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 4 | +42.350 | 47.923 | +0.88 | [-33.896, +118.596] | 0.125 |
| surprisal per token (nats) | 4 | +0.202 | 0.165 | +1.23 | [-0.060, +0.464] | 0.125 |
| type-token ratio | 4 | -0.024 | 0.017 | -1.41 | [-0.050, +0.003] | 0.125 |
| MTLD lexical diversity | 4 | +23.925 | 57.882 | +0.41 | [-68.165, +116.015] | 0.750 |
| distinct bigrams | 4 | +0.005 | 0.023 | +0.21 | [-0.032, +0.041] | 0.875 |
| hapax share | 4 | -0.033 | 0.018 | -1.78 | [-0.062, -0.003] | 0.125 |
| compression ratio | 4 | -0.004 | 0.014 | -0.27 | [-0.026, +0.019] | 0.625 |
| self bigram overlap | 4 | +0.000 | 0.002 | +0.03 | [-0.004, +0.004] | 1.000 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## doomscroll

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 4 | +0.500 | 0.577 | +0.87 | [-0.419, +1.419] | 0.500 |
| distinctiveness (distance from other conditions) | 4 | +0.028 | 0.025 | +1.13 | [-0.011, +0.067] | 0.250 |
| diversity (mean pairwise distance) | 4 | +0.024 | 0.039 | +0.61 | [-0.039, +0.087] | 0.375 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 4 | +124.775 | 143.263 | +0.87 | [-103.156, +352.706] | 0.125 |
| surprisal per token (nats) | 4 | +0.412 | 0.331 | +1.24 | [-0.115, +0.939] | 0.125 |
| type-token ratio | 4 | +0.019 | 0.025 | +0.76 | [-0.021, +0.059] | 0.250 |
| MTLD lexical diversity | 4 | +34.550 | 59.740 | +0.58 | [-60.497, +129.597] | 0.375 |
| distinct bigrams | 4 | +0.013 | 0.022 | +0.59 | [-0.022, +0.047] | 0.375 |
| hapax share | 4 | -0.015 | 0.015 | -0.98 | [-0.038, +0.009] | 0.125 |
| compression ratio | 4 | +0.013 | 0.017 | +0.75 | [-0.014, +0.040] | 0.250 |
| self bigram overlap | 4 | +0.000 | 0.002 | +0.16 | [-0.002, +0.003] | 0.875 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## Per model

| model | condition | Δ distinctiveness | Δ perplexity | Δ ideas | n |
|---|---|---|---|---|---|
| anthropic/claude-opus-5.5 | walk | +0.045 | +54.6 | +1.8 | 4 |
| anthropic/claude-opus-5.5 | daydream | +0.064 | +42.4 | +0.0 | 4 |
| anthropic/claude-opus-5.5 | doomscroll | +0.028 | +124.8 | +0.5 | 4 |

## What n would settle it

At the observed sd (0.025) on distinctiveness, a 95% interval of ±0.02 needs n ≈ 6 blocks per condition. Blocks here: 4.
