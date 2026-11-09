# Change: the concept graph — what a concept is attached to, and a picture of it

Status: **LIVE** · opened 2026-11-08 · built 2026-11-08

## Intent

Ryan asked, on 2026-11-08: *"does the concept graph include relationships to messages /
artifacts and can we visualize it"*.

The honest answer before this change was **no on both counts**. The walk's graph is WordNet and
FrameNet — concept to concept, with no edge to anything the plugin produced. The ledger recorded
which *session* a concept was met in but had no message identity, no artifact identity, and its
`links` table was written by a function nobody called (`0` rows). There was no export and no
picture.

This change makes the graph real and visible, without changing what any state does.

## Nodes and edges

| node | key | meaning |
|---|---|---|
| `concept` | `kind:synset-or-lemma` | a concept the plugin served or met |
| `session` | Hermes session id | the conversation it was met in |
| `file` | `project/relpath` | a file a repository's own commit touched |
| `project` | repo name | where the file lives |

| edge | meaning |
|---|---|
| `served_in` | concept → session (provenance, without the conversation) |
| `co_served` | concept ↔ concept, served in the same move of the same session |
| `touched` | concept → file, when the concept's own words appear in the file's path |
| `in_project` | file → project |

Artifacts are recorded from `git log --name-only` — **paths only, never contents**. Sessions are
recorded as ids, never as transcripts. This keeps the ledger's identity-only rule intact.

A session is a hub, so each gets at most **four** `served_in` spokes: a session with eighty
edges is a hairball, not provenance. Node caps are per kind (50 % concepts, 25 % files, 20 %
sessions, projects unpinned), because a picture made only of concepts is not a picture of a
graph.

## The picture

`tools/graph_export.py` writes `graph.json`, `graph.svg` and `graph.png` under
`experiments/graph/`.

The layout is **concentric, not a spring**. A force layout on hub-and-spoke data pulls the hubs
outward and leaves the centre black — the first two attempts did exactly that and were rejected
by looking at them. The structure is already known, so it is drawn as that: concepts on a
phyllotaxis spiral in the middle (even spacing at any count, no overlap), files on one ring,
projects on another, sessions on the outside. Concepts with the highest degree, every session
and every project are labelled; labels point outward so they never run into the next node. Same
ledger, same picture — the layout is deterministic.

## Non-goals

- No change to any state's material, dose, ceiling, ending, or to the walk's WordNet traversal.
- No embeddings, no vector index, no model call, no network at render time.
- No file contents, no message bodies, no transcripts in the ledger.
- No interactive product surface: this is a diagnostic tool, not a sixth surface.

## Acceptance criteria

1. A concept is connected to the session it was met in, and to any file whose path shares its
   words.
2. A file is connected to its project, and a file node is created from a commit's touched paths
   only.
3. A session has at most four spokes; node caps are per kind.
4. Session ids are drawn as dates (`Nov 8 09:18`), not as hashes.
5. An empty or corrupt ledger yields an empty graph, never an exception.
6. Edges never reference a node that is not in the graph.
7. The export writes all three artefacts, and the SVG contains the nodes it counted.

## Verification

- `tests/test_concept_graph.py` (8): provenance edge, artifact → project, co-served pair, the
  four-spoke cap, the date label, empty/corrupt ledger, summary matching the drawn graph, and a
  real export run that checks the PNG is non-trivial, the SVG has circles, and the JSON agrees.
- A real export over a 900-message scan of this machine's sessions plus the week's commits:
  **120 concepts, 36 files, 3 projects, 12 sessions, 121 edges** — checked by looking at the PNG,
  twice: the first spring layouts were rejected as hairballs with an empty centre and replaced
  by the concentric one.
- Suite: **865 passed, 1 skipped**; `spec_audit` 0 drift.

## Must not change

The ledger's identity-only rule, the four-spoke session cap, the per-kind node caps, and the
rule that no state's behaviour depends on this module or on the export existing.
