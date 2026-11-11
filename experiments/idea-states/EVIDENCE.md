# Evidence, and what is not here

`BENCHMARK.md` is the report. This directory publishes what backs it:

- `BENCHMARK.md`, `concepts.md`, `floor.md`, `overlap.md`, `percent.md`, `math-*.md`,
  `master.md` — the counts, in prose and tables.
- `aggregate-<model>.json` — every number the report cites, per model, per condition,
  extracted verbatim from the run's own `stats.aggregate`.
- `concepts.py`, `floor.py`, `intrinsic.py`, `effects.py` — the measurement code, so the
  counts can be recomputed.
- `*.png`, `index.html` — the same numbers as pictures.

Not in this tree: `results-*.json`, `variation-*.json`, `log-*.log`. Those hold the raw
model transcripts, including the states' own text, and they are published separately at
[roosiq/antemuse-evidence](https://github.com/roosiq/antemuse-evidence) with a sha256 for
every file. They are not here for two reasons: the catalog's install-time security scan
treats a transcript of a model role-playing a deception as a dangerous payload, and shipping
tens of megabytes of prompt text with a plugin that never reads it is waste. Nothing in the
report depends on reading them — the aggregates are copied from them mechanically, and the
separate repository is where a reader can check that.

To regenerate an aggregate from a run you still have locally:

```
python3 - <<'PY'
import json, glob, pathlib
for f in glob.glob("results-*.json"):
    d = json.load(open(f))
    agg = d.get("stats", {}).get("aggregate")
    if agg:
        pathlib.Path(f.replace("results-", "aggregate-")).write_text(json.dumps(
            {"model": d.get("model"), "seeds": d.get("seeds"),
             "conditions": list(agg), "aggregate": agg}, indent=1) + "\n")
PY
```

`results-lp-*.json` are partial provider runs with no aggregate block; they contributed no
numbers to the report and are absent here entirely.
