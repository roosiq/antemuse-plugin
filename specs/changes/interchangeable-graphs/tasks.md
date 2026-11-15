# Interchangeable concept graphs — tasks

Change id: `interchangeable-graphs`
Source: `proposal.md`

Three phases, each independently verifiable. Phase 0 changes no behaviour; Phase 1 makes the existing
behaviour honest; Phase 2 proves interchangeability with a second real provider.

## Phase 0 — the interface (no behaviour change)

- [ ] **T1 · declare on the base class** — `Graph` gains `name`, `relations` (relation → role),
      `capabilities`; `WordNetGraph` declares `{general: hypernym, specific: hyponym, whole: holonym,
      part: meronym, lateral: similar/also/antonym}` and `{"far","resume","gloss","seeds"}`
      Accept: `python3 -c "from core.walks import GRAPHS; print(GRAPHS['wordnet']().capabilities)"`
- [ ] **T2 · registry** — `graph` resolved through a registry; unknown name answers
      `unknown graph 'x' (known: …)`; `save()` rejects unknown graph and capability mismatch
      Accept: saving a walk with `"graph": "nope"` raises with that message
- [ ] **T3 · namespaced ids** — node ids become `<graph>:<key>`; `resume()` strips its own prefix
      Accept: a WordNet hop id starts `wordnet:`; resuming an old unprefixed id still resolves
- [ ] **T4 · provenance** — `source` and `licence` required on every node; WordNet reports
      Princeton WordNet 3.0
      Accept: every node from both providers carries both fields
- [ ] **T5 · roles, not relation names** — the nine built-in walks express direction as roles;
      translation is compared against the current specs, not eyeballed
      Accept: `pytest tests/test_walks.py -q` and a comparison test asserting the nine specs are
      unchanged apart from `graph`/`relations`/`roles` spelling

## Phase 1 — honesty and determinism

- [ ] **T6 · capability check at entry** — `far`, `vault`, `orbit`, `composite` on a provider without
      `far_from` fail at entry, naming the graph and the alternative
      Accept: a `vault` walk on `manual` answers `manual cannot jump · use wander`; no step is served
- [ ] **T7 · seeded RNG** — `ANTEMUSE_GRAPH_SEED` swaps `SystemRandom` for a seeded `random.Random`
      Accept: the same cursor and seed replay the same six hops twice; unset, the paths differ
- [ ] **T8 · named failure modes** — `unavailable`, `empty`, `too_large`, `no_far`, each in the
      state's own voice, none raising into a turn
      Accept: a test per mode, including nltk data hidden
- [ ] **T9 · seeds from roles** — `random_node(roles)` returns a node with at least one usable edge or
      `None` with a reason; `SEEDS` becomes WordNet's own data
      Accept: manual and corpus providers never start on a node with no edges

## Phase 2 — the corpus provider

- [ ] **T10 · load a corpus graph** — `$ANTEMUSE_STATES_HOME/graphs/<name>.json` with nodes, edges,
      source, licence; lazy load; over-cap rejected with a message, never truncated
      Accept: a two-node corpus graph walks; a 500k-node one is rejected as `too_large`
- [ ] **T11 · contract tests over both** — one module, run over `wordnet` and `corpus`, plus a stub
      provider so the tests are not shaped around WordNet
      Accept: `pytest -q` green; the stub fails when the interface is violated
- [ ] **T12 · docs** — `specs/product/states.md` walk clause names the graph and what it implies for
      the path's meaning; README stops implying WordNet is the only graph
      Accept: `pytest tests/test_docs_current.py -q`; the README's walk paragraph is edited, not
      appended

## Out of scope for this change

- Remote graphs, runtime embeddings, graph editing, ontology import, third-party provider loading.
- Any change to the ledger graph, `/graph`, the pane, or state semantics.
