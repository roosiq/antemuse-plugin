SUPERSEDED 2026-11-16 — this spec describes the retired multi-state product; see one-state-and-verdict.

# State experience — tasks

Change id: `state-experience`
Source: `proposal.md` (F1–F9, O1–O4, D1–D5)

Nothing here is approved yet. Each phase is independently shippable and testable.

## Phase 0 — done in this session

- [x] F8: the `state` tool description and its `name` parameter name the sole walk state.
      Guard: `tests/test_session.py::test_the_tool_schema_names_every_state`.
      Verify: `pytest tests/test_session.py -q`.

## Phase 1 — outcomes (recommended first)

- [ ] **T1 · every ending names its own product** — `stop()` uses `states.after()` for
      `reason == "complete"` instead of one shared sentence.
      Accept: a `complete` daydream ends naming the possibility; a `complete` doomscroll says there
      was nothing to keep; walk still asks for a different first step.
      Test: one assertion per state in `tests/test_states.py`.

- [ ] **T2 · the account names what arrived, safely** — `_account()` reports shared terms, the
      possibility, the connection's two sides, or the first move — never memory sentences.
      Accept: daydream's account contains the shared terms and no memory text; the privacy test still
      passes unchanged; `1 of 1 directions` gains the direction's first move.
      Test: extend `test_the_account_never_quotes_the_material_it_was_given` with a positive case.

- [ ] **T3 · the pane shows the dose** — a state strip: label, served/seen, ending reason.
      Accept: a running walk shows `4/6 hops`; a closed state shows its reason for one poll, then
      clears; nothing renders when no state is running.
      Verify: harness check + a screenshot at 1440 and 390.

- [x] **T8 · the status chip carries the state** (G1) — `walking · 4/6 hops` while active, the
      ending reason for a few seconds after, nothing when idle.
      Evidence: 2.1% of catalog entries occupy the status bar; the ones that do put live detail in it.
      Accept: the chip is never blank while a state runs; it never shows `0/0`.
      Built: `chip(payload)` in `desktop/plugin.js` renders `served/dose unit`, `N picked`
      for explore, and nothing when idle; guard in `tests/test_cockpit_pane.py`.

## Phase 2 — the map earns the state

- [ ] **T0 · decide D5** — delete the `SCENES`/`ascii3d` kit, or adopt it as the signature vocabulary.
      No code until this is decided.
- [ ] **T4 · per-state signatures** — daydream anchors, dream arc between project clusters, doomscroll
      scatter, unstuck gap halo; walk trail and explore picks stay.
      Accept: each signature appears only while its state runs, and the dream arc is drawn only from a
      real relation the payload carries.
      Verify: stills per state; no invented geometry.

- [ ] **T5 · the receipt card** — the pane's corner note becomes an end-of-state card (T2's contents).
- [ ] **T9 · a read-only states panel** (G2) — last N states: served/seen, ending reason, turns,
      and the account line. Modelled on `session-lens`: read-only, no new writes, counts not content.
- [ ] **T10 · a blocked tool says why** (G6) — `transform_tool_result` annotates a refusal with the
      state and the rule. Evidence: 37 of 1,379 community plugins use this hook; we use none.

## Listing work — independent of code, do before the next release

- [x] **L1 · disclosure** — already present on the live entry and precise; no work needed.
      (Earlier claim retracted: the listing does carry one.)
- [ ] **L2 · release the current README** — the marketplace renders the README at the pinned sha,
      and that sha predates the one-state, four-ending, no-expiry rewrite. Until a release is cut,
      the page says five states, one-second pacing, and an `expired` ending. No engine work.
- [ ] **L3 · shelf** — `category: desktop` (409 entries) instead of `general` (119, mixed with
      themes and telemetry). A plugin whose product is two desktop panes belongs on the desktop
      shelf.
- [ ] **L4 · card copy** — one sentence that names `/explore` and the cockpit, and uses the words
      people search: `state`, `cognitive`, `creativity`. Evidence: `cognitive` and `creativity`
      return 0 results across 2,311 entries; `state` returns 448 with us buried.
- [ ] **L5 · screenshots** — add a cockpit image and the states table; the three current images
      pre-date the cockpit.

## Phase 3 — the record

- [ ] **T6 · outcomes journal** — `.antemuse/outcomes.jsonl`, `state(action='outcomes')`, last three in
      the pane.
- [ ] **T7 · a states page** — catalogue with contract, dose, product, and an enter button.
- [ ] **T11 · cost counts** (G7) — `post_api_request`: tokens and latency per state, counts only,
      surfaced in T9. Only if T9 exists to show it.

## Verification for every phase

```
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) uvx --with-requirements requirements-test.txt \
  --quiet pytest tests/ -q
```

and the harness: `python3 tools/cockpit_harness.py` (26 checks today).

## Not doing

- model calls on the state path
- quoting memory text anywhere a person can read it
- approval cards
- new states, new doses
