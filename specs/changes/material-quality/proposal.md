# Material quality, and a dose paced by the person

## Why

Driving the real desktop app produced this, from `/walk` with no arguments:

```
idea → zebra-tailed lizard → Hydra → brown creeper
```

Every hop is a `far` jump sampled uniformly from `wordnet.words()`. `far_from()`
picks the candidate with the *lowest* path similarity, so a jump is guaranteed to
land on a word unrelated to the one before it. "Different on return" became
"random on return". The walk's own docstring says *distance is the walk's goal,
distance without a path back is noise* — the code contradicted it.

The same run also showed `walk 'outer' failed · …` sitting in the trail as if it
were material, and a status chip reading `WALKING · 6/6 HOPS` before the person
had typed anything: pane polls had spent the entire dose in the background.

## What changes

1. **A jump is the outer rim of the connected neighbourhood, not a random word.**
   `far_from` searches outward from the current node by breadth-first over the
   walk's own relations, collects nodes at depth ≥ 2 (bounded by a budget),
   and picks the farthest of those by path similarity. Candidates are connected
   by construction, so a hop can always be explained and always has a way back.

2. **A walk that raises is a failure, not material.** `walk_text` retries once
   from a fresh start, then returns nothing and records health. No exception text
   reaches the transcript as if a person should read it.

3. **A pane poll may show, it may not spend.** `deliver_if_due(source="pane")`
   may not take `served` above `turns + 1` for the owning session. The first hop
   appears on entry; each further hop waits for a turn. The chip therefore reads
   what the person has actually done, and a state cannot complete itself while
   nobody is talking.

## Non-goals

- No state-surface change in this historical proposal; the product now has one agent state.
  after the material is worth having.
- Not touching the cockpit HUD, its flight model, or `/graph`.
- Not changing the ending vocabulary (`complete`/`returned`/`dry`/`failed`).
- No change to the surviving walk material or person-driven explore mode.

## Acceptance

- For a three-step `outer` walk, every hop's two ends are reachable from one
  another within two relation steps of the graph.
- No hop in a walk has a path similarity of exactly `0.0` to the node it left,
  unless the graph has nothing else to offer (logged, not silent).
- A provider that raises produces zero material and one health record.
- With the pane polling repeatedly and no turn, `served` stays at 1; one turn
  and one poll moves it to 2.
- The suite passes, and `docs/EXAMPLES.md` regenerates with recognisable hops.

## Affected paths

- `core/walks.py` — `WordNetGraph.far_from`, `Walk.step` jump policies.
- `core/sources.py` — `walk_text` failure handling.
- `core/engine.py` — `deliver_if_due(source=…)`.
- `dashboard/plugin_api.py` — pane poll passes `source="pane"`.
- `tests/test_walk_material.py`, `tests/test_state_delivery.py`.
- `specs/changes/material-quality/`, `CHANGELOG.md`.
