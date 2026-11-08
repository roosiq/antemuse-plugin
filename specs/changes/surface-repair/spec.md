# Surface repair — the person's card shows the state it is in

Status: proposed 2026-11-08 by the controller, from `docs/spec.md` §14 items 15–18.
Owner: Ryan Cook. Scope: `/home/ryan/antemuse/plugin` surfaces and the spec record.

## Goal

Fix the four defects found by running the plugin rather than reading it. Every
one of them is invisible to the current test suite because the suite tests the
encoders as encoders and never asserts what a person receives.

1. **The chat card is nearly empty.** §14.15. `art()` maps a 1600×420 frame with
   mean luminance 11.9–15.2 straight onto an eight-step ramp whose first visible
   character needs ~32/255, so a walk card carried two rows of two dots and the
   PNG carried 84 bright pixels out of 90,692.
2. **The card serves the whole journal.** §14.16. `watch_state()` hands every
   renderer all 60 entries, across sessions, so a walk begun this morning
   rendered steps recorded the previous evening as if current.
3. **Card frames and card writes use different homes.** §14.17. `art()` reads
   `data_dir()/three_frames`; `snapshot_path()` writes to
   `project_dir() or data_dir()`, so a card can be built from one directory and
   saved into another.
4. **The verification record is stale.** §14.18. `docs/spec.md` §13 records 107
   tests; the suite has 584.

## Non-goals

- No words on the human surface. BR-5 forbids text on the card, and the existing
  tests `test_card_is_only_a_picture` / `test_idle_card_is_still_only_a_picture`
  enforce it. The defect is fixed by making the picture visible, not by adding a
  caption. If a caption is ever wanted it is a BR-5 change, decided separately.
- No new state, tool action, command, hook, model call, or storage location.
- No change to journal cap 60, residue cap 3, two-turn decay, tool policy,
  directives, contracts, residue labels, or `/return`.

## Contract

- `art()` normalises each frame against its own sampled luminance: the 2nd and
  99.5th percentile of the resized cells become the ends of the ramp. Deterministic
  for a given frame; no random element; no dependence on the previous frame.
- At least 8% of the card's art cells are non-space for every scene bank, and no
  scene becomes a solid block (density stays under 60%).
- The journal a renderer sees is this session's, and inside a state, this state's
  window (`at >= entered_at`). Entries stamped with another session never appear.
- `snapshot_path()` writes under `storage.data_dir()`, the same home `art()`
  reads frames from, for every environment (including `ANTEMUSE_STATES_HOME`).
- `docs/spec.md` §13 carries the 2026-11-08 verification and §14 marks 15–18
  resolved with what was done.

## Acceptance

- New tests: art density per scene; art determinism; journal scoping across
  sessions; snapshot and frames resolve under one home.
- Existing tests `test_card_is_only_a_picture` and
  `test_idle_card_is_still_only_a_picture` still pass unchanged.
- Full suite green twice; `hermes plugins doctor antemuse` still `1 tool(s), 8 hook(s)`.

## Affected paths

`core/surfaces.py`, `core/engine.py`, `tests/test_surfaces.py`,
`tests/test_states.py`, `docs/spec.md`.

## Verification

```bash
cd /home/ryan/antemuse/plugin && env -u PYTHONPATH NLTK_DATA=/home/ryan/nltk_data \
  ANTEMUSE_STATES_HOME=$(mktemp -d) uvx --with pillow --with nltk --quiet pytest tests/ -q
```
