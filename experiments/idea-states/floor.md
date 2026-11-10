# With a state vs without, against the no-state baseline

Brief: food-waste-city. Same model, same brief, four conditions. **No state** = one plain list scored against another plain list from the same model — what the model does when nothing is done to it. The three state columns score the state's list against the plain list from the same seed. Score is the average best embedding match: higher = more of the same ideas, lower = further away.

| model | no state (two lists) | walk | daydream | doomscroll |
|---|---|---|---|---|
| Opus 5.5 | 0.764 (floor 0.717) | 0.664 **below** | 0.631 **below** | 0.674 **below** |
| DeepSeek v4.1 | 0.719 (floor 0.699) | 0.686 **below** | 0.555 **below** | 0.563 **below** |
| MiniMax M3.1 | 0.677 (floor 0.662) | 0.657 **below** | 0.617 **below** | 0.647 **below** |
| GPT-6.1 Sol | 0.735 (floor 0.719) | 0.711 **below** | 0.675 **below** | 0.700 **below** |
| GPT-6.1 Terra | 0.725 (floor 0.697) | 0.718 | 0.687 **below** | 0.710 |
| Qwen3.8 Max | 0.711 (floor 0.670) | — | 0.645 **below** | 0.704 |

**below** = under the lowest no-state value for that model, i.e. further from its own plain list than two plain lists ever are from each other.

## Verdict

- daydream clears the floor on **6 of 6** models
- walk clears it on **4 of 5**
- doomscroll clears it on **4 of 6**
