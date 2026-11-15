# Acceptance, as built

| Criterion | Evidence |
| --- | --- |
| `/explore` registered | `tests/test_command_surface.py::removed-state coverage`, `tests/test_runtime.py::test_the_commands_are_registered` |
| Cannot be closed by the engine | `tests/test_explore_state.py::removed-state coverage` — three turns, a delivery, still `explore` |
| Picks filed from the pane, ignored outside | `tests/test_explore_state.py::removed-state coverage`, `::removed-state coverage`, harness `shoot: the picks are filed with the plugin` |
| `/return` names the picks | `tests/test_explore_state.py::removed-state coverage`; a live run printed `EXPLORING ended · explore · 3 shot(s) on 2 concept(s) · bookshelf ×2, legacy ×1` |
| No hook can be taken down | `tests/test_hook_resilience.py` — every state walked through `policy`/`tick`/`inject`/`annotate`/`status`, a broken `policy` returning `None` instead of raising, and a legacy residue entry surviving the tick |
| State line does not promise a countdown | `tests/test_explore_state.py::removed-state coverage`; harness `pane: an open-ended state says you end it` renders `3 picked · you end it · all tools` |
| A pick moves the map | `tests/test_explore_state.py::removed-state coverage`; measured against a copy of the live ledger: `abrasion` and `abrasive` went `w 0.000 → 1.000` and the graph's `lit` went `0 → 2` after one volley |
| The state offers its surface | `tests/test_cockpit_pane.py::test_an_explore_points_at_the_cockpit` — the dock pane renders "open the cockpit" while exploring, and the status chip navigates to `/{ID}/cockpit` |
| The routes the pane calls work over HTTP | `tests/test_explore_api.py` — `POST /picks` files 3 shots on 2 concepts, a non-list body is 400, the state survives six polls, and picks stop landing after the explore ends |

## Incident this change closes

The failure has its own change now — `../hook-resilience/` — because it is about every
state and every turn, not about flying a map. Kept here as the record of how it was found.

Entering `/explore` in the live store made every tool call in the session fail with
`pre_tool_call plugin callback _pre_tool_call raised KeyError: 'turns_left'` — the policy
hook raised, and a raising policy hook blocks the whole tool channel, not just the tools
a state means to block. Two fixes: `_pre_tool_call` now catches and allows (logging the
cause), and `tick()` no longer indexes `turns_left` on residue entries that may not carry
it (legacy strings, older reports). Both are covered above.

## Known limits

- A pick of a label that is not in the projected graph counts in the account but cannot
  light anything; the map only knows concepts it has positions for.
- One pick takes a node's weight straight to the top of the scale, so a single hit reads
  as strongly as a long session's worth. If that is too eager, weight it by count.
- Plugin Python loads when the gateway process starts, so the fixed hooks take effect
  after the next gateway reload — not in the process that was running during the incident.
