# Hook resilience — a state record can never cost a turn

Change id: `hook-resilience`

## Goal

A malformed or legacy state record can degrade plugin output, but it can never take
the host tool channel down.

## Root cause

A policy-hook exception propagated into the host, while older residue entries could
lack `turns_left` or be bare strings. Both conditions made ordinary hook reads unsafe.

## Scope

- `_pre_tool_call` catches policy errors, logs them, and allows the tool call.
- `engine.tick()` normalizes legacy residue records before decay.
- Hook reads are covered for the sole agent state, `walk`, and the separate open-ended
  explore mode.

## Non-goals

- No migration of existing state records.
- No change to requested tool restrictions: `block: true` and `allow:` still apply.
- No change to person-driven explore behaviour.

## Acceptance

See `acceptance.md` and `tasks.md` for executable evidence.
