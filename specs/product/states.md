# The one agent state

## Product surface

Antemuse has one agent state: `walk`.

A walk is a bounded six-hop WordNet traversal. It is an ambient change in frame, not
a source of prompt material: the pane can show the path, but the agent continues the
person's task without receiving hop text as evidence. Tools remain open unless the
entry explicitly requests `block: true` and an optional `allow` list.

`/explore` is not an agent state. It remains a person-driven cockpit mode: it has no
provider or dose, the person selects concepts, and only `/return` ends it.

## Walk contract

| command | dose | tools | material in model turn | ending |
|---|---:|---|---|---|
| `/walk` | 6 hops | open by default | none | complete, dry, failed, or returned |
| `/explore` | open | open | the person's picks are accounted, not injected | returned |

A walk ends `complete` only after all six hops have been delivered and shown. It ends
`dry` after no new material is available, and `failed` when its provider cannot
produce material. Each ending writes exactly one account and one `moves` ledger row.
There is no clock ending.

## Acceptance evidence

- `tests/test_states.py`: tool openness/narrowing, session ownership, residue, account privacy.
- `tests/test_state_delivery.py`: dose accounting, pane-poll limits, repeated material, ownership.
- `tests/test_semantic_states.py`: units, end reasons, account posting, state wording.
- `tests/test_moves_ledger.py` and `tests/test_ledger_writes.py`: one ledger row per ending.
- `tests/test_e2e_states.py`: public walk entry through the e2e runner.
- `tests/test_explore_state.py`: explore remains person-driven and open-ended.

## Non-goals

- No replacement agent states for `daydream`, `doomscroll`, `dream`, or `unstuck`.
- No change to `/explore` behaviour.
- No automatic state entry or timer-based exit.
