# Interchangeable concept graphs — tasks

Change id: `interchangeable-graphs`
Source: `proposal.md`

Three phases, each independently verifiable. Phase 0 changes no behaviour; Phase 1 makes the existing
behaviour honest; Phase 2 proves interchangeability with a second real provider.

## Acceptance mapping

- [x] **AC1 — contract tests, both providers:** `tests/test_interchangeable_graphs.py`.
- [x] **AC2 — the nine built-ins are unchanged:** `tests/test_interchangeable_graphs.py`.
- [x] **AC3 — capability honesty is observable:** `tests/test_interchangeable_graphs.py`.
- [x] **AC4 — determinism:** `tests/test_interchangeable_graphs.py`.
- [x] **AC5 — provenance:** `tests/test_interchangeable_graphs.py`.
- [x] **AC6 — ids do not collide:** `tests/test_interchangeable_graphs.py`.
- [x] **AC7 — failure modes:** `tests/test_interchangeable_graphs.py`.
- [x] **AC8 — no regressions:** `tests/test_walks.py`, `tests/test_concept_graph.py`,
  `tests/test_walk_pane.py`, and `tests/test_manifest.py`.

Each item is **in progress (implementer)**; no acceptance criterion is verified by this bookkeeping
update.

## Phase 0 — the interface (no behaviour change)

- [x] **T1 · declare on the base class** — in progress (implementer). `Graph` gains `name`,
      `relations` (relation → role), `capabilities`; `WordNetGraph` declares `{general: hypernym,
      specific: hyponym, whole: holonym, part: meronym, lateral: similar/also/antonym}` and
      `{"far","resume","gloss","seeds"}`
      Accept: `python3 -c "from core.walks import GRAPHS; print(GRAPHS['wordnet']().capabilities)"`
- [x] **T2 · registry** — in progress (implementer): `graph` resolved through a registry; unknown name answers
      `unknown graph 'x' (known: …)`; `save()` rejects unknown graph and capability mismatch
      Accept: saving a walk with `"graph": "nope"` raises with that message
- [x] **T3 · namespaced ids** — in progress (implementer): node ids become `<graph>:<key>`; `resume()` strips its own prefix
      Accept: a WordNet hop id starts `wordnet:`; resuming an old unprefixed id still resolves
- [x] **T4 · provenance** — in progress (implementer): `source` and `licence` required on every node; WordNet reports
      Princeton WordNet 3.0
      Accept: every node from both providers carries both fields
- [x] **T5 · roles, not relation names** — in progress (implementer): the nine built-in walks express direction as roles;
      translation is compared against the current specs, not eyeballed
      Accept: `pytest tests/test_walks.py -q` and a comparison test asserting the nine specs are
      unchanged apart from `graph`/`relations`/`roles` spelling

## Phase 1 — honesty and determinism

- [x] **T6 · capability check at entry** — in progress (implementer): `far`, `vault`, `orbit`, `composite` on a provider without
      `far_from` fail at entry, naming the graph and the alternative
      Accept: a `vault` walk on `manual` answers `manual cannot jump · use wander`; no step is served
- [x] **T7 · seeded RNG** — in progress (implementer): `ANTEMUSE_GRAPH_SEED` swaps `SystemRandom` for a seeded `random.Random`
      Accept: the same cursor and seed replay the same six hops twice; unset, the paths differ
- [x] **T8 · named failure modes** — in progress (implementer): `unavailable`, `empty`, `too_large`, `no_far`, each in the
      state's own voice, none raising into a turn
      Accept: a test per mode, including nltk data hidden
- [x] **T9 · seeds from roles** — in progress (implementer): `random_node(roles)` returns a node with at least one usable edge or
      `None` with a reason; `SEEDS` becomes WordNet's own data
      Accept: manual and corpus providers never start on a node with no edges

## Phase 2 — the corpus provider

- [x] **T10 · load a corpus graph** — in progress (implementer): `$ANTEMUSE_STATES_HOME/graphs/<name>.json` with nodes, edges,
      source, licence; lazy load; over-cap rejected with a message, never truncated
      Accept: a two-node corpus graph walks; a 500k-node one is rejected as `too_large`
- [x] **T11 · contract tests over both** — in progress (implementer): one module, run over `wordnet` and `corpus`, plus a stub
      provider so the tests are not shaped around WordNet
      Accept: `pytest -q` green; the stub fails when the interface is violated
- [x] **T12 · docs** — in progress (implementer): `specs/product/states.md` walk clause names the graph and what it implies for
      the path's meaning; README stops implying WordNet is the only graph
      Accept: `pytest tests/test_docs_current.py -q`; the README's walk paragraph is edited, not
      appended

## Out of scope for this change

- Remote graphs, runtime embeddings, graph editing, ontology import, third-party provider loading.
- Any change to the ledger graph, `/graph`, the pane, or state semantics.
