# With a state vs without, against the no-state baseline

Brief: food-waste-city. Same model, same brief, four conditions. **No state** = one plain list scored against another plain list from the same model — what the model does when nothing is done to it. The three state columns score the state's list against the plain list from the same seed. Score is the average best embedding match: higher = more of the same ideas, lower = further away.

| model | no state (two lists) | walk | daydream | doomscroll |
|---|---|---|---|---|
| Opus 5.5 | 0.757 (floor 0.743) | 0.664 **below** | 0.631 **below** | 0.674 **below** |
| DeepSeek v4.1 | 0.710 (floor 0.692) | 0.686 **below** | 0.555 **below** | 0.563 **below** |
| MiniMax M3.1 | 0.668 (floor 0.643) | 0.657 | 0.617 **below** | 0.647 |
| GPT-6.1 Sol | 0.713 (floor 0.700) | 0.711 | 0.675 **below** | 0.700 **below** |
| GPT-6.1 Terra | 0.715 (floor 0.687) | 0.718 | 0.687 **below** | 0.710 |
| Qwen3.8 Max | 0.696 (floor 0.674) | — | 0.645 **below** | 0.704 |

**below** = under the lowest no-state value for that model, i.e. further from its own plain list than two plain lists ever are from each other.

## Verdict

- daydream clears the floor on **6 of 6** models
- walk clears it on **2 of 5**
- doomscroll clears it on **3 of 6**
