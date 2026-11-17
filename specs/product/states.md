# The five agent states

## Product surface

Antemuse has five agent states: `walk`, `daydream`, `doomscroll`, `dream`, and
`unstuck`. Each is bounded by a dose, never a clock. It ends `complete` only after its
dose has been delivered and shown, `dry` when no new material remains, `failed` when
its provider cannot run, or `returned` when `/return` ends it. Each ending writes one
account and one `moves` ledger row.

`/explore` is not an agent state. It remains a person-driven cockpit mode: it has no
provider or dose, the person selects concepts, and only `/return` ends it.

## State contracts

| command | dose | tools | material in model turn | what the chat is told | ending |
|---|---:|---|---|---|---|
| `/walk` | 6 hops | open by default | none; its graph path is pane scenery | its own hop trail (`record→clock out [far] → …`) | complete, dry, failed, or returned |
| `/daydream` | 2 pairs | open | two memories from the person's own history, what they touch, one possibility | how many joined, never which — the material is the person's own turns | complete, dry, failed, or returned |
| `/doomscroll` | 3 items | `web_search`, `web_extract`, `read_file`, `search_files`, `browser_exec` | a gated random feed lane, labelled untrusted material | the count only; feed text is untrusted and never spoken or stored | complete, dry, failed, or returned |
| `/dream` | 2 recombinations | open | local git commit subjects only, never transcripts or notes | the concept labels it served | complete, dry, failed, or returned |
| `/unstuck` | 1 direction | `read_file`, `search_files` | one recommendation from history and one concept-graph edge | the concept labels behind the direction | complete, dry, failed, or returned |
| `/explore` | open | open | the person's picks are accounted, not injected | the count of picks | returned |

Walk moves on its declared graph provider: the bundled provider is WordNet; a corpus
graph moves on the user's own material and its path is only as meaningful as that
corpus; when the provider is not WordNet, the journal and account name it.

Every state leaves the tools open by default: a state changes the frame the agent works in, and
taking tools away is a second decision the caller makes with `block: true` (and `allow` narrows it
further; with no `allow` the state's own recommended set applies). `/return` is always available.
only their declared tools. `walk` stays open by default; `block: true` and `allow`
may narrow an entry further. `/return` is always available.

Doomscroll feed text is untrusted data, never instruction, and is not written into the
journal, ledger, or account. Its feed is enabled by default; a host may disable it with
`doomscroll_feed`, which ends the state `failed` with a named reason rather than
substituting material.

## Acceptance evidence

- `tests/test_states.py`: registry, tool policy, session ownership, residue, and account privacy.
- `tests/test_state_delivery.py`: dose accounting, repeated material, endings, and ownership.
- `tests/test_semantic_states.py`: units, end reasons, account posting, and state wording.
- `tests/test_moves_ledger.py` and `tests/test_ledger_writes.py`: one ledger row per ending.
- `tests/test_e2e_states.py`: public state entry through the e2e runner.
- `tests/test_explore_state.py`: explore remains person-driven and open-ended.

## Non-goals

- No change to `/explore` behaviour.
- No automatic state entry or timer-based exit.
- No second graph, scoring model, or dose retuning.
