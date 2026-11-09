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

## Measures

- **ideas / 50** parsed out of the reply; cells that end mid-sentence are flagged truncated
- **mean pairwise** embedding distance across the list (how spread out the ideas are)
- **distinctiveness** mean distance to the nearest idea from the other conditions on the
  same brief (does the state move the list off the straight answer)
- **novelty / usefulness** blind sample of six ideas per cell, three judges, never the model
  under test

## Run

```bash
cd /home/ryan/antemuse-plugin
env -u PYTHONPATH -u VIRTUAL_ENV HF_HUB_OFFLINE=1 \\
  /home/ryan/breadth/.venv/bin/python experiments/idea-states/run.py \\
    --model deepseek/deepseek-v4.1-flash-1017 --seeds 11 12
env -u PYTHONPATH -u VIRTUAL_ENV /home/ryan/breadth/.venv/bin/python experiments/idea-states/render_html.py
```

`--rejudge` re-runs only the judged sample against stored cells.

## Limits

Four cells per condition per model. Judges are order-free but not human-validated, and a
six-idea sample of fifty is noisy by construction. Treat direction, not magnitude.
