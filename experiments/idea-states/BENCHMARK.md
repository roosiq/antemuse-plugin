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
- **Perplexity.** How surprising the list is to a small fixed language model. Higher means
  less ordinary phrasing.
- **Word variety.** The share of distinct words in the list. Lower means the model reuses more
  of the same words.

Ideas written is a plain count. Percentages compare each list with the same model's plain list
for the same brief and seed, and are medians over those comparisons. `math-*.md` has the
differences with their ranges.

## The numbers

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
3. **Higher perplexity is not different ideas.** MiniMax's daydream raises perplexity more
   than any other case (+49%) while the ideas themselves barely move (+9%). GPT-6.1 Terra's
   doomscroll is +36% perplexity and +7% different ideas.
4. **Word variety is what it costs.** DeepSeek buys its 37% move with 16% less word variety —
   rarer words, fewer of them. Opus and Sol move without that cost.
5. **Doomscroll ignores the count.** DeepSeek and MiniMax wrote 63 ideas instead of 50. Opus
   and the GPT models stuck to 50.
6. **walk is the weak state.** On four of six models the list stays within 6% of the plain one,
   and on MiniMax it goes slightly backwards. Only Opus moves clearly (+18%).

## Do different models write the same ideas?

Same brief, same seed, the six lists side by side. Two ideas count as the same when their
embedding similarity clears 0.80. `overlap.md` has the full per-pair matrices.

| brief | condition | overlap between models | average best match | distinct ideas in the pooled set |
|---|---|---|---|---|
| food waste | no state | 11% | 0.66 | 243 of 300 (81%) |
| food waste | walk | 6% | 0.64 | 228 of 253 (90%) |
| food waste | daydream | 1% | 0.57 | 293 of 300 (98%) |
| food waste | doomscroll | 5% | 0.63 | 275 of 302 (91%) |
| one room | no state | 1% | 0.47 | 295 of 300 (98%) |
| one room | walk | 0% | 0.45 | 232 of 234 (99%) |
| one room | daydream | 0% | 0.47 | 250 of 250 (100%) |
| one room | doomscroll | 0% | 0.43 | 300 of 301 (100%) |

The level depends on the threshold, so it is worth seeing the same six lists through different
ones — no state, seed 11:

| brief | avg best match | 0.50 | 0.60 | 0.70 | 0.80 |
|---|---|---|---|---|---|
| food waste | 0.66 | 94% | 70% | 35% | 11% |
| one room | 0.47 | 34% | 12% | 3% | 1% |

Two things follow. Models already disagree on the practical brief — only about one idea in nine
is a near-copy across models, and 19% of the pooled list is redundant. Daydream cuts what
agreement there was roughly in half (0.66 to 0.57 on best match; 70% to 40% at the 0.60
threshold). And on the open creative brief there was almost nothing shared to begin with: the
lists are 98–100% distinct whether a state is used or not.

Caveat, and the next section covers it: twin-share at 0.80 turns out to be noisy — a model
reproduces only 18% of its own ideas when asked twice. The sturdier figure is the average best
match: 0.66 between models with no state, 0.57 after daydream, against 0.69 when re-asking the
same model. Read the overlap direction as real for daydream on best match, and as directional
only for the twin percentages.

So the state is not making models converge on a canon of ideas. It pushes each model further
into its own corner.
## How much does a straight list vary on its own?

No state at all: same brief, 100 ideas, asked four times per model. This is the floor
anything else has to clear — if re-asking moves the list as much as a state does, the state
effect is not separable from sampling. `variation.md`, seed-free, files `variation-*.json`.

| model | twin ideas when asked again | avg best match | distinct ideas in the pooled 400 |
|---|---|---|---|
| DeepSeek v4.1 | 14% | 0.68 | 339 (85%) |
| Qwen3.8 Max | 15% | 0.69 | 330 (82%) |
| MiniMax M3.1 | 6% | 0.66 | 372 (93%) |
| GPT-6.1 Terra | 20% | 0.70 | 315 (79%) |
| GPT-6.1 Sol | 25% | 0.72 | 299 (75%) |
| Opus 5.5 | 28% | 0.72 | 287 (72%) |

- Average: **18% of ideas are near-copies when the same model is asked again**, best match 0.69.
- Across every pair of lists, best match never fell below **0.64** (mean 0.69, sd 0.02).
- Different models, one list each: **8% twins**, best match 0.65.
- Every model delivered exactly the 100 ideas asked for.

This sets the bar. The straight lists agree with themselves only about 18% of the time at
0.80, so a state that shifts twin-share from 11% to 1% is changing something smaller than the
model's own run-to-run wobble. Best match is the stable measure: re-asking stays at 0.69 and
never drops below 0.64, while daydream drops the cross-model figure to 0.57 — below anything
re-asking ever produced. So the daydream divergence holds; the twin percentages do not carry
that weight on their own.

Two consequences for the rest of this document:

1. Any claim resting on twin-share (11% → 1%) is inside the noise floor. Restate those as best
   match, or treat them as directional only.
2. The state comparisons were made with 50-idea lists. Re-asking four 50-idea lists would give
   a slightly higher twin-share than four 100-idea lists, since shorter lists have fewer
   chances to diverge — the 18% here is a conservative floor, not an exact match.

## Limits

- Four lists per condition per model (Terra: two), over two briefs. Treat the direction as the
  finding, not the exact size.
- Nothing here says an idea is good. These numbers say the list moved, and what that cost in
  words. Judging whether an idea is any use needs people, and no people have rated these.
- Qwen3.8 Max produced no walk list at all — the state turn happened and the list came back
  empty. Its walk row is a failure, not a zero.
- Perplexity is scored by the same small model for every list, but different models write in
  different registers, so compare conditions rather than models on that column.
- Per-token probabilities are only available from the open-weight models here, so no measure
  built on them appears in this table. `report-lp-*.md` holds that for DeepSeek and Kimi.
