# Tasks — material quality

- [x] T1 `WordNetGraph.rim()` — breadth-first out to depth 2, node budget 400.
- [x] T2 `far_from()` picks from the rim, never a direct neighbour, never a
      random dictionary word; prefers hops whose gloss does not restate the
      one being left.
- [x] T3 `Walk.step` keeps every visited node out of the far search, so a jump
      cannot land where the walk already stood.
- [x] T4 `walk_text()` retries from a fresh start on a raised walk, records
      health, and returns no material — a traceback is not a hop.
- [x] T5 `deliver_if_due(source=...)`; a pane poll stops at `turns + 1`.
- [x] T6 `dashboard/plugin_api.py` polls with `source="pane"`.
- [x] T7 Guards: `tests/test_walk_material.py` (7 tests).
- [x] T7b `WordNetGraph.edges()` reports no edges for an id that is not a synset,
      instead of raising through the walk.
- [x] T8 Regenerate `docs/EXAMPLES.md` and read the hops that come out
      (`design → creating by mental acts → programming → logic programming`,
      6,833 chars).
- [x] T9 Update `CHANGELOG.md`, and the walk paragraph in `specs/product/states.md`
      if the jump description changed.
- [x] T10 Full suite green: **952 passed, 1 skipped** (was 945); README's
      measured jump/step numbers replaced with the ones measured after the change.
- [x] T11 Driven in the running app after the gateway restart: typed `/walk`,
      then one message. `served 3, turns 1, dose 6`; hops
      `finback → mammal genus → Balaenoptera`, no traceback in the path.
      Found and fixed two things the run exposed: a five-day-old cursor was
      resumed instead of seeding fresh (`start_node()` now drops a cursor older
      than twelve hours), and the chip reads `0/6` at entry when no pane is
      polling — correct pacing, but the entry copy should say so (follow-up).

## Follow-ups this change does not do

- Cut to one state, or rebalance the six.
- Cockpit: clicking a node should say what it is and why it lit.
- Publish a keep/trash hit rate from the ledger. **Blocked on a decision, not on
  code:** nothing in the states layer records a keep or a trash verdict today
  (`loved`/`liked` live in the creative-retrieval collider, not here), so a hit
  rate would mean inventing the verdict surface first.
