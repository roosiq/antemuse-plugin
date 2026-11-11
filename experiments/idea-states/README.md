# 50 ideas, twice — with a state in the middle

Ryan's question in experiment form: ask a model for 50 ideas, then ask it again with a
walk, daydream or doomscroll between the brief and the list. Does the list change?

## Design

Two briefs (city food waste; a two-minute one-room short film), 2 seeds, 4 conditions:

| condition | what happens |
|---|---|
| N | one call: brief → 50 ideas |
| walk | turn 1 holds the brief in the walk state, turn 2 writes the list |
| daydream | same, in the daydream state |
| doomscroll | same, in the doomscroll state, with three real feed items from `core.sources.feed_pick` |

State directives are read from `core/states.py`, not rewritten, so this measures shipped
behaviour. The state turn is instructed not to list ideas; the return prompt carries what
the state produced.

## Measures — deterministic only

There is no LLM judge anywhere in this experiment. Every number is a function of the text
plus a fixed embedding model or a fixed language model, so it reproduces exactly.

| measure | what it means | source |
|---|---|---|
| ideas / 50 | how many ideas the reply actually contains | parsing |
| mean pairwise | spread of the list (mean cosine distance between ideas) | MiniLM embeddings |
| distinctiveness | distance from the straight answer on the same brief | MiniLM embeddings |
| perplexity | how predictable the wording is, per token | Qwen3-0.6B |
| TTR / MTLD | vocabulary spread and length-robust vocabulary richness | counts |
| distinct-2 / hapax | phrase variety and share of one-off words | counts |
| compression | repetition proxy (zlib ratio) | counts |
| self NLL | surprise per token under the model's own logprobs | generation |

`percent.py` turns these into paired percent changes against the same model's straight
answer for the same brief and seed.

Perplexity is a predictability measure, not a quality measure. Nothing here says an idea is
good; it says the text shifted, and how.

## Run

```bash
cd /home/ryan/antemuse-plugin
env -u PYTHONPATH -u VIRTUAL_ENV HF_HUB_OFFLINE=1 \
  /home/ryan/breadth/.venv/bin/python experiments/idea-states/run.py \
    --model deepseek/deepseek-v4.1-flash-1017 --seeds 11 12
# deterministic measures on stored cells (no new generations, no API calls)
env -u PYTHONPATH -u VIRTUAL_ENV HF_HUB_OFFLINE=1 \
  /home/ryan/breadth/.venv/bin/python experiments/idea-states/run.py \
    --model deepseek/deepseek-v4.1-flash-1017 --seeds 11 12 --reuse --intrinsic
# self-perplexity from the model's own logprobs (regenerates the lists)
env -u PYTHONPATH -u VIRTUAL_ENV HF_HUB_OFFLINE=1 \
  /home/ryan/breadth/.venv/bin/python experiments/idea-states/logprobs.py \
    --model moonshotai/kimi-k3.1-pro --seeds 11
env -u PYTHONPATH -u VIRTUAL_ENV /home/ryan/breadth/.venv/bin/python experiments/idea-states/percent.py
env -u PYTHONPATH -u VIRTUAL_ENV /home/ryan/breadth/.venv/bin/python experiments/idea-states/render_html.py
```

## Limits

Two cells per condition per model per brief. Percent changes are medians over blocks, so
they carry spread; `math-*.md` gives the paired deltas with intervals and permutation
p-values. Perplexity is not comparable across models — each model is normalised by itself.
Self NLL from served logprobs looks near-greedy, so use it as a relative signal only.
