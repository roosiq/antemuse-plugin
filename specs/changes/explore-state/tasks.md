# Tasks

- [x] `core/states.py`: the `explore` spec — label, `dose {picks, 0}`, `turns 0`,
      directive, contract, residue.
- [x] `core/engine.py`: `note_pick()` — counts per concept, ignores everything unless an
      explore is active; `_account()` returns the tally for an explore.
- [x] `core/engine.py`: `_expire` / `complete_if_dosed` / `note_turn` refuse to close a
      state with no dose (a dry turn is normal when a person is flying).
- [x] `core/engine.py`: an open-ended close names the picks instead of asking the agent to
      summarise a trip it did not take.
- [x] `core/sources.py`: `PROVIDERS["explore"] = None` — nothing to search for.
- [x] `dashboard/plugin_api.py`: `POST /picks`, 400 on a non-list body.
- [x] `desktop/plugin.js`: `counts()` says "N picked · you end it" for a dose-less state;
      the cockpit posts only the delta of what it hit, debounced, and flushes on destroy.
- [x] `__init__.py`: schema text lists explore; command hint no longer promises minutes.
- [x] Tests: `tests/test_explore_state.py`, `tests/test_hook_resilience.py`.
- [x] `SKILL.md`, `README.md`, catalog description, CHANGELOG.

## Verification

```
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q
/usr/bin/python3 tools/cockpit_harness.py
```

## Must not change

- The six existing states' doses, tools, directives, or endings.
- The single `/graph` route and the pane's theme-variable discipline.
- Nothing is committed or released by this change.
