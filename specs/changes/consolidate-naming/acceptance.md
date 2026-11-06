# Acceptance: consolidate-naming

Evidence recorded against the criteria in `spec.md`.

## R1 — one package, named for what it holds

`git mv kitchen core`; no `kitchen/` remains. Imports:

```
core/__init__.py        docstring lists every module by what it does
__init__.py             from .core import engine, panel, states, surfaces, tui, walks
__main__.py             from core import tui
tests/*.py              from core import ...
```

The flat-module fallback (`from core import ...`) is kept for the plugin loader.

## R2 — modules named by content

```
definitions.py     -> states.py
store.py           -> storage.py
atlas.py           -> walk_map.py
three_backdrop.py  -> backdrop.py
realimagery.py     -> photographs.py
image.py           -> folded into photographs.py (deleted)
tests/test_image.py     -> tests/test_photographs.py
tests/test_atlas.py     -> tests/test_walk_map.py
```

`grep -rn "kitchen\|realimagery\|three_backdrop\|record_spark\|leaderboard"`
over Python/Markdown/YAML (excluding `specs/` and the retired-name list in
`docs/brand.md`) returns one hit: an image prompt in `tools/gen_frames.py` that
describes a photograph of a domestic table, which is content, not naming.

## R3 — one terminal-imaging module

One `Cell` type — `(top, bottom)` pixels — with a single `BAYER8`, `blend`,
`to_rows` (glyph overlay included), `load`, `_crop`, `cells`, `solid`, frame
discovery, drift + dissolve motion, and `still`. `image.py` is gone; the two
duplicate dissolves and the two row encoders are one each.

## R4 — dead code removed

`storage.py` is 58 lines (was 152): `data_dir`, `load_active`, `save_active`.
The SQLite board (`sparks`, `services`, `record_spark`, `close_service`,
`leaderboard`, `table_titles`, `table_for_service`) and the
`ANTEMUSE_ROOM_HOME` / `ANTEMUSE_KITCHEN_HOME` aliases are deleted.

## R5 — no stale identity

- `plugin.yaml` 0.9.0 == `__init__.__version__`; asserted by
  `tests/test_manifest.py`.
- Skill registers as `antemuse`; `SKILL.md` frontmatter `name: antemuse`.
- `__main__.py` no longer names `antemuse_states` and derives its path from
  `__file__`.
- `bin/hermes-states` → `bin/antemuse`, resolving the repo from the script's own
  location instead of `~/antemuse-states`.

## Verification

```
$ env -u PYTHONPATH NLTK_DATA=~/nltk_data ANTEMUSE_STATES_HOME=<tmp> \
    uvx --with pillow --with nltk --quiet pytest tests/ -q
74 passed in 5.65s

$ hermes plugins doctor ~/antemuse-plugin
  manifest: antemuse 0.9.0 (standalone)
  OK: runtime discovery, manifest parsing, import, and registration passed
  registrations: 1 tool(s), 3 hook(s)

$ # real state cycle, throwaway home
enter walk -> WALKING · 1 min · 4 turn(s) · concept to concept · no destination
record + tick -> panel renders both columns
stop -> WALKING ended · walk 1m · 1 step(s) · salt to brine, the path narrows
status -> not in a state. residue: walk 1m · 1 step(s) · ...

$ # live photographs, read only
counts: {'walk': 6, 'daydream': 6, 'dream': 6, 'doomscroll': 6}
imagery_frame(60x12, t=30s): 12 rows, truecolor present
```

Installed plugin is a symlink to this repo (`~/.hermes/plugins/antemuse ->
/home/ryan/antemuse-plugin`), so the live agent picked the change up with no copy
step.
