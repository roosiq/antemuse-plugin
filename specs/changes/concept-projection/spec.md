# Change: project the concepts by meaning

Status: **LIVE** · opened 2026-11-08 · built 2026-11-08

## Intent

Ryan asked *"can we semantically project the concepts? we don't need to show the dates"*.

The structural drawing places a concept by what it is attached to — file, project, session. That
is provenance, not meaning: `gateway` sits next to `plugin` because a commit touched both, and
`porosity` sits next to `thermal` for the same reason. A projection by meaning puts a concept
next to the concepts it is *about*, which is the thing a reader actually wants to see when they
ask what the ledger knows.

Dates are gone from session nodes in the structural view too: a session is structure, not a
moment to read.

## How it is built

**Embeddings are a data artefact, not a dependency.** `tools/graph_embed.py` runs under whatever
interpreter has torch (here `/home/ryan/ontology-embedding-experiment/.venv`), embeds the
ledger's concept labels with `BAAI/bge-small-en-v1.5` (384 dimensions, cached locally), and
writes unit vectors to `$XDG_CACHE_HOME/antemuse/embeddings.json` (~/.cache/antemuse/). The plugin itself never imports
torch; the export reads the JSON.

**The projection is PCA, then stress majorization.** PCA alone keeps two of 384 directions and
drops every concept into a narrow band, so it is only the starting point:

1. two principal components by power iteration with deflation, sign-fixed so the same data never
   draws mirrored;
2. SMACOF refinement against the embedding distances (power 1.4, 80 iterations) — the textbook
   update, because an ad-hoc force version was tried first and made agreement **worse**
   (0.34 → 0.29);
3. fitted to the canvas with the axes kept to scale.

All of it is plain arithmetic: no numpy, no sklearn, no network, and deterministic — the same
embeddings file draws the same picture, so two exports can be compared rather than described.

**Edges mean "near in meaning"** in this view: each concept to its two closest neighbours. The
structural `co_served` edges are not drawn across a semantic map — that would be a category
error, and it was what made the first attempt unreadable.

**Sessions and projects are absent from this view.** They have no semantic position; placing
them somewhere false to keep the legend complete would be worse than leaving them out.

## Measured

`projection_quality()` correlates 2D distance against embedding distance over 600 sampled pairs
— a projection you cannot score is a decoration.

| stage | correlation |
|---|---|
| PCA only | 0.34 |
| ad-hoc force refinement (rejected) | 0.29 |
| SMACOF, power 1.4 | **0.57** |

On 120 concepts from a scanned ledger the clusters are what they should be: implementation and
config terms together, documentation and evaluation terms together, physical-material terms
(`porosity`, `thermal`, `weight`) off on their own.

## Acceptance criteria

1. `tools/graph_export.py --semantic` writes `concept-semantic.{json,svg,png}`.
2. The projection is deterministic: identical inputs give identical coordinates.
3. Refinement does not reduce agreement with embedding distances, and neighbours in meaning land
   closer together than strangers.
4. Only concepts appear in the semantic view; sessions and projects are excluded rather than
   guessed at.
5. Missing embeddings fail with a message naming `tools/graph_embed.py`, not a traceback.
6. Session nodes in the structural view carry no date label.
7. The plugin imports no new dependency and makes no network call at render time.

## Verification

- `tests/test_concept_graph.py` (14, six of them new): determinism, refinement ≥ PCA agreement,
  neighbour ordering in the drawing, concepts-only semantic view, the three artefacts written,
  and the missing-embeddings message.
- `tools/graph_embed.py` on a real ledger: **400 concepts · dim 384 · 3.6 s**, offline model load.
- Reviewed by looking at the render: the first PCA-only image was rejected for a dense central
  band, label collisions and long crossing edges; the shipped one clusters, labels without
  collision and fills the canvas.
- Suite: **871 passed, 1 skipped**; `spec_audit` 0 drift.

## Must not change

The ledger's identity-only rule, the absence of torch from the plugin's own imports, the
determinism of the projection, and the structural view remaining the default.
