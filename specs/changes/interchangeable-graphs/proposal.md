# Interchangeable concept graphs

Change id: `interchangeable-graphs`
Status: **implemented — 2026-11-16 (v0.11.20)**

## The situation

A walk is already "a graph plus the rules for moving on it" (`core/walks.py`, first line). The
seam exists and is used: `Graph` is an abstract class (`walks.py:128`), `GRAPHS` is a registry
(`walks.py:275`), and two providers implement it — `WordNetGraph` (`:149`) and `ManualGraph`
(`:251`), the latter fed by a JSON adjacency list a user drops in `walks/`.

What does not exist is the part that makes the seam *interchangeable*:

- **The registry is two names in a dict.** There is no way for a third provider to arrive without
  editing the source, and no validation of the `graph` field in a walk spec beyond
  `GRAPHS[self.graph_name]()` (`:291`), which raises `KeyError` on a typo.
- **`far_from()` is optional and silently degrades.** `far()` returns `None` when the provider
  lacks it (`:391`), so a `far`, `vault`, `orbit` or `composite` walk on a non-WordNet graph quietly
  becomes an ordinary near-step walk and reports it as the jump it did not make.
- **Relations are WordNet's vocabulary.** `ALL_RELATIONS` (`:49`) and the built-in walk specs encode
  hypernym/hyponym/holonym/meronym as directions. `upward` means "toward the general" only because
  those names happen to mean that; a provider with `is-a` / `part-of` / `cites` cannot express the
  same intent, and `ManualGraph` already invents `next`.
- **Node ids are provider-global.** A node id is a synset name or a lowercased word, with nothing
  naming the graph it came from. Two providers can produce the same id for different things, and the
  ledger only ever sees labels, so a walk's provenance is lost the moment it is recorded.
- **Seeds are a fixed English list.** `SEEDS` (`:152`) is twelve words. A provider whose vocabulary
  is not English — a personal wiki, an ontology, a repo corpus — has no seeds, and
  `random_node()` returning `None` produces `walk unavailable · graph 'x' has no starting node`.
- **Nothing is deterministic.** `RNG = random.SystemRandom()` (`:26`). Two runs of the same walk on
  the same cursor take different paths. That is defensible for a walk and fatal for the example
  generator (`specs/product/examples.md`), which must be reproducible to be honest.
- **No provenance or licence on a node.** Shipping a second bundled graph raises a licensing
  question the current node shape cannot answer.

`core/graph.py` is a **different** graph and must not be confused with this one: it is a read-only
snapshot of the ledger (concepts, sessions, files), capped at 400 nodes / 1,200 edges, and it is what
the pane and `/explore` draw. This change is about the graph a **walk** moves on. The spec keeps them
apart by name: *walk graph* vs *ledger graph*.

## Goal

A walk graph is a **provider behind a declared interface**, so a new graph can be added without
touching the engine, and every policy either works on it or says it cannot. Two providers ship: the
existing WordNet projection and a new corpus graph built from text the user supplies — the second one
exists to prove the first is not special.

## Non-goals

- No remote graph service, no network fetches, no embeddings at runtime. (WordNet is already
  projected offline by `tools/project_wordnet.py`; other providers follow the same rule.)
- No graph-editing UI, no ontology editor.
- No change to state semantics, dose, endings, or the tool surface.
- No change to the ledger graph, `/graph`, or the pane.
- No third-party code execution in this change. External providers are Tier 3, below, and need their
  own spec.

## The interface

```python
class Graph:
    name: str                      # stable, lowercase, becomes the id namespace
    relations: dict[str, str]      # relation -> role: general | specific | part | whole | lateral | sequence
    capabilities: set[str]         # {"far", "resume", "gloss", "seeds"} — declared, not discovered by hasattr

    def resolve(self, term: str) -> dict | None: ...
    def random_node(self, relation_roles: set[str] | None = None) -> dict | None: ...
    def edges(self, node: dict) -> list[tuple[str, dict]]: ...
    def resume(self, node_id: str) -> dict | None: ...
    def far_from(self, node: dict, samples: int, avoid: list[str]) -> dict | None: ...  # if "far"

# node: {"id": "<graph>:<key>", "label": str, "pos": str, "gloss": str,
#        "source": str, "licence": str}
```

Four rules make this an interface rather than a convention:

1. **Ids are namespaced** — `wordnet:carousel.n.01`, `corpus:onboarding`. `resume()` receives the
   namespaced id and the provider strips its own prefix. Two graphs can never collide, and a ledger
   row can name where a concept came from.
2. **Roles, not relation names, carry intent.** Built-in walks are rewritten against roles:
   `upward` = `{general, whole}`, `downward` = `{specific, part}`, `lateral` = `{lateral}`. A walk
   spec may still name relations directly for a specific graph.
3. **Capabilities are declared.** A walk whose policy needs `far` on a provider without it **fails
   loudly at entry** — `WALKING · graph 'corpus' cannot jump · use wander or supply far_from` —
   rather than silently walking one hop and calling it a jump.
4. **Provenance travels with the node.** `source` and `licence` are required fields; the bundled
   WordNet provider reports Princeton WordNet 3.0 and its licence, so the first non-WordNet graph
   cannot arrive without the same paperwork.

## Requirements

**R1 — registry with validation.** `graph` in a walk spec resolves through a registry that answers
`unknown graph 'x' (known: wordnet, manual, corpus)`; `save()` rejects an unknown graph and a
capability mismatch at write time, not at the first step.

**R2 — the role mapping is data.** Each provider declares `relations`; walks declare `roles`. Both
existing built-in sets keep working: the nine WordNet walks must produce byte-identical walk specs
after translation (`outer`, `wander`, `upward`, `downward`, `composite`, `vault`, `run3`, `orbit`,
`lateral`).

**R3 — capability honesty.** `far`, `vault`, `orbit` and `composite` on a provider without `far`
fails at entry with a message naming the provider and the alternative. No silent degradation.

**R4 — seeds are provider-supplied.** `random_node()` takes the roles the walk can actually move on
and must either return a node that has at least one such edge, or `None` with a reason. `SEEDS`
becomes WordNet's own business.

**R5 — determinism on demand.** `ANTEMUSE_GRAPH_SEED` (unset = today's behaviour, `SystemRandom`)
makes every choice — seed node, edge, far sample — come from a seeded `random.Random`, so the same
cursor and seed replay the same path. The example generator sets it; the product does not.

**R6 — provenance.** Every node carries `source` and `licence`; the journal line for a hop includes
the graph name when it is not `wordnet`, because "we walked a corpus you gave us" is different from
"we walked English".

**R7 — the corpus provider.** A file-per-graph format in `$ANTEMUSE_STATES_HOME/graphs/`:
`{"name": "onboarding", "source": "...", "licence": "...", "nodes": {...}, "edges": [...]}` with
explicit edges, capped by the same limits as the ledger graph. It must pass the provider contract
tests without special cases in the engine.

**R8 — limits.** Providers declare `size` and load lazily; a graph over the cap is rejected at load
with a message, never truncated silently. WordNet's 117,659 synsets remain an offline projection, not
a runtime load.

**R9 — failure contract.** Four failure modes are named and reported: `unavailable` (dependency
missing, e.g. nltk data), `empty` (no nodes / no seeds), `too_large`, `no_far`. Each answers in the
state's own voice and none raises into a turn.

**R10 — no new model calls.** The provider interface is deterministic data access; nothing in it may
call a model, and the existing no-model-call rule for entry, exit, expiry and rendering is unchanged.

**R11 — the pane is untouched.** `/graph` continues to draw the ledger graph. A walk's graph is not
drawn; the doc that says what the pane shows must keep saying that, and the walk's own provenance is
visible in the journal and the account instead.

**R12 — docs.** `specs/product/states.md` gains one clause under walk: which graph it walked and what
that means for the path's meaning (a corpus path is only as meaningful as the corpus). The README's
walk paragraph stops implying WordNet is the only graph.

## Acceptance criteria

1. **Contract tests, both providers.** A provider-contract module runs the same assertions —
   resolve, random_node with roles, edges, resume, far or declared absence — over `wordnet` and
   `corpus`; a third stub provider in the test file proves the tests are not written to WordNet's
   shape.
2. **The nine built-ins are unchanged.** For each, the translated spec yields the same relations,
   the same jump policy and the same seed mode as today; `tests/test_walks.py` passes unedited except
   where it asserts the old `graph` field.
3. **Capability honesty is observable.** A `vault` walk on `corpus` exits at entry with a message
   naming the graph and the alternative; a `wander` walk on the same graph runs to its dose.
4. **Determinism.** With `ANTEMUSE_GRAPH_SEED=7`, two consecutive walks from the same cursor produce
   identical hop sequences; unset, they differ (that is the existing behaviour and the test asserts
   it only as "not equal on repeated runs", not as a flake).
5. **Provenance.** A hop recorded from `corpus` carries `source` and `licence` in the ledger row and
   names the graph in the journal line; a WordNet hop does not.
6. **Ids do not collide.** A `corpus` node labelled `carousel` and the WordNet synset `carousel.n.01`
   are two distinct nodes with two distinct ids, and one walk of each in the same session leaves two
   ledger rows.
7. **Failure modes.** `unavailable` (nltk data hidden), `empty` (a graph with no edges), `too_large`
   (over cap) and `no_far` each produce their named line and no exception, verified by a test per
   mode.
8. **No regressions.** Full suite green (`tests/test_walks.py`, `tests/test_concept_graph.py`,
   `tests/test_walk_pane.py` among them), harness unchanged, no new dependency, and
   `hermes plugins validate` still clean.

## Risks

- **The role mapping is where this change can quietly break the product.** `upward`/`downward` are
  the walks whose *meaning* is a direction; translating them into roles must preserve the nine specs
  exactly, which acceptance criterion 2 checks by comparison rather than by eye.
- **Determinism is a product decision as much as a test affordance.** A seeded walk makes the demo
  and the examples reproducible, and makes a real walk repeatable — which some users will like and
  others will read as "it's the same walk every time". It is opt-in by env var for exactly that
  reason.
- **A corpus graph invites paths that are only as meaningful as the corpus.** Explicit edges can
  still encode a weak or misleading relationship. The failure is honest (R12 wording), but the
  product risk is that a bad corpus produces bad walks and the user blames the walk.
  `specs/product/states.md` says this plainly instead of hiding it.
- **Provenance adds a field to every node**, which touches the node shape used by the pane's payload
  builder if it is ever shared. It is not shared today; the spec forbids making it shared in this
  change.

## Open questions (gate 1)

1. **Corpus edges**: derive co-occurrence automatically from supplied text, or require explicit
   edges (the `manual` format already does this)? Automatic is friendlier and much weaker.
   **Decision (2026-11-16):** Require explicit edges. The corpus provider does not derive runtime
   co-occurrence edges.
2. **Scope of R7**: is a corpus provider in scope for this release, or should this change land only
   the interface + capability/provenance/determinism rules, with the corpus provider as its own
   follow-up? The interface is verifiable with a test-only stub; the corpus provider is what proves
   it in public.
   **Decision (2026-11-16):** The corpus provider is in scope for this change.
3. **Third-party providers (Tier 3)**: manifest-declared factory path with a sandbox rule, or
   forever out of scope? I would keep it out and say so, so nobody designs for it.
   **Decision (2026-11-16):** Tier 3 manifest-declared factory providers are out of scope for this
   change.
