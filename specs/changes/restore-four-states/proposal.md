# Restore the four agent states

Change id: `restore-four-states`
Status: **implemented — 2026-11-16** (command surface, public documents, examples, and record)

## Why

`walk` is the only agent state in 0.11.20. On 2026-11-09 the owner declined both cut lists
(`docs/audits/2026-11-09-product-direction.md`: "No states dropped … walk, daydream, doomscroll, unstuck
and dream all stay for the submission"). On 2026-11-15 `971f715` removed four of them anyway, with no
recorded approval. This change puts them back, on top of everything 0.11.x learned, and records the
decision that was missing.

`/explore` is not affected: it was never an agent state.

## What comes back

Restored from the pre-cut tree (`971f715^`: `core/states.py`, `core/sources.py`) and re-ported onto the
current engine contract — dose accounting, session ownership, no clock, named endings, residue decay.

| state | label | dose | turns | tools on entry | material |
|---|---|---|---|---|---|
| `walk` | WALKING | 6 hops | 6 | open | unchanged (graph provider) |
| `daydream` | DAYDREAMING | 2 pairs | 2 | open | two memories from the person's own history, what they touch, one possibility |
| `doomscroll` | DOOMSCROLLING | 3 items | 3 | open (recommended set: `web_search`, `web_extract`, `read_file`, `search_files`, `browser_exec`) | a random feed lane: stupidity and comedy, nothing to take away |
| `dream` | DREAMING | 2 recombinations | 2 | open | the day across projects — local commit subjects only, never transcripts |
| `unstuck` | UNSTUCK | 1 direction | 3 | open (recommended set: `read_file`, `search_files`) | one recommendation from history plus one edge of the concept graph |

Each keeps the ending vocabulary the engine already has (`complete`, `dry`, `failed`, `returned`) and
writes exactly one account and one `moves` row per ending. No state may re-introduce a wall clock.

## Decisions taken here

- **Tools stay open by default** (the owner's standing rule): a state changes the frame the agent
  works in, and taking tools away is a second decision. `block: true` applies the state's declared
  set, `allow` narrows it further, and `/return` is always available. The pre-cut build blocked
  `daydream` and `dream` by default; that is the behaviour this restore deliberately does not bring
  back.
- **`doomscroll` is restored with its feed gated.** The audit's objection was injection risk: feed text
  is untrusted. It comes back behind its own setting (default on, `doomscroll_feed` to disable) and its
  material is labelled to the model as untrusted data, never as instruction — the residue line and the
  block header say what it is. No feed text is written to the ledger or the journal.
- **`dream` reads local git subjects only.** Not transcripts, not notes — the pre-cut behaviour, kept.
- **Memory readers stay local and read-only** (`MEMORY.md`, `USER.md` under the Hermes home), as they
  were, and the disclosure returns to `SECURITY.md` and the catalog entry.
- **One tool, one command per state.** The `state` tool keeps its `name` parameter; commands come back as
  `/daydream`, `/doomscroll`, `/dream`, `/unstuck` beside `/walk`, `/explore`, `/return`.

## Non-goals

- No change to `/explore`, the cockpit, the ledger graph, `/graph`, or the pane's drawing.
- No change to `/walk`, the graph provider interface, dose accounting, residue ownership or `/flight`.
- No new dependency, no network call added beyond `doomscroll`'s existing feed fetch.
- No second graph, no scoring model, no re-tuning of doses.

## Acceptance criteria

1. **Registry.** `STATES` contains exactly `walk`, `daydream`, `doomscroll`, `dream`, `unstuck`; each
   entry declares label, dose unit + n, turn count, tool policy and its material provider.
2. **Dose honesty.** Every state delivers exactly its dose and ends `complete` only after the last unit
   is shown; a provider with nothing to give ends `dry`; a provider that cannot run ends `failed` with a
   named reason. No state ends on time.
3. **Tool policy.** `daydream` and `dream` refuse tools while active with a message naming the state and
   `/return`; `doomscroll` and `unstuck` permit exactly their declared tools and refuse others; `/walk`
   stays open by default; `block: true` narrows further and `/return` is always allowed.
4. **Material is real.** `daydream` pairs come from the person's own recorded turns, `dream` from git
   subjects in the local repository, `unstuck` from history plus a graph edge, `doomscroll` from a feed
   lane — each test asserts the shape of the material, not just that a line was printed.
5. **Doomscroll safety.** Feed text reaches the model only inside a labelled untrusted block; it is not
   written into the journal, the ledger, or the account; `doomscroll_feed=false` makes the state end
   `failed` with a named reason instead of silently pretending.
6. **No regression.** The suite is green, including every existing walk/graph/flight/cockpit test; the
   cockpit harness and desktop harness are unchanged and pass; `hermes plugins validate` is clean.
7. **Surface truth.** README, SKILL, SECURITY, CONTRIBUTING, `specs/product/states.md`, the manifest
   description and the catalog entry describe five agent states again — no document still says "one
   agent state", and no document promises a state the registry lacks.
8. **The record is fixed.** `specs/changes/one-state-and-verdict/` is marked superseded by this change
   with the date and the reason, so the tree stops contradicting the 2026-11-09 owner note.

## Risks

- **Four providers is four ways to fail quietly.** Each needs its own failure mode test; the pre-cut
  bodies were written before the current provider contract, so they are re-ported rather than pasted.
- **The command surface grows back to seven.** That is the owner's call and it is recorded here; the
  cost is a wider surface for a reviewer to audit, and the catalog description must say five states.
- **Doomscroll is a network fetch.** It stays the only one; it is gated, labelled, and its material never
  reaches durable storage.

## Acceptance evidence

To be filled by the implementation: one module per restored state, a tool-policy module, and a
doomscroll-labelling module.
