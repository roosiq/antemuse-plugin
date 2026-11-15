# Hook resilience — acceptance

| Criterion | Evidence |
| --- | --- |
| A broken policy allows the call instead of raising | `test_a_broken_policy_decision_allows_the_call` — `policy` raises `KeyError('turns_left')`; the hook returns `None`. |
| Every agent-state hook path survives | `test_every_state_survives_the_hook_paths` — parametrised over the sole `walk` state through `policy`, `tick`, `note_turn`, `deliver_if_due`, `complete_if_dosed`, `inject`, `annotate`, and `status`. |
| Explore cannot wedge the channel | `test_an_open_ended_state_cannot_wedge_the_tool_channel`. |
| A legacy residue entry cannot raise | `test_a_legacy_residue_entry_does_not_crash_the_tick`. |
| Tool narrowing still works | `test_an_entry_may_narrow_the_set_without_editing_the_state`. |

A failed policy computation must be visible in logs but cannot cost the host tool
channel or a turn.
