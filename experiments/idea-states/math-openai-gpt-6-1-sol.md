# Idea states — the arithmetic

Blocks: 4 (model × brief × seed with a usable straight cell). Every number below is the paired difference state − straight inside a block.

## walk

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 4 | +0.000 | 0.000 | +0.00 | [+0.000, +0.000] | 1.000 |
| distinctiveness (distance from other conditions) | 4 | +0.015 | 0.014 | +1.06 | [-0.008, +0.038] | 0.125 |
| diversity (mean pairwise distance) | 4 | -0.026 | 0.019 | -1.36 | [-0.055, +0.004] | 0.250 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 4 | +1.775 | 55.573 | +0.03 | [-86.641, +90.191] | 1.000 |
| surprisal per token (nats) | 4 | +0.001 | 0.244 | +0.00 | [-0.388, +0.390] | 1.000 |
| type-token ratio | 4 | -0.015 | 0.034 | -0.44 | [-0.069, +0.039] | 0.500 |
| MTLD lexical diversity | 4 | +6.250 | 48.545 | +0.13 | [-70.985, +83.485] | 1.000 |
| distinct bigrams | 4 | -0.012 | 0.018 | -0.66 | [-0.041, +0.017] | 0.250 |
| hapax share | 4 | -0.003 | 0.013 | -0.19 | [-0.024, +0.019] | 0.750 |
| compression ratio | 4 | -0.004 | 0.003 | -1.13 | [-0.008, +0.001] | 0.250 |
| self bigram overlap | 4 | +0.004 | 0.005 | +0.80 | [-0.004, +0.012] | 0.250 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## daydream

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 4 | +0.000 | 0.000 | +0.00 | [+0.000, +0.000] | 1.000 |
| distinctiveness (distance from other conditions) | 4 | +0.029 | 0.016 | +1.82 | [+0.004, +0.053] | 0.125 |
| diversity (mean pairwise distance) | 4 | -0.018 | 0.017 | -1.08 | [-0.045, +0.009] | 0.250 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 4 | +47.275 | 54.927 | +0.86 | [-40.113, +134.663] | 0.250 |
| surprisal per token (nats) | 4 | +0.149 | 0.133 | +1.12 | [-0.063, +0.361] | 0.250 |
| type-token ratio | 4 | -0.008 | 0.029 | -0.27 | [-0.053, +0.038] | 0.625 |
| MTLD lexical diversity | 4 | +33.750 | 30.197 | +1.12 | [-14.294, +81.794] | 0.125 |
| distinct bigrams | 4 | +0.002 | 0.023 | +0.09 | [-0.034, +0.038] | 1.000 |
| hapax share | 4 | -0.006 | 0.028 | -0.23 | [-0.050, +0.038] | 1.000 |
| compression ratio | 4 | -0.001 | 0.015 | -0.06 | [-0.026, +0.024] | 0.875 |
| self bigram overlap | 4 | -0.000 | 0.001 | -0.00 | [-0.002, +0.002] | 1.000 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## doomscroll

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 4 | +0.000 | 0.000 | +0.00 | [+0.000, +0.000] | 1.000 |
| distinctiveness (distance from other conditions) | 4 | +0.017 | 0.032 | +0.52 | [-0.034, +0.067] | 0.500 |
| diversity (mean pairwise distance) | 4 | -0.010 | 0.009 | -1.13 | [-0.024, +0.004] | 0.250 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 4 | +43.350 | 73.554 | +0.59 | [-73.675, +160.375] | 0.500 |
| surprisal per token (nats) | 4 | +0.140 | 0.284 | +0.49 | [-0.312, +0.592] | 0.500 |
| type-token ratio | 4 | +0.008 | 0.027 | +0.31 | [-0.035, +0.051] | 0.625 |
| MTLD lexical diversity | 4 | +21.025 | 46.420 | +0.45 | [-52.829, +94.879] | 0.500 |
| distinct bigrams | 4 | +0.005 | 0.008 | +0.65 | [-0.007, +0.017] | 0.375 |
| hapax share | 4 | +0.007 | 0.014 | +0.49 | [-0.016, +0.030] | 0.375 |
| compression ratio | 4 | +0.003 | 0.012 | +0.28 | [-0.016, +0.023] | 0.750 |
| self bigram overlap | 4 | -0.001 | 0.000 | -1.53 | [-0.001, +0.000] | 0.125 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## Per model

| model | condition | Δ distinctiveness | Δ perplexity | Δ ideas | n |
|---|---|---|---|---|---|
| openai/gpt-6.1-sol | walk | +0.015 | +1.8 | +0.0 | 4 |
| openai/gpt-6.1-sol | daydream | +0.029 | +47.3 | +0.0 | 4 |
| openai/gpt-6.1-sol | doomscroll | +0.017 | +43.4 | +0.0 | 4 |

## What n would settle it

At the observed sd (0.032) on distinctiveness, a 95% interval of ±0.02 needs n ≈ 10 blocks per condition. Blocks here: 4.
