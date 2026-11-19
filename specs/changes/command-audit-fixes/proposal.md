# Command audit fixes

## Goal

Six slash commands (`/daydream`, `/doomscroll`, `/dream`, `/unstuck`, `/explore`, `/return`) were
audited one by one by independent probers, and the four serious findings were reproduced by hand
before any code changed. This change fixes them, in privacy-first order, and makes the copy match
what the code actually does.

## Why

Two of the defects put one person's conversation in front of another; one put untrusted feed text on
disk against the state's own contract; one let a foreign chat write into someone else's account. The
rest made the plugin say things that were not true: an ending drawn twice, a "connection" between two
unrelated things, and `/unstuck` recommending the change the person had just finished — the very
thing that stuck them.

## Non-goals

- No new state, no dose retuning, no change to `/walk`'s act semantics (0.12.0).
- No feed suitability classifier. The doomscroll lanes are named honestly instead of filtered by a
  keyword guess.
- No change to the tool policy: tools stay open unless the entry passes `block: true`. Where a
  directive implied otherwise, the directive is corrected, not the policy.
- No multi-project dream. `projects()` resolves one repository; the copy now says so.

## Findings and fixes

1. **Cross-chat material (critical).** `recall.remember()` stored no session, and daydream's provider
   read the whole profile-wide ring. Reproduced: three turns marked `ALICE PRIVATE` recorded in one
   chat were served as `bob`'s daydream material. Fixed by stamping each recorded turn with its
   session, filtering `recall.recent(..., session=...)`, threading the owner through
   `sources.ready()` and the provider call, and scoping the seeding pool the same way.
2. **Untrusted feed text on disk (high).** `delivery_trace.log` wrote the delivered lines verbatim,
   so a doomscroll headline was persisted although the state, journal and ledger excluded it. Fixed
   by writing a 12-character digest of each unit's material key instead of the line.
3. **Foreign picks (high).** `note_pick()` checked only that an explore was running. Reproduced:
   session `stranger` added a concept to `owner`'s explore. Fixed by refusing a caller that is not
   the owning chat.
4. **Ending drawn twice (medium, four commands).** The reply hook appends `— <key> · …` and the
   annotation then appends `— <label> ended · …`; `_is_footer_line()` recognised neither the key nor
   the account form, so the first line survived the strip. Fixed by recognising a footer whose head
   is a state key or label.
5. **`/unstuck` recommends the last change (high).** The provider rendered `subjects[0]` — the newest
   commit — as "continue the last change". Fixed by grounding the direction in an earlier subject and
   naming the newest as the thing to step away from, with an honest single-commit branch.
6. **Dishonest pairing and copy (medium).** Daydream labelled every pair `JOINED` and invented a
   possibility from "the gap between them"; dream invented "the same unfinished shape". Both now say
   plainly when nothing is shared. Dream's "across projects" copy and doomscroll's "professional
   material is not in scope" claim were corrected to match the code.

## Affected paths

- `core/recall.py`, `core/sources.py`, `core/engine.py`, `core/seeding.py`, `core/states.py`
- `__init__.py` (turn recording carries the session)
- `tests/test_command_audit_fixes.py`, `tests/test_state_unstuck.py`
- `specs/product/states.md`

## Verification

```bash
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q
```

Reversion proof: with `core/` and `__init__.py` stashed, all six new audit tests fail; restored, they
pass.

## Must not change

- `/walk` completing inside its command, and its six-hop account.
- The tool policy (`block: true` is the only thing that closes tools).
- `/explore` having no dose, no clock, and no agent-side picking.
- One account and one ledger row per ending.
