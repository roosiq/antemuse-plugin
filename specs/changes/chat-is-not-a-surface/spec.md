# chat-is-not-a-surface

**Status:** LIVE (0.9.36)
**Kind:** surface removal + message-chain correctness
**Date:** 2026-11-10

## What changed

1. **Chat carries no visualization.** The picture lives in the desktop app's Antemuse pane.
   Removed: the card posted on state entry, `state(action="card"|"image")` returning artwork,
   `/state picture` in chat returning a card, and the two settings that controlled them
   (`picture_enabled`, `picture_narrow`). A terminal is not chat: `/state picture` in a tty
   still runs the takeover, which draws locally and sends nothing.
2. **State material belongs to one message chain.** `engine.inject(session)` builds a state
   block only for the session that entered the state (an empty owner reaches everyone). A
   walk started in one chat used to inject its concepts into every other chat's next turn.
3. **`/return` is owner-only.** Typed in a session that does not own the running state it now
   changes nothing and says where the state lives; before, it ended the state and only said
   the account stayed elsewhere.
4. **`suggest_autofollow`** (bool, default `false`) — the one setting that can start a move:
   when on, the state a suggestion names is entered instead of only named. It never stacks on
   a running state, the suggestion line is still posted, and the move is unchanged.
5. **Bounds declared, not just enforced.** The integer settings carry `min`/`max` in the
   manifest equal to `core/settings.py`'s clamps; a test fails if either side moves alone.

## Non-goals

- No change to doses, ceilings, directives, contracts, residue labels, or tool policy.
- The card renderer (`core/surfaces.py`) is retained for the terminal takeover and proofs.
- No new state, command, or model call.

## Acceptance

| claim | evidence |
|---|---|
| entering a state posts nothing | `tests/test_unstuck.py::test_entering_a_state_posts_nothing_into_the_chat` |
| `card`/`image` answer with the pane pointer | `tests/test_command_surface.py` (state tool surface) |
| a walk does not leak into another chat | `tests/test_states.py::test_a_walk_does_not_leak_into_another_chats_turn` |
| a bystander cannot `/return` someone's state | `tests/test_states.py::test_a_bystander_cannot_return_someone_elses_state` |
| auto-follow is off unless asked | `tests/test_settings.py::test_following_a_suggestion_is_off_unless_asked` |
| manifest and code agree on defaults and bounds | `tests/test_settings.py::test_the_manifest_and_the_code_agree_on_every_default` |

## Must not change

§18 constraints stand unchanged: five states, dose-based endings, ceilings, turn budgets,
directives' mechanics, contracts' field set, residue labels' field set, journal cap 60,
residue cap 3, two-turn report decay, hook contracts, `/return` and `CONTROL_TOOLS`.
