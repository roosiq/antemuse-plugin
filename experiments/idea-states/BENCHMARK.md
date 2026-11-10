# What happens when a model takes a walk, daydreams, or doomscrolls before writing 50 ideas

Six models, four conditions, measured from the text itself. No model judges another model.
Run: 2026-11-09. Evidence: `results-*.json`, `percent.md`, `math-*.md`, `table.png`, `index.html`.

## The question

Ask a model for 50 ideas for a brief. Ask it again with a walk, daydream or doomscroll held in
between — the state text comes straight from `core/states.py`, and doomscroll's feed from
`core/sources.feed_pick`. Does the list change, and by how much?

## How it was set up

- Two briefs: cutting food waste in a city; a two-minute film shot in one room.
- Two seeds per model (11 and 12), all four conditions at each seed. GPT-6.1 Terra ran one seed.
- Four conditions: no state, then walk, daydream, doomscroll. In a state condition the model
  holds the brief, answers in that state, then comes back and writes the list.
- 50 ideas asked for in every list.

## What was measured

Three numbers per list, all computed from the text, all repeatable — run it again and you get
the same values:

- **Different ideas.** How far the list sits from the ideas the same model wrote for the same
  brief without a state. Bigger means the ideas moved somewhere new.
- **Unusual wording.** How surprising the list is to a small fixed language model. Higher means
  less ordinary phrasing.
- **Word variety.** The share of distinct words in the list. Lower means the model reuses more
  of the same words.

Ideas written is a plain count. Percentages compare each list with the same model's plain list
for the same brief and seed, and are medians over those comparisons. `math-*.md` has the
differences with their ranges.

## The numbers

| model | after a | different ideas | unusual wording | word variety | ideas written |
|---|---|---|---|---|---|
| Opus 5.5 | walk | +18% | +38% | +1% | +3.5% |
| Opus 5.5 | daydream | +28% | +20% | −4% | 0% |
| Opus 5.5 | doomscroll | +12% | +40% | +3% | +1% |
| GPT-6.1 Sol | walk | +5% | +2% | −2% | 0% |
| GPT-6.1 Sol | daydream | +11% | +15% | −1% | 0% |
| GPT-6.1 Sol | doomscroll | +12% | +11% | +1% | 0% |
| GPT-6.1 Terra | walk | +5% | +7% | −3% | 0% |
| GPT-6.1 Terra | daydream | +14% | +9% | −2% | 0% |
| GPT-6.1 Terra | doomscroll | +7% | +36% | −1% | 0% |
| DeepSeek v4.1 | walk | +4% | +29% | +2% | 0% |
| DeepSeek v4.1 | daydream | +37% | +41% | −16% | 0% |
| DeepSeek v4.1 | doomscroll | +14% | +13% | −7% | +27% |
| MiniMax M3.1 | walk | −1% | −5% | −3% | −8% |
| MiniMax M3.1 | daydream | +9% | +49% | −2% | +1% |
| MiniMax M3.1 | doomscroll | +4% | +38% | −4% | +27% |
| Qwen3.8 Max | walk | no list | no list | no list | 0 |
| Qwen3.8 Max | daydream | +18% | +5% | −5% | +39% |
| Qwen3.8 Max | doomscroll | +4% | −15% | −11% | +29% |

## What it shows

1. **The state always changes the list.** Daydream moved the ideas on every model that
   produced a list, from +9% to +37%. None was unaffected.
2. **How much depends on the model, not the state.** The same daydream moves DeepSeek 37% and
   MiniMax 9%. That is a fourfold difference from one instruction.
3. **Different wording is not different ideas.** MiniMax's daydream changes its phrasing more
   than any other case (+49%) while the ideas themselves barely move (+9%). GPT-6.1 Terra's
   doomscroll is +36% wording and +7% ideas.
4. **Word variety is what it costs.** DeepSeek buys its 37% move with 16% less word variety —
   rarer words, fewer of them. Opus and Sol move without that cost.
5. **Doomscroll ignores the count.** DeepSeek and MiniMax wrote 63 ideas instead of 50. Opus
   and the GPT models stuck to 50.
6. **walk is the weak state.** On four of six models the list stays within 6% of the plain one,
   and on MiniMax it goes slightly backwards. Only Opus moves clearly (+18%).

## Limits

- Four lists per condition per model (Terra: two), over two briefs. Treat the direction as the
  finding, not the exact size.
- Nothing here says an idea is good. These numbers say the list moved, and what that cost in
  words. Judging whether an idea is any use needs people, and no people have rated these.
- Qwen3.8 Max produced no walk list at all — the state turn happened and the list came back
  empty. Its walk row is a failure, not a zero.
- Unusual wording is scored by the same small model for every list, but different models write
  in different registers, so compare conditions rather than models on that column.
- Per-token probabilities are only available from the open-weight models here, so no measure
  built on them appears in this table. `report-lp-*.md` holds that for DeepSeek and Kimi.
