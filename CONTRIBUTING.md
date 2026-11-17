# Contributing

Antemuse is a Hermes plugin. The repository root is the plugin root: `plugin.yaml`,
`__init__.py`, `core/`, and `desktop/plugin.js` are loaded through
`~/.hermes/plugins/antemuse`.

## Public contract

`__init__.py` registers exactly seven public commands:

- `/walk [walk]` enters the `walk` agent state.
- `/daydream` enters the `daydream` agent state.
- `/doomscroll` enters the `doomscroll` agent state.
- `/dream` enters the `dream` agent state.
- `/unstuck` enters the `unstuck` agent state.
- `/explore` opens the person-driven concept-map mode.
- `/return` ends the current state or exploration.

`core/states.py` keeps the five agent states (`walk`, `daydream`, `doomscroll`,
`dream`, and `unstuck`). The single plugin tool is `state(action=...)`; the desktop
pane has a map and a cockpit tab. Do not add commands or state names without changing
this contract and its tests.

No model call belongs on the state entry, exit, delivery, or rendering path. Tests
should name observable behavior and keep plugin data under `ANTEMUSE_STATES_HOME`.

## Run tests

```bash
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q
```

## Changes and pull requests

1. Add or update the focused test with the behavior change.
2. Run the full suite and include the command and result in the pull request.
3. Refresh `docs/screenshots/` when a pane changes.
4. Do not commit generated caches, local plugin data, or credentials.

`./scripts/release.sh <version>` updates release metadata and builds the validated
tarball. The catalog pin is a commit SHA; do not hand-edit its generated entry.

## Licence

Contributions are accepted under the MIT licence in `LICENSE`.
