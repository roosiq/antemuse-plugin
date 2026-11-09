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

Generation cells are cached in `cache.jsonl` (the runner's own cache); judge verdicts in
`judge-cache.json`. Deleting either forces a rerun.

## Report

`index.html` is the page to show. `report.md` / `report-<model>.md` are the same content as text.

## Limits

Six outputs per condition per model, development tasks, one judge pair per comparison.
Judges are order-controlled (both orders, consistent decisions only) but not human-validated.
This is a demonstration; the preregistered `experiments/state-settings/` remains the evidence path.
