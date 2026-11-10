# Benchmark outcome — does an agent state change a list of 50 ideas?

Six models, four conditions, deterministic measurement, no LLM judge.
Run: 2026-11-09. Evidence: `results-*.json`, `percent.md`, `math-*.md`, `index.html`.

## Question

Ask a model for 50 ideas for a brief. Ask it again with a walk, daydream or doomscroll held
in the middle — the state directive comes verbatim from `core/states.py`, doomscroll's feed
from `core/sources.feed_pick`. Does the list change, and by how much?

## Design

- 2 development briefs (city food waste; a two-minute one-room short film)
- 2 seeds per model (11, 12), all four conditions per seed — GPT-6.1 Terra ran one seed
- conditions: straight (one call), and walk / daydream / doomscroll (state turn, then the list)
- 50 ideas requested per cell

## Measurement

Everything is a function of the text plus a fixed model, so it reproduces exactly:

| axis | what it reads | source |
|---|---|---|
| distance from straight | mean distance to the nearest idea from the other conditions, same brief | MiniLM embeddings |
| surprise | token-level perplexity of the list | Qwen3-0.6B |
| vocabulary spread | type-token ratio | counts |
| vocabulary longevity | MTLD | counts |
| ideas delivered | parsed list length | counts |

Percent changes are medians of within-block ratios: (state − straight) / straight, same
model, same brief, same seed. Paired deltas with intervals and exact permutation p-values
are in `math-*.md`.

## Outcome

| model | condition | further from straight | surprise | vocab spread | ideas |
|---|---|---|---|---|---|
| Opus 5.5 | walk | +18.5% | +38% | +0.6% | +3.5% |
| Opus 5.5 | daydream | +27.6% | +20% | −3.6% | 0% |
| Opus 5.5 | doomscroll | +12.3% | +40% | +3.1% | +1.0% |
| GPT-6.1 Sol | walk | +4.7% | +2% | −2.0% | 0% |
| GPT-6.1 Sol | daydream | +11.4% | +15% | −1.3% | 0% |
| GPT-6.1 Sol | doomscroll | +12.1% | +11% | +1.1% | 0% |
| GPT-6.1 Terra | walk | +5.0% | +7% | −3.3% | 0% |
| GPT-6.1 Terra | daydream | +14.0% | +9% | −1.8% | 0% |
| GPT-6.1 Terra | doomscroll | +6.9% | +36% | −1.4% | 0% |
| DeepSeek v4.1 | walk | +4.4% | +29% | +2.0% | 0% |
| DeepSeek v4.1 | daydream | +37.1% | +41% | −15.7% | 0% |
| DeepSeek v4.1 | doomscroll | +14.3% | +13% | −6.7% | +26.5% |
| MiniMax M3.1 | walk | −0.7% | −5% | −2.8% | −7.5% |
| MiniMax M3.1 | daydream | +8.6% | +49% | −2.5% | +0.7% |
| MiniMax M3.1 | doomscroll | +4.5% | +38% | −3.7% | +27.0% |
| Qwen3.8 Max | walk | — | — | — | — |
| Qwen3.8 Max | daydream | +17.6% | +5% | −4.9% | +39.1% |
| Qwen3.8 Max | doomscroll | +3.5% | −15% | −11.1% | +29.3% |

## What the numbers say

1. **The state moves the list.** Daydream relocates the list on every model that produced
   cells: +8.6% to +37.1%. No model was unmoved.
2. **Magnitude is a property of the model, not the state.** DeepSeek daydream +37% against
   MiniMax daydream +8.6% is a 4× spread on the same manipulation.
3. **Surprise and relocation come apart.** MiniMax daydream shifts its wording most of any
   cell (+49%) while the list barely moves (+8.6%). GPT-6.1 Terra's doomscroll is +36%
   surprise, +6.9% relocation. Wording changing is not ideas changing.
4. **Vocabulary is the cost.** DeepSeek pays for its relocation with a 15.7% narrower word
   pool. Opus and Sol relocate without that cost (+0.6%, −1.3%). Qwen's doomscroll is the
   only cell where wording gets *less* surprising (−15%) and vocabulary shrinks most (−11%).
5. **Doomscroll ignores the count.** DeepSeek and MiniMax wrote 63 ideas instead of 50
   (+26.5%, +27.0%) under doomscroll. Opus overran only slightly (+1%), the GPT models not
   at all.
6. **walk is the weak state.** On four of six models it is within ±6% of straight; on
   MiniMax it is slightly negative. Only Opus relocates materially on walk (+18.5%).

## Limits

- Two briefs, two seeds — 4 cells per condition per model (Terra: 2). Direction, not
  magnitude, is the reportable part; `math-*.md` carries the intervals.
- Perplexity is not comparable across models; each list is scored by the same fixed LM but
  the models differ in register.
- No human ratings, so nothing here says an idea is good. It says the distribution of ideas
  moved, and what that cost in vocabulary.
- Qwen3.8 Max produced no walk cells at all (state turn then empty list); its walk row is a
  failure, not a null result.
- Logprobs exist only for open-weight models on this gateway, so no self-surprisal column
  appears here. `report-lp-*.md` holds that for DeepSeek and Kimi.
