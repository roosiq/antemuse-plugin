# What the state changes, in percent

Each number is the median change against the same model's straight answer for the same brief and seed. Positive = more. A blank means that model did not produce a usable cell for that condition.

## anthropic/claude-opus-5.5

| after a | ideas | distance from straight | wording surprise | vocabulary spread | vocabulary longevity |
|---|---|---|---|---|---|
| walk | +3.5% | +18.477% | +38% | +0.561% | +2% |
| daydream | +0.0% | +27.649% | +20% | -3.603% | -1% |
| doomscroll | +1.0% | +12.276% | +40% | +3.096% | +6% |

## deepseek-v4.1

| after a | ideas | distance from straight | wording surprise | vocabulary spread | vocabulary longevity |
|---|---|---|---|---|---|
| walk | +0.0% | +4.417% | +29% | +2.048% | -6% |
| daydream | +0.0% | +37.138% | +41% | -15.703% | -13% |
| doomscroll | +26.5% | +14.332% | +13% | -6.682% | -10% |

## minimax-m3.1

| after a | ideas | distance from straight | wording surprise | vocabulary spread | vocabulary longevity |
|---|---|---|---|---|---|
| walk | -7.5% | -0.728% | -5% | -2.790% | -34% |
| daydream | +0.7% | +8.578% | +49% | -2.476% | -22% |
| doomscroll | +27.0% | +4.491% | +38% | -3.684% | -16% |

## openai/gpt-6.1-sol

| after a | ideas | distance from straight | wording surprise | vocabulary spread | vocabulary longevity |
|---|---|---|---|---|---|
| walk | +0.0% | +4.653% | +2% | -2.042% | +0% |
| daydream | +0.0% | +11.409% | +15% | -1.332% | +12% |
| doomscroll | +0.0% | +12.142% | +11% | +1.057% | +11% |

## gpt-6.1-terra

| after a | ideas | distance from straight | wording surprise | vocabulary spread | vocabulary longevity |
|---|---|---|---|---|---|
| walk | +0.0% | +5.027% | +7% | -3.335% | -20% |
| daydream | +0.0% | +13.984% | +9% | -1.824% | +14% |
| doomscroll | +0.0% | +6.857% | +36% | -1.365% | +12% |

## qwen3.8-max

| after a | ideas | distance from straight | wording surprise | vocabulary spread | vocabulary longevity |
|---|---|---|---|---|---|
| walk | — | — | — | — | — |
| daydream | +39.1% | +17.568% | +5% | -4.851% | +33% |
| doomscroll | +29.3% | +3.536% | -15% | -11.060% | -5% |

Reading it: wording surprise up with vocabulary spread down means the model picked less ordinary words while reaching for a smaller set of them. Distance from straight is the only column that says the ideas moved somewhere new; it does not say they are better.
