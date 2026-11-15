# Acceptance — one state, and a way to judge it

Every line is a command that was run on this tree.

## The cut

```
$ python -c "from core import states; print(list(states.STATES))"
['walk']

$ python -c "from core import sources; print(list(sources.PROVIDERS))"
['walk']
```

`/explore` is untouched: `tests/test_explore_state.py` and `tests/test_explore_api.py`
pass unchanged.

Nine test files were deleted because their subject no longer exists (the unstuck,
doomscroll-ledger, state-moves, goals, navigation, recommend, gap-fixes, mood and
hermes-integration suites). Three of those carried real coverage that is not about a
removed state, and it was restored rather than lost:

- `tests/test_walk_known_ledger.py` — a ledger that has seen everything must not
  stall the walk, and must steer it away from concepts it already holds.
- `tests/test_hermes_integration.py` — no hardcoded Hermes home, `HERMES_HOME` is
  resolved, no provider SDK in `core/`, and every routed task key is declared.

## Verdicts

```
$ POST /api/plugins/antemuse/verdict {"label":"via route","verdict":"trash"}
{"ok": true, "recorded": 1, "label": "via route", "verdict": "trash"}

$ GET /api/plugins/antemuse/verdicts
{"keep": 0, "trash": 1, "rate": 0.0}
```

A verdict is a `served` row whose `move` is `keep` or `trash`. There is no separate
verdict table; the subagent's first draft invented one, and `tools/hit_rate.py` now
counts through `core/history.verdicts()` so the pane's tally and the report cannot
disagree.

## The hit rate, on a real ledger

```
$ python -c "engine.note_verdict('refactoring','keep'); engine.note_verdict('zebra-tailed lizard','trash'); engine.note_verdict('gestalt','keep')"
{'ok': True, ...} ×3

$ python tools/hit_rate.py
hit rate: 2 kept, 1 trashed · 66.7%

$ python tools/hit_rate.py --json
{"keep": 2, "trash": 1, "rate": 0.6666666666666666, "since_days": 30}

$ python tools/hit_rate.py            # empty ledger
no verdicts recorded yet
```

## The pane

```
$ node --check desktop/plugin.js          # clean
$ pytest tests/test_cockpit_pane.py -q    # 20 passed
$ python tools/cockpit_harness.py         # 26/26 passed
```

Not verified in a real desktop window: the verdict buttons mounted in React. The
harness proves the canvas flight/shoot lifecycle and module loading; it does not
mount the controls or inspect their layout.

## The pane, in the packaged app

The harness cannot prove the controls work: it stubs the host. This was driven on
2026-11-14 in the real Electron window (`--remote-debugging-port`, Xvfb display :99),
with the working-tree `plugin.js` installed and the gateway serving the new tree.

The first live attempt found a real bug that no test could catch: `submit()` posted
with `win.fetch('/api/plugins/antemuse/verdict')`, and the pane runs on a `file://`
origin, so the call failed with `TypeError: Failed to fetch` and the controls recorded
nothing while still rendering. `picks` had the same defect and had never reached the
ledger. Both now use the host's `ctx.rest(path, {method, body})` — the door that
carries the session cookie — falling back to `fetch` only where no host door exists
(the harness).

After the fix, in the running app:

```
button: aria-label "keep maximum (K)", aria-keyshortcuts "K", 77x30 at (326,162)
click it      -> ledger: {'keep': 1, 'trash': 0, 'rate': 1.0}
press "t"     -> ledger: {'keep': 1, 'trash': 1, 'rate': 0.5}
pane tally    -> "kept 1 · dropped 1"
HUD           -> NEAR: maximum · PICK: 0 · EDGE: 1.49 · LIT: 0/1327
```

and the report reads the same rows:

```
$ python tools/hit_rate.py
hit rate: 1 kept, 1 trashed · 50.0%
```

Evidence: `.hermes/cache/scratch/verdict-live.png` (cockpit with the named reticle,
both controls, and the tally).

## Suite

```
$ env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
    uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q
804 passed, 1 skipped, 1 warning in 14.84s
```

Before the cut the suite was 952 passed. The difference is tests whose subject was
deleted, plus the nine files above.
