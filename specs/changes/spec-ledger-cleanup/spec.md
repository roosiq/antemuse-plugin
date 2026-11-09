# Change: make the spec record readable again

Status: **LIVE** · opened 2026-11-08 · built 2026-11-08

## Intent

The review found the change log had stopped being a record. `docs/spec.md` §15 carried **two
rows for each of two changes** (`semantic-states`, `desktop-surfaces`), so it double-counted
them; **six rows named a change with no `specs/changes/` directory**; and the status column had
grown seven words (*implemented, verified, approved, draft, planning, live, partial*) against a
standing decision that there are **four**: LIVE, PARTIAL, PROPOSED, NOT BUILT. The audit passed
throughout, because it only compared each spec's header with its row and never looked at the
column itself.

A record that cannot be read at a glance is a record that gets re-litigated in every review.

## What changed

- **One row per change.** `semantic-states` and `desktop-surfaces` are single rows again, with
  the surviving `desktop-surfaces` row carrying both halves of what was verified in the app.
- **Four status words, enforced.** Every row's status is one of LIVE / PARTIAL / PROPOSED /
  NOT BUILT, and `tools/spec_audit.py` now fails when a row uses anything else (`row-status:`).
  Spec headers may still say "implemented" or "approved" — `status_word()` resolves those to one
  of the four rather than the table growing synonyms again.
- **Orphans are named, not hidden.** Rows with no change folder are printed by the audit and
  allowlisted in `LEGACY_ROWS`: they were built before the discipline and survive on commit
  history alone. Writing retroactive specs for them would invent a process that did not happen.
  A *new* orphan fails the test.
- **The audit reads §15, not the whole document.** It previously matched backticked names in
  every table — walks, states, tools — so it could neither see a suffixed row nor name an
  orphan. It now scopes to the section and accepts suffixes (`§9`, `(J2)`).

## Acceptance criteria

1. Every change folder has exactly one §15 row; every §15 row has at most one.
2. Every row's status is one of the four words.
3. A row whose status is a synonym fails the audit.
4. An orphan row outside `LEGACY_ROWS` fails the test, and the audit prints the legacy ones.
5. A suffixed row (`§9`, `(J2)`) is visible to the audit.

## Verification

- `tools/spec_audit.py --counts` → **0 drift**, and prints the six legacy orphans.
- `tests/test_spec_audit.py` — the row/folder test now allowlists the six and fails on any new
  one; the status test pins `implemented → live`, `implemented (partial) → partial`,
  `not built → not built`.
- Suite: **857 passed, 1 skipped**.

## Must not change

The four status words themselves, `LEGACY_ROWS` staying exactly the six historical rows, and
the audit remaining a tool that is also a test.
