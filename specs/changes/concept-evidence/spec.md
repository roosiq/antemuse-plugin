# Change: the evidence behind a concept

Status: **LIVE** · opened 2026-11-08 · built 2026-11-08

## Intent

Ryan asked *"how do we get more detail on what these concepts connect to"*.

The graph could say a concept was connected to a session and to a file, and nothing more. A
session id is not detail: it tells you *that* a word came up in a conversation, not what was said,
which commit it was about, or which words it travelled with. `served beside` was worse than
useless — it was computed over every concept in a session, so it returned `source (1092)`.

## What is stored now

`appearances(concept_id, source, ref, at)` — the row behind a sighting:

| source | `ref` | meaning |
|---|---|---|
| `message` | Hermes message id | the message the concept was read from |
| `commit` | commit sha | the commit whose changed files name the concept |

`at` is the **message's own timestamp**, not the scan's: the ledger says when the thing was said,
not when we got round to reading it. Two concepts are linked when they appeared in the **same
message** — real co-occurrence a reader can check — rather than in the same session, which is only
the session template.

The ledger still stores **identity only**: an id, a sha, a path. No message text, no reasoning,
no file contents.

## What a reader gets

`tools/graph_inspect.py <concept>` — a card with the evidence:

- **sessions** it was met in, with counts and dates;
- **messages** by id and time, and with `--text` a short excerpt resolved on demand from Hermes'
  own store (read-only, never written to the ledger);
- **commits** — its own, plus those of the files it is attached to;
- **files** whose path carries the concept's words;
- **served beside** — concepts that appeared in the same messages, with counts;
- **nearest in meaning**, from the embeddings, when that file exists;
- `--top N` — the best-connected concepts, and `--json` for the raw detail.

Worked example, from a scan of this machine's sessions:

```
toslop  (lemma)
  seen 3× · first Nov 7 13:36 · last Nov 8 12:16
  sessions
    20261108_091834_aa6c8db0  2×  last Nov 8 12:16
    20261107_133554_c4dbe2  1×  last Nov 7 13:36
  messages (3 shown)
    #331325  Nov 8 12:16  assistant: J3 is done — Wave 3 is now one item from closed. **Origin…
    #331210  Nov 8 11:50  assistant: Daydream is a **state**, not a source — so the collider…
  served beside
    source (4), memory (2), antemuse (2), evidence (2), material (2)
```

## The graph follows

- `served_in` edges carry how often and when the last sighting was.
- `co_served` edges are co-occurrence counts in messages, capped to the **200 strongest pairs** —
  852 unchecked pairs turned the structural view into a hairball, and edge width now encodes the
  count.
- `near_in_meaning` edges carry their cosine.
- Every edge optionally carries an `evidence` object, so the JSON explains the line it drew.

## Acceptance criteria

1. A sighting records which message or commit it came from, when the caller knows it.
2. A concept's `at` is the message's timestamp, not the scan time.
3. Two concepts are linked only when they share a message; sharing a session is not a link.
4. `detail()` returns sessions, messages, commits (own plus its files'), files, siblings, links.
5. `message_excerpts()` reads on demand, returns nothing when the store is absent, and never
   writes a transcript into the ledger.
6. The inspect card prints all of that for a person, and `--top`/`--json` work.
7. The export's summary describes what is actually drawn.

## Verification

- `tests/test_concept_detail.py` (7): sessions/messages/files/commits, sibling from the same
  message, never-seen wording, the card on an empty and a populated ledger, `--top` ordering, and
  an excerpt read on demand with an assertion that nothing was stored.
- `tests/test_concept_graph.py` (+2): same-message link with weight and evidence, and
  sharing-only-a-session is *not* a link.
- Real run: 1,800 messages scanned → 2,925 concepts; `gateway` resolves to 6 sessions, 8 messages
  with excerpts, 8 co-occurring concepts and 6 nearest-in-meaning.
- Suite: **879 passed, 1 skipped**; `spec_audit` 0 drift.

## Must not change

The identity-only rule (ids, shas, paths — never text), the read-only posture toward
`state.db`, and the four-spoke session cap in the structural view.
