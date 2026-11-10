# What happens when a model takes a walk, daydreams, or doomscrolls before writing 50 ideas

Six models, four conditions, measured from the text itself. No model judges another model.
Run: 2026-11-09. Evidence: `results-*.json`, `concepts.md`, `percent.md`, `math-*.md`,
`floor.md`, `overlap.md`, `table.png`, `concepts.png`, `index.html`.

## The question

Ask a model for 50 ideas for a brief. Ask it again with a walk, daydream or doomscroll held in
between — the state text comes straight from `core/states.py`, and doomscroll's feed from
`core/sources.feed_pick`. How many distinct concepts come out, and how much does the list move?

## How it was set up

- Two briefs: cutting food waste in a city; a two-minute film shot in one room.
- Two seeds per model (11 and 12), all four conditions at each seed. GPT-6.1 Terra ran one seed.
- Four conditions: no state, then walk, daydream, doomscroll. In a state condition the model
  holds the brief, answers in that state, then comes back and writes the list.
- 50 ideas asked for in every list.

## The direct count: distinct concepts, with a state vs without

Pool two lists of 50 from the same model and brief, cluster the 100 ideas, and count the
clusters. Two lists without a state repeat themselves; two lists split by a state repeat far
less. Nothing is judged here — the count comes from clustering the text. `concepts.md`.

Food waste:

| model | no state | walk | daydream | doomscroll |
|---|---|---|---|---|
| Opus 5.5 | 85 of 100 (85%) | 98 of 107 (92%) | 98 of 100 (98%) | 92 of 101 (91%) |
| DeepSeek v4.1 | 93 of 100 (93%) | 96 of 100 (96%) | 100 of 100 (100%) | 145 of 153 (95%) |
| MiniMax M3.1 | 96 of 100 (96%) | 99 of 101 (98%) | 100 of 101 (99%) | 98 of 101 (97%) |
| GPT-6.1 Sol | 85 of 100 (85%) | 89 of 100 (89%) | 95 of 100 (95%) | 90 of 100 (90%) |
| Qwen3.8 Max | 95 of 100 (95%) | no list | 98 of 100 (98%) | 93 of 100 (93%) |

One room:

| model | no state | walk | daydream | doomscroll |
|---|---|---|---|---|
| Opus 5.5 | 96 of 100 (96%) | 100 of 100 (100%) | 100 of 100 (100%) | 101 of 101 (100%) |
| DeepSeek v4.1 | 97 of 100 (97%) | 99 of 100 (99%) | 100 of 100 (100%) | 97 of 100 (97%) |
| MiniMax M3.1 | 100 of 100 (100%) | 84 of 84 (100%) | no list | 153 of 153 (100%) |
| GPT-6.1 Sol | 99 of 100 (99%) | 100 of 100 (100%) | 99 of 100 (99%) | 98 of 100 (98%) |
| Qwen3.8 Max | 69 of 73 (95%) | no list | no list | 99 of 100 (99%) |

Distinct concepts per 100 ideas written, averaged over models:

| condition | mean | range |
|---|---|---|
| no state | 93.8 | 85–100% |
| walk | 96.7 | 89–100% |
| daydream | 98.6 | 95–100% |
| doomscroll | 96.0 | 90–100% |

So on the practical brief a plain second list repeats about 1 idea in 7 — 85 of 100 distinct on
Opus and Sol, 93–96 on the others. Put daydream in between and the repetition is nearly gone:
98 to 100 distinct. On the open brief there was almost no repetition to remove, because the
models were already writing 96–100 distinct.

## The numbers behind "the list moved"

Three numbers per list, all computed from the text, all repeatable — run it again and you get
the same values:

- **Different ideas.** How far the list sits from the ideas the same model wrote for the same
  brief without a state. Bigger means the ideas moved somewhere new.
- **Perplexity.** How surprising the list is to a small fixed language model. Higher means
  less ordinary phrasing.
- **Word variety.** The share of distinct words in the list. Lower means the model reuses more
  of the same words.

Percentages compare each list with the same model's plain list for the same brief and seed, and
are medians over those comparisons. `math-*.md` has the differences with their ranges.

| model | state | different ideas | perplexity | word variety | ideas written |
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
| MiniMax M3.1 | daydream | +9% | +49% | −2.5% | +1% |
| MiniMax M3.1 | doomscroll | +4% | +38% | −4% | +27% |
| Qwen3.8 Max | walk | no list | no list | no list | 0 |
| Qwen3.8 Max | daydream | +18% | +5% | −5% | +39% |
| Qwen3.8 Max | doomscroll | +4% | −15% | −11% | +29% |

## What it shows

1. **Daydream produces the most distinct concepts, on every model that produced a list.** Per
   100 ideas written: 98.6 against 93.8 with no state. Opus goes from 85 distinct to 98; Sol
   from 85 to 95; DeepSeek to 100 of 100.
2. **The size depends on the model, not the state.** The same daydream moves DeepSeek's ideas
   37% and MiniMax's 9%. A fourfold difference from one instruction.
3. **Higher perplexity is not different ideas.** MiniMax's daydream raises perplexity but the
   ideas barely move; GPT-6.1 Terra's doomscroll is +36% perplexity and +7% different ideas.
4. **Word variety is what it costs.** DeepSeek buys its 37% move with 16% less word variety —
   rarer words, fewer of them. Opus and Sol move without that cost.
5. **Doomscroll ignores the count.** DeepSeek and MiniMax wrote 63 ideas instead of 50. Opus
   and the GPT models stuck to 50.
6. **walk is the weak state.** On four of six models the list stays within 6% of the plain one,
   and on MiniMax it goes slightly backwards (−1%). Only Opus moves clearly (+18%). It gains
   only about 3 points of distinctness against daydream's 5.

## Do different models write the same ideas?

Same brief, same seed, the six lists side by side. Two ideas count as the same at 0.80
similarity. `overlap.md` has the per-pair matrices.

| brief | condition | overlap between models | average best match | distinct in the pooled set |
|---|---|---|---|---|
| food waste | no state | 11% | 0.66 | 243 of 300 (81%) |
| food waste | walk | 6% | 0.64 | 228 of 253 (90%) |
| food waste | daydream | 1% | 0.57 | 293 of 300 (98%) |
| food waste | doomscroll | 5% | 0.63 | 275 of 302 (91%) |
| one room | no state | 1% | 0.47 | 295 of 300 (98%) |
| one room | walk | 0% | 0.45 | 232 of 234 (99%) |
| one room | daydream | 0% | 0.47 | 250 of 250 (100%) |
| one room | doomscroll | 0% | 0.43 | 300 of 301 (100%) |

The overlap level depends on the threshold, so here are the same six lists through different
ones — no state, seed 11:

| brief | avg best match | 0.50 | 0.60 | 0.70 | 0.80 |
|---|---|---|---|---|---|
| food waste | 0.66 | 94% | 70% | 35% | 11% |
| one room | 0.47 | 34% | 12% | 3% | 1% |

Models already disagree on the practical brief, and daydream pushes them further apart: 0.66 to
0.57 on best match, 81% to 98% distinct across the six lists. On the open brief there was
nothing shared to lose.

## With a state vs without, against the no-state baseline

The question this answers: is the distance a state produces bigger than the distance between
two plain lists? Keep the model and brief fixed; score each state's list against the plain list
from the same seed. Lower = further away. `floor.md`.

| model | no state (two lists) | walk | daydream | doomscroll |
|---|---|---|---|---|
| Opus 5.5 | 0.764 | 0.664 | 0.631 | 0.674 |
| DeepSeek v4.1 | 0.719 | 0.686 | 0.555 | 0.563 |
| MiniMax M3.1 | 0.677 | 0.657 | 0.617 | 0.647 |
| GPT-6.1 Sol | 0.735 | 0.711 | 0.675 | 0.700 |
| GPT-6.1 Terra | 0.725 | 0.718 | 0.687 | 0.710 |
| Qwen3.8 Max | 0.711 | no list | 0.645 | 0.704 |

Every daydream figure is lower than its model's no-state figure, by 0.05–0.17. Walk is lower on
five of six by a hair (0.011 on MiniMax, 0.007 on Terra). Doomscroll splits: 0.16 lower on
DeepSeek, 0.09 on Opus, but 0.007–0.02 on the GPT models, where it is barely distinguishable
from writing a second plain list.

## Limits

- Two lists per condition per model on the concept counts, four for the no-state baseline
  (Terra: one). Treat the direction as the finding, not the exact size.
- Nothing here says an idea is good. These numbers say the list moved and repeated itself less.
  Judging whether an idea is any use needs people, and no people have rated these.
- Qwen3.8 Max produced no walk list at all — the state turn happened and the list came back
  empty. Its walk row is a failure, not a zero.
- "Distinct concepts" is a clustering at 0.80 similarity, so two ideas that are the same move in
  different words count as two. It is a lower bound on repetition.
- Perplexity is scored by the same small model for every list, but different models write in
  different registers, so compare conditions rather than models on that column.
- Per-token probabilities exist only for the open-weight models here, so no measure built on
  them appears in this table. `report-lp-*.md` holds that for DeepSeek and Kimi.
