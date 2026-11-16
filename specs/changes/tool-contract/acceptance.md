# Acceptance — the tool's contract

Every line here was run. The four inputs come from the live-app review that found them.

## The four inputs that used to lie

Run with an isolated `ANTEMUSE_STATES_HOME`:

```text
IN  state(action='enter', name='walk', walk='bogus')
OUT no such walk: 'bogus' · try: outer, wander, upward, downward, composite, vault, run3, orbit, lateral

IN  state(action='card')
OUT no such action: 'card'. try: enter, exit, status, list, walks, walk_new, walk_del, break,
    mood, spark, keep, complete, watch.

IN  state(action='enter', name='explore')
OUT explore is person-driven · the person types /explore

IN  state(action='list')
OUT AGENT STATE
      /walk       6 hops · all tools
                 work continues · the frame is elsewhere · different on return
      /return     end the current state and keep the residue

    PERSON-DRIVEN
      /explore    you fly the map yourself · no dose, no provider · ends on /return
```

Before the change the first answered `WALKING · 6 hops …` and wrote `walk: "bogus"` to the
active state; the second recommended `card` and `image`; the third entered the state; the
fourth named two verbs.

## Guards

`tests/test_tool_contract.py` — 8 tests, each one a sentence the tool used to get wrong:

- `test_entering_a_walk_that_does_not_exist_is_refused` — asserts the message **and** that
  `engine._load()["active"] == {}`. The old behaviour passed silently, so the message alone
  would not prove it.
- `test_a_real_walk_still_enters` — `walk='outer'` still enters and records `walk: outer`.
- `test_the_walk_resolver_refuses_an_unknown_name` — the fallback lived in `walks.get()`, not
  in the handler, so it is checked at that seam too, including `get("") == wander`.
- `test_every_action_the_tool_advertises_is_answered` — loops the `ACTIONS` tuple and fails if
  any of them answers `no such action`. `card` and `image` fail this test; that is the proof.
- `test_the_rejection_names_only_actions_that_exist` — parses the sentence, then calls every
  action it names.
- `test_the_agent_cannot_enter_the_person_driven_map`.
- `test_the_command_still_enters_the_person_driven_map` — the refusal belongs to the tool;
  `engine.enter("explore")` still answers `EXPLORING …`.
- `test_the_palette_names_the_three_verbs`.

Rewritten tests that encoded the defect rather than being loosened: `test_walks.py`'s two
fall-back-to-wander tests now assert a refusal, and the traversal test keeps its eleven hostile
names while allowing `""` to mean the default walk.

## Full checks

```text
pytest tests/                    812 passed, 1 skipped
tools/cockpit_harness.py         26/26 passed
node --check desktop/plugin.js   clean
```

## The pane, after

The live app was re-driven to confirm the change did not touch the cockpit: click `KEEP · K`,
the panel reads `kept 1 · dropped 0`, the ledger takes the row. The row was deleted afterwards,
so `tools/hit_rate.py` answers `no verdicts recorded yet` rather than a number a probe invented.

## Not verified here

The four strings above were produced by calling the plugin directly, not by a chat turn in the
packaged app: the gateway serving the app is still running the previous code, and reloading it
means restarting the process that carries this session. The pane half — verdict path, render,
tally — was re-driven live and is unchanged.
