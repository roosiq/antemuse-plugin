# Spec change: consolidate-naming

Status: implemented
Kind: internal restructuring. No change to state semantics, hooks, commands,
tool schema, or rendered output.

## Goal

The plugin's internals still carry the names of concepts it has since dropped.
A stranger opening the repo should be able to name every module by what it does.

- The package was `core/`'s predecessor, named after a minigame that no longer
  exists; its `__init__.py` docstring still called the modules by that minigame's
  name.
- `store.py` is half dead: the `sparks`/`services` SQLite board, leaderboard,
  and round bookkeeping are minigame leftovers with no caller.
- `definitions.py` names a file after its verb, not its content.
- `atlas.py` and `three_backdrop.py` name files after a metaphor and an
  implementation detail respectively.
- `image.py` and `realimagery.py` both implement a Bayer dissolve, both build
  ANSI half-block rows, and both crop-to-cell-aspect. Two cell models
  (`(r,g,b)` and `((r,g,b),(r,g,b))`) for one idea.
- `data_dir()` still honours two retired environment aliases from earlier names.

## Non-goals

- No behaviour change. Same states, same policy, same clock, same journal,
  same commands, same tool schema.
- No new features. `scenes-per-surface` stays unimplemented and its task list
  keeps its own scope.
- No change to the on-disk layout under the plugin data dir.

## Requirements

**R1 — one package, named for what it holds.**
`core/` becomes `core/`. Every import inside the plugin and its tests uses
`core`, with the flat-module fallback preserved for the plugin loader.

**R2 — modules named by content.**
`definitions.py` → `states.py`; `store.py` → `storage.py`; `atlas.py` →
`walk_map.py`; `three_backdrop.py` → `backdrop.py`; `realimagery.py` +
`image.py` → `photographs.py`.

**R3 — one terminal-imaging module.**
`photographs.py` owns the cell model `(top, bottom)`, the Bayer matrix, the
dissolve, the ANSI row encoder (with glyph overlay), the crop-to-cell-aspect
loader, frame discovery per state, motion (drift + dissolve), and the still
frame. No second copy of any of these exists in the package.

**R4 — dead code removed.**
`storage.py` keeps `data_dir`, `load_active`, `save_active` only. The SQLite
board, sparks, services, leaderboard, and round bookkeeping are deleted, as are
the retired environment aliases from earlier names.

**R5 — no stale identity.**
`__version__` matches `plugin.yaml`. Registered skill name matches the plugin
name. `__main__.py` does not name a retired module path. `bin/` resolves the
repo relative to itself rather than a hardcoded path outside it.

## Affected paths

- `core/` (was `core/`), every module listed in R2
- `__init__.py`, `__main__.py`, `bin/`, `.gitignore`, `plugin.yaml`, `README.md`,
  `SKILL.md`, `docs/brand.md`
- `tests/` — imports and the two renamed test modules

## Verification

- `env -u PYTHONPATH NLTK_DATA=~/nltk_data ANTEMUSE_STATES_HOME=<tmp> pytest tests/ -q`
- `hermes plugins doctor ~/antemuse/plugin`
- one real CLI run of the panel plus one tool call (`state(action="status")`)
- `grep -rni` for the retired package name, `realimagery`, `three_backdrop`,
  `record_spark`, `leaderboard` over
  Python outside `docs/brand.md` and `specs/` returns nothing

## Must not change

- The `state` tool schema and its actions.
- The five state definitions, their budgets, directives, and contracts.
- The hook set: `pre_llm_call`, `pre_tool_call`, `transform_llm_output`.
- Files written under the data dir: `active.json`, `real/<state>/*.png`,
  `three_frames/`, `walks/`, `scene.json`.
