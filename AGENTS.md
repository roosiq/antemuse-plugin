# Antemuse plugin — repository workspace

This repository **is** the Hermes plugin. Its root is the plugin root: `plugin.yaml`,
`__init__.py`, and `core/` sit at the top level, and Hermes loads it through the
symlink `~/.hermes/plugins/antemuse` → this directory.

It was extracted from `/home/ryan/antemuse` (formerly `antemuse/plugin/`) on
2026-11-08. The 22 commits that touched the plugin were carried across with
`git-filter-repo`, so history here is real history, not a fresh start. The site
repository `/home/ryan/antemuse` no longer contains the plugin and does not import it.

## What this code is

Two layers, deliberately separate:

- **States** (`core/states.py`, `core/engine.py`, `core/surfaces.py`) — walk,
  daydream, doomscroll, dream. Entry, exit, expiry, tool restoration and rendering
  are deterministic and must never require a model.
- **Exploration** (`core/collider.py`, `core/collision.py`, `core/orchestrator.py`,
  `core/runtime.py`) — a run takes a goal, selects far-domain sources, makes
  candidates, and hands them to the model. Every auxiliary call sits behind
  `experimental.enabled`.

The person and the model are different audiences by construction: the model receives
candidates, the person receives counts (`Run.account()`). No candidate text may reach
a human-facing surface, and the human card stays wordless.

## Rules that are not negotiable

- **No creative-improvement claim.** Runtime selection scores are not evidence.
- **Nothing is inferred on the entry/exit path.** If it needs a model, it does not
  belong in a state boundary.
- **Missing sources produce named failures, never invented material.**
- **A shard is immutable.** `evaluation/shards.py` freezes a task set, model set,
  conditions and versions under one id; a fixture that moves afterwards is caught by
  `verify()`, not silently accepted.
- **An incomplete grid is not a result.** `evaluation/aggregate.py` fails closed and
  names every missing cell.

## Commands

```bash
# tests — the exported PYTHONPATH breaks collection and PIL, so drop it
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with pillow --with nltk pytest tests/ -q

# the plugin loads as a package and registers its surfaces
hermes plugins doctor antemuse        # expect: 1 tool(s), 8 hook(s)

# the whole evidence pipeline, no network, seconds
env -u PYTHONPATH python3 tools/e2e.py

# the runtime path end to end: state → /spark → injection → feedback → return
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) python3 tools/walkthrough.py

# a pilot against a real endpoint (NOT evidence — writes to a temp dir)
env -u PYTHONPATH python3 tools/pilot.py --model <model> --seed 7
```

`ANTEMUSE_STATES_HOME` must always point at a temp directory during tests: the
plugin otherwise shares one state file with the live agent.

## Where the record lives

- `docs/spec.md` — the plugin contract. §13 holds the dated verification record;
  §15 the change log. Test counts live here and nowhere else.
- `specs/changes/<change>/` — per-change `spec.md` and `tasks.md` with delivery and
  review trails, including rejected reviews.
- `evaluation/` — conditions A–F, the task fixture, immutable shards, aggregation.
