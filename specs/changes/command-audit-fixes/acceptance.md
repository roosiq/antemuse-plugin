# Acceptance

Each item was observed in a live probe, then fixed, then held by a test that fails without the fix.

| # | criterion | evidence |
|---|---|---|
| 1 | A daydream in chat B never contains chat A's recorded turns | `test_daydream_reads_only_its_own_chats_turns` — B is refused with no turns of his own; after his own turns the block contains `pricing` and no `ALICE` |
| 2 | Walk seeding does not read another chat's words | `test_walk_seeding_does_not_read_another_chats_words` |
| 3 | No delivered material text reaches `delivery_trace.log` | `test_the_delivery_trace_holds_no_material` — trace shows `got=1` and a digest, never `EXFILTRATE` or `evil.example` |
| 4 | A foreign chat cannot add picks to another chat's explore | `test_picks_from_another_chat_are_refused` — `{'ok': False, 'added': 0, 'reason': 'another session is exploring'}` |
| 5 | One reply carries one ending | `test_an_ending_is_drawn_once` — exactly one line begins `—`, and it is the `ended ·` account |
| 6 | A pair with nothing in common is not called joined | `test_a_pair_with_nothing_in_common_is_not_called_joined` — `APART`, `possibility: none`, no `JOINED` |
| 7 | A recombination with nothing shared says so | `test_a_recombination_that_shares_nothing_says_so` — `adjacent … nothing yet` |
| 8 | `/unstuck` steps away from the change just finished | `test_unstuck_steps_away_from_the_change_just_finished` — `not another pass at finish design boundary · take add design boundary from a different angle` |
| 9 | A single-commit repository is handled honestly | `test_unstuck_delivers_one_direction_from_history_and_graph` — `only one change in history (…)`, still names `graph edge:` |
| 10 | The whole suite still passes | 946 passed, 6 skipped |
| 11 | The new tests bite | with `core/` and `__init__.py` stashed: 6 failed; restored: 6 passed |

## Copy corrected to match the code

- `/dream` speaks about *this project's* recent work; `projects()` resolves one repository.
- `/dream`'s directive says tools stay available and nothing here needs one, instead of implying
  they are closed. Only `block: true` closes tools.
- `/doomscroll` names its three fixed lanes and admits an item may be a technical headline, instead
  of claiming professional material is filtered out.

## Residual, stated rather than hidden

- A doomscroll item already counted in `served` is lost if the process restarts: the feed payload is
  memory-only by design while the count is durable, so a resumed run can finish 3/3 having shown two.
  Not fixed here; it needs a decision about whether the count or the ephemerality wins.
- `GET /state` still projects the profile-wide active state to any requesting session, so another
  desktop session can see that a chat is exploring and its pick count. Ownership of *writes* is
  fixed; visibility of the summary is not.
