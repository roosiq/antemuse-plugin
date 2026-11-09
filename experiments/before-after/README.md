# Before / after — Antemuse material

A demonstration page, not a preregistered result.

## What it runs

Two development tasks (`evaluation/tasks/development.json`) × 3 seeds × 3 conditions,
through the plugin's own offline runner (`evaluation/run.py`), one model at a time:

| condition | what the model receives |
|---|---|
| A | the brief, as normal |
| B | the brief plus a matched-length "make it creative" instruction (placebo) |
| D | A plus the deterministic collider block from `deterministic_material()` |

A vs D shows whether the material changes the output. B exists so that a D gain cannot be
explained by simply asking for creativity. Same model, same token budget, one call per cell.

## Run

```bash
cd /home/ryan/antemuse-plugin
env -u PYTHONPATH -u VIRTUAL_ENV HF_HUB_OFFLINE=1 \
  /home/ryan/breadth/.venv/bin/python experiments/before-after/run.py            # local gufo
env -u PYTHONPATH -u VIRTUAL_ENV HF_HUB_OFFLINE=1 \
  /home/ryan/breadth/.venv/bin/python experiments/before-after/run.py \
    --model meituan/longcat-2.5:free                                             # Nous model
/home/ryan/breadth/.venv/bin/python experiments/before-after/render_html.py      # index.html
```

Cloud models run the same way; `--word-target` forces a length range on every condition so
verbosity cannot drive the result, and writes separate `-w130` files:

```bash
for m in deepseek/deepseek-v4.1-flash-1017 moonshotai/kimi-k3.1-pro \
         minimax/minimax-m3.1-flash qwen/qwen3.8-max-prime openai/gpt-6.1-terra; do
  /home/ryan/breadth/.venv/bin/python experiments/before-after/run.py --model "$m" --word-target 130
done
```

Generation cells are cached in `cache.jsonl` (the runner's own cache); judge verdicts in
`judge-cache.json`. Deleting either forces a rerun. A model never judges its own outputs;
the judge pool is beam-1.0, deepseek-v4.1-flash, and solar-mini4.

## Report

`index.html` is the page to show. `report.md` / `report-<model>.md` are the same content as text.

## Result (length-controlled, 130 words, 2 tasks × 3 seeds)

| model | D beats A | D beats B | diversity A → D |
|---|---|---|---|
| minimax/minimax-m3.1-flash | 9/10 | 11/11 | 0.524 → 0.564 |
| moonshotai/kimi-k3.1-pro | 9/9 | 5/6 | 0.462 → 0.534 |
| deepseek/deepseek-v4.1-flash | 8/9 | 6/8 | 0.574 → 0.489 |
| openai/gpt-6.1-terra | 3/5 | 3/8 | 0.499 → 0.538 |
| qwen/qwen3.8-max-prime | 5/9 | 4/10 | 0.542 → 0.433 |

Local Qwen3.8-Flash-Next loses under both settings (3/7 unconstrained). Material helps some
models, is neutral on qwen, and costs on gpt-6.1 and the local model.

## Limits

Six outputs per condition per model, development tasks, one judge pair per comparison.
Judges are order-controlled (both orders, consistent decisions only) but not human-validated.
This is a demonstration; the preregistered `experiments/state-settings/` remains the evidence path.
