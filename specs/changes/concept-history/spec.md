# Change: a concept ledger, and concepts that survive the session

Status: **LIVE** · opened 2026-11-08 · built 2026-11-08

## Intent

Every state re-derives its world from scratch. The journal is a decaying transcript (60 entries),
`residue` is a two-turn handoff note, the recall ring is the last 24 turns of *this* conversation,
and a walk's `seen` set is 12 terms. So the plugin can say what just happened and cannot answer
the two questions every move actually needs: **have we been here before?** and **did anything
come of it?**

Ryan, 2026-11-08: *"also need to be able to identify concepts from past sessions."*

This change adds a **concept ledger** — a small, durable, derived SQLite store of concepts the
plugin has seen — plus the identification that makes "past sessions" meaningful.

It is deliberately **not** a memory layer. The plugin must run with any memory provider by its
default interface, so the ledger never writes to the provider, never reads it behind its back,
and is never required for entry, exit, expiry, tool restoration or rendering.

## Non-goals

- No embeddings, no vector index, no model call. The ledger stores identity, not meaning.
- No writes to `MEMORY.md` or any provider. The agent's memory stays read-only input.
- No transcripts. The ledger stores a term, its kind, its key, and provenance — never the
  sentence, prompt or reply a term came from.
- No sixth state, no new command, no new setting.
- No behaviour change that depends on the ledger existing.

## Concept identity

A concept is `(kind, key)`, so the same thing seen twice is the same row:

| kind | key | label |
|---|---|---|
| `wordnet` | synset name (`shipper.n.01`) when resolvable | the term as served |
| `lemma` | normalized term when WordNet has no synset | the term |
| `frame` | FrameNet frame ID | frame name |
| `feed` | hash of the item URL | source host |
| `memory` | hash of the normalized memory text | first six words |

Resolution order is lexical: lowercase, strip punctuation, WordNet `morphy`, then synset.
Without a synset the term still counts as a concept — it just never merges with a neighbour.

## Sources

- `move` — delivered by a state (walk step, daydream pair, dream connection, scroll item).
- `session` — extracted from a past Hermes session (`~/.hermes/state.db`, read-only).
- `seed` — the entry seed a state started from (`[seed=project:antemuse]`).

## Session identification

The canonical store is Hermes' own `state.db` (`messages`, `messages_fts`; 165 k messages over
1 447 sessions on this machine as of 2026-11-08). It is opened **read-only** and scanned
incrementally with a stored row-id cursor, so a scan is bounded and repeatable:

1. read messages newer than the cursor (bounded batch),
2. keep user and assistant text only — no tool output, no reasoning fields,
3. extract candidate terms (WordNet-lemmatized, stopwords and code dropped, 3–30 chars),
4. resolve identity, upsert `concepts`, append `served` rows with `session` and `at`,
5. advance the cursor.

Nothing from a message body is stored except the terms themselves, and a term longer than 30
characters is not a term — that bound is the acceptance test for "no transcripts in the ledger".

## Storage

```
concepts(id, kind, key, label, first_seen, last_seen, times, UNIQUE(kind, key))
served(concept_id, move, session, at, used_at)          -- one row per sighting
moves(id, state, started, ended, ending, dose_done)
links(a, b, relation, move, at)                          -- connections the plugin found
cursor(name, value)                                      -- scan cursors
```

Bounded: rows older than 30 days pruned on write, hard cap 20 000 concepts and 60 000 servings.
Fail-open: a missing or corrupt database logs a named failure event and every state still runs.

## Queries the moves need

- `seen_before(kind, key, session)` → when and in which sessions, excluding the current one.
- `in_session(session)` → the concepts a session touched.
- `circling(days, min_sessions)` → concepts appearing in several sessions: relevance by repetition.
- `unused(days)` → concepts served but never used downstream.
- `recent(days)` → the last few days of concepts, any source.

## Consumers, in order

1. **walk** — skip concepts already in the ledger's recent window, and say so when a step lands
   somewhere with history: `↩ 5 hops from agent · seen 2 days ago in 3 sessions`.
2. **dream** — connect *moves across sessions*: a concept circling in walks this week is a task
   connection the commit subjects never mention. This is what dream's thinness actually needs.
3. **unstuck** — "we have been circling `shipper` for a week and never touched `retry`".

## Acceptance criteria

1. A bounded scan of past sessions stores concepts from **at least two distinct session ids**,
   and `seen_before` answers for a term the current session never saw.
2. **No message text is stored**: every stored string is ≤ 30 characters and the row count is
   independent of message length.
3. **Fail-open**: with the ledger deleted, all five states still deliver; with it made
   unreadable, the plugin records a named failure and still delivers.
4. **Bounded**: a scan of 30 days processes a bounded number of messages and the store stays
   under its caps.
5. **Walk stops repeating across sessions**: the same synset does not appear twice in two
   consecutive walks at dose 6 when the ledger has history.
6. **Retention**: rows older than the window are pruned on write, and pruning never deletes a
   concept that is still inside the window.

## Verification

- `tests/test_concept_history.py` — identity merging, the 30-character bound, fail-open, cursor
  resumption, cross-session query, pruning.
- A real bounded scan against `state.db`, reported with counts: sessions scanned, concepts
  resolved, synsets merged, and one query answered from a session that is not this one.
- All five states re-run with the ledger deleted and with it corrupt.

## Must not change

§18's protected set: lifecycle, doses, ceilings, endings, turn budgets, tool policy, directives,
contracts, residue labels, journal cap 60, residue cap 3, two-turn report decay, hook contracts,
`/return`, `CONTROL_TOOLS`, the wordless card. The six settings stay six.

## Verification (2026-11-08)

A real bounded scan against this machine's Hermes store (`days=2`, eight batches of 300,
read-only, cursor kept in the ledger):

- **905 messages scanned → 1 972 concepts, 8 850 servings, 65 distinct session ids.**
- `seen_before("shipper", exclude_session="…")` → **2 sessions, "earlier today"** — a concept
  identified from sessions that are not this one.
- `circling(7d, ≥3 sessions)` after the boilerplate filter, top terms: `plugin`, `hermes`,
  `contracts`, `antemuse`, `ryan`, `docstring`, `repair`, `failure`. Before the filter the top
  of that list was `work`, `scratch`, `repo` — the session template, not the work.
- Extraction rule that made it usable: a concept is a noun, or a word WordNet has never heard
  of. Verbs and adjectives were a third of the first run ("exist", "already", "actually"), and
  a short dictionary noun is usually a function word in disguise ("point", "look", "let").

Fail-open, checked both ways with all five states re-run: **ledger deleted** → every state
delivers; **ledger corrupt** (a text file where the database should be) → every state delivers,
queries return empty, and one named `history` failure event is recorded instead of a crash.

Bounds: nothing longer than 30 characters can be stored (a sentence cannot be a term), rows
older than 30 days are pruned on write, and the hard caps are 20 000 concepts / 60 000
servings. A second scan re-reads nothing (cursor test).

Suite: **839 passed, 1 skipped**; `spec_audit` 0 drift.
