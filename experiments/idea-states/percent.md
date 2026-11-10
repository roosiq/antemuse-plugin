# What changes after a state, in percent

Each number compares the list to the same model's plain list for the same brief, same seed. Positive means more. A dash means that model produced nothing usable for that condition.

## anthropic/claude-opus-5.5

| state | ideas | different ideas | perplexity | word variety |
|---|---|---|---|---|
| walk | +3.5% | +18% | +38% | +0.6% |
| daydream | +0.0% | +28% | +20% | -3.6% |
| doomscroll | +1.0% | +12% | +40% | +3.1% |

## deepseek-v4.1

| state | ideas | different ideas | perplexity | word variety |
|---|---|---|---|---|
| walk | +0.0% | +4% | +29% | +2.0% |
| daydream | +0.0% | +37% | +41% | -15.7% |
| doomscroll | +26.5% | +14% | +13% | -6.7% |

## minimax-m3.1

| state | ideas | different ideas | perplexity | word variety |
|---|---|---|---|---|
| walk | -7.5% | -1% | -5% | -2.8% |
| daydream | +0.7% | +9% | +49% | -2.5% |
| doomscroll | +27.0% | +4% | +38% | -3.7% |

## openai/gpt-6.1-sol

| state | ideas | different ideas | perplexity | word variety |
|---|---|---|---|---|
| walk | +0.0% | +5% | +2% | -2.0% |
| daydream | +0.0% | +11% | +15% | -1.3% |
| doomscroll | +0.0% | +12% | +11% | +1.1% |

## gpt-6.1-terra

| state | ideas | different ideas | perplexity | word variety |
|---|---|---|---|---|
| walk | +0.0% | +5% | +7% | -3.3% |
| daydream | +0.0% | +14% | +9% | -1.8% |
| doomscroll | +0.0% | +7% | +36% | -1.4% |

## qwen3.8-max

| state | ideas | different ideas | perplexity | word variety |
|---|---|---|---|---|
| walk | — | — | — | — |
| daydream | +39.1% | +18% | +5% | -4.9% |
| doomscroll | +29.3% | +4% | -15% | -11.1% |

Reading it: higher perplexity with less word variety means the model reached for less ordinary words while using a narrower set of them. "Different ideas" is the only column that says the list went somewhere new. None of them say the ideas are better.
