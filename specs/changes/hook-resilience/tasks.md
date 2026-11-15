# Hook resilience — tasks

## T1 — A policy hook answers, or says nothing

- [x] `_pre_tool_call` catches exceptions from `engine.policy`, logs the failure, and
  returns `None` to allow the call.
- Evidence: `test_a_broken_policy_decision_allows_the_call`,
  `test_an_open_ended_state_cannot_wedge_the_tool_channel`.

## T2 — Residue decay tolerates older records

- [x] `engine.tick()` coerces legacy residue entries to dictionaries before decay.
- [x] Missing `turns_left` values default safely.
- Evidence: `test_a_legacy_residue_entry_does_not_crash_the_tick`.

## T3 — Every supported mode survives the hook reads

- [x] The walk hook path is covered through policy, tick, delivery, injection,
  annotation, and status.
- [x] The separate open-ended explore mode is covered at the boundary.
- Evidence: `test_every_state_survives_the_hook_paths` and
  `test_an_open_ended_state_cannot_wedge_the_tool_channel`.

## Verification

```bash
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with-requirements requirements-test.txt --quiet pytest tests/test_hook_resilience.py -q
```

## Must not change

- `block: true` and `allow:` still narrow tools when requested.
- `/return` remains exempt from the block.
