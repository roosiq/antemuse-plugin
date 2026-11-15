# Acceptance — material quality

Evidence, not intentions. Every line below is a command that was run.

## A jump is connected

`/walk` from `design` before this change:

```
design (n) → zoo (n) / idea → zebra-tailed lizard → Hydra → brown creeper
```

After:

```
design (n) → realization (n) · "making real or giving the appearance of reality"
realization (n) → formation (n) · "creation by mental activity"
formation (n) → verbal creation (n) · "creating something by the use of speech"
verbal creation (n) → composing (n) · "musical creation"
```

`memory` after: `memory → image → stereotype → content → meaning`.
`idea` after: `idea → semantics → meaning → plan → guidance`.

Command: `python -c "... walks.GraphWalk(...).step(5)"` with a cursor pinned to
the seed. Guarded by `test_a_far_hop_is_two_steps_out_and_never_a_neighbour`
(12/12 jumps reachable in two edges, 0 neighbours) and
`test_a_walk_never_lands_where_it_has_already_stood`.

## A jump is still a jump

`test_an_outer_hop_is_a_jump_but_never_an_unrelated_word`: mean similarity of
jumps < mean similarity of the node's own edges, and at most 1 of 20 jumps is
`0.0` (WordNet's "no path at all").

## A broken walk is not material

`test_a_walk_that_raises_serves_no_material`: a walk whose `step()` raises
returns `[]`, records one health row, and never puts an exception in the
transcript. Before this change the same failure appeared as
`walk 'outer' failed · …` in the trail of a live walk.

## The pane cannot outrun the person

`test_a_burst_of_polls_cannot_outrun_the_person`: four polls leave `served` at
1; one turn plus one poll moves it to 2; six more polls leave it at 2.

Before: four polls served four hops and a six-hop walk read `6/6` before the
first message — observed in the running desktop app on 2026-11-14, in the
screenshot the audit kept as `app10.png`.

## The live app, now on the new build

After the gateway restart, in the running desktop app (typed `/walk`, then one
message), the state record read:

```
active: {key: walk, walk: outer, served: 3, turns: 1, dose: 6}
journal: finback (n) → mammal genus (n) · took its far edge · "a genus of mammals"
         finback (n) → Balaenoptera (n) · took its far edge · "type genus of the Balaenopteridae"
         mammal genus (n) → genus (n) · … "(biology) taxonomic group containing one or more species"
```

What that shows: **no traceback in the path**, a hop that is a real conceptual
step rather than a random dictionary word, and `served` tracking turns instead
of hitting six on entry. Two things it also showed, both now fixed:

- the walk resumed from a **five-day-old cursor** (`finback`), so it set out from
  leftover WordNet space rather than from the work in front of the person —
  `start_node()` now ignores a cursor older than twelve hours and seeds afresh;
- entering `/walk` serves nothing until a turn or an open pane asks, so the chip
  reads `0/6` at entry when no pane is polling. That is the pacing rule working,
  but it is worth a line of copy in the entry message.

The same run against the previous build is recorded below, for contrast:

```
active: {key: walk, walk: outer, served: 6, turns: None, dose: 6}
journal: walk 'outer' failed · 'NoneType' object has no attribute '_hypernyms'
```

Both defects that change removes, seen live: a traceback as the first item of
the path, and six units spent with no turn taken. That failure also named a
third defect, fixed and guarded: `WordNetGraph.edges()` raised when a cursor
held a label where a synset id belongs, instead of reporting no edges.

## Suite

`env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) uvx --with-requirements
requirements-test.txt --quiet pytest tests/ -q`
→ see `tasks.md` T10 for the recorded count.
