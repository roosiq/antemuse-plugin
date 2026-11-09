# Idea states — the arithmetic

Blocks: 2 (model × brief × seed with a usable straight cell). Every number below is the paired difference state − straight inside a block.

## walk

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 2 | +0.000 | 0.000 | +0.00 | [+0.000, +0.000] | 1.000 |
| distinctiveness (distance from other conditions) | 2 | +0.019 | 0.021 | +0.90 | [-0.172, +0.210] | 0.500 |
| diversity (mean pairwise distance) | 2 | -0.001 | 0.002 | -0.24 | [-0.020, +0.019] | 1.000 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 2 | +49.450 | 140.361 | +0.35 | [-1211.621, +1310.521] | 1.000 |
| surprisal per token (nats) | 2 | +0.023 | 0.416 | +0.06 | [-3.713, +3.759] | 1.000 |
| type-token ratio | 2 | -0.019 | 0.004 | -4.48 | [-0.057, +0.019] | 0.500 |
| MTLD lexical diversity | 2 | -36.550 | 36.416 | -1.00 | [-363.729, +290.630] | 0.500 |
| distinct bigrams | 2 | -0.014 | 0.018 | -0.82 | [-0.173, +0.144] | 0.500 |
| hapax share | 2 | -0.014 | 0.030 | -0.44 | [-0.287, +0.260] | 1.000 |
| compression ratio | 2 | -0.004 | 0.004 | -0.99 | [-0.035, +0.028] | 0.500 |
| self bigram overlap | 2 | +0.000 | 0.001 | +0.10 | [-0.009, +0.009] | 1.000 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## daydream

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 2 | +0.000 | 0.000 | +0.00 | [+0.000, +0.000] | 1.000 |
| distinctiveness (distance from other conditions) | 2 | +0.040 | 0.004 | +9.43 | [+0.002, +0.078] | 0.500 |
| diversity (mean pairwise distance) | 2 | -0.012 | 0.013 | -0.93 | [-0.133, +0.108] | 0.500 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 2 | +45.450 | 88.035 | +0.52 | [-745.498, +836.398] | 1.000 |
| surprisal per token (nats) | 2 | +0.078 | 0.228 | +0.34 | [-1.968, +2.124] | 1.000 |
| type-token ratio | 2 | -0.010 | 0.023 | -0.44 | [-0.213, +0.193] | 1.000 |
| MTLD lexical diversity | 2 | +15.000 | 71.983 | +0.21 | [-631.735, +661.735] | 1.000 |
| distinct bigrams | 2 | +0.012 | 0.002 | +5.42 | [-0.008, +0.031] | 0.500 |
| hapax share | 2 | -0.009 | 0.007 | -1.27 | [-0.073, +0.055] | 0.500 |
| compression ratio | 2 | -0.002 | 0.015 | -0.10 | [-0.135, +0.132] | 1.000 |
| self bigram overlap | 2 | -0.001 | 0.001 | -1.13 | [-0.007, +0.006] | 0.500 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## doomscroll

| metric | n | Δ | sd | dz | 95% CI | p (sign-flip) |
|---|---|---|---|---|---|---|
| ideas delivered | 2 | +0.000 | 0.000 | +0.00 | [+0.000, +0.000] | 1.000 |
| distinctiveness (distance from other conditions) | 2 | +0.027 | 0.032 | +0.83 | [-0.259, +0.312] | 0.500 |
| diversity (mean pairwise distance) | 2 | -0.005 | 0.021 | -0.27 | [-0.190, +0.179] | 1.000 |
| perplexity (Qwen3-0.6B, lower = more predictable) | 2 | +142.200 | 192.616 | +0.74 | [-1588.357, +1872.757] | 0.500 |
| surprisal per token (nats) | 2 | +0.278 | 0.354 | +0.79 | [-2.904, +3.461] | 0.500 |
| type-token ratio | 2 | -0.008 | 0.016 | -0.46 | [-0.154, +0.139] | 1.000 |
| MTLD lexical diversity | 2 | +15.950 | 37.265 | +0.43 | [-318.853, +350.753] | 1.000 |
| distinct bigrams | 2 | +0.004 | 0.014 | +0.28 | [-0.123, +0.131] | 1.000 |
| hapax share | 2 | -0.008 | 0.014 | -0.57 | [-0.135, +0.119] | 1.000 |
| compression ratio | 2 | -0.001 | 0.006 | -0.08 | [-0.058, +0.057] | 1.000 |
| self bigram overlap | 2 | -0.000 | 0.000 | -6.36 | [-0.001, +0.000] | 0.500 |
| self NLL/token from own logprobs | 0 | — | — | — | — | — |

## Per model

| model | condition | Δ distinctiveness | Δ perplexity | Δ ideas | n |
|---|---|---|---|---|---|
| openai/gpt-6.1-terra | walk | +0.019 | +49.5 | +0.0 | 2 |
| openai/gpt-6.1-terra | daydream | +0.040 | +45.5 | +0.0 | 2 |
| openai/gpt-6.1-terra | doomscroll | +0.027 | +142.2 | +0.0 | 2 |

## What n would settle it

At the observed sd (0.032) on distinctiveness, a 95% interval of ±0.02 needs n ≈ 10 blocks per condition. Blocks here: 2.
