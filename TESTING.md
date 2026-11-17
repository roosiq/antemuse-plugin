# Testing

## Requirements

- Hermes Agent 0.21.6 or newer.
- Python 3.11+.
- `nltk` with the WordNet corpus for live walk coverage.
- Optional: `node` and `npm` for the desktop-pane harness.

## First run

```bash
hermes chat -q '/walk'       # six hops, tools open, work continues
hermes chat -q '/return'     # end it and keep the account
```

The seven slash commands are `/walk`, `/daydream`, `/doomscroll`, `/dream`,
`/unstuck`, `/explore`, and `/return`.

- `/walk` enters the ambient six-hop state: `WALKING · 6 hops · work continues · the frame is elsewhere · different on return`.
- `/daydream` enters two memory-pair deliveries; `/dream` enters two local-git-subject recombinations.
- `/doomscroll` enters three gated public-feed deliveries; `/unstuck` enters one direction from history and the graph.
- `/explore` is person-driven and open-ended: `EXPLORING · 0 picks · you fly · you choose · it ends when you end it`.
- `/return` ends the active state or explore and preserves its account.

There is no `/break`, `/mood`, `/note`, `/watch`, or `/states` command. Those are
actions on the `state` tool.

## Suite

Run this exact command from the repository root:

```bash
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q
```

The suite uses a temporary state home. It verifies state doses, delivery ownership,
tool policy, ending accounts, residue, ledger rows, command surface, person-driven
explore, and docs consistency.

## Additional checks

```bash
python3 tools/examples.py --check
hermes plugins validate . --install-deps
hermes plugins doctor antemuse
```

`tools/examples.py` generates `docs/EXAMPLES.md` from the real engine. It includes
one worked example for each agent state.

## Where it writes

- State, journal, residue, cursors: `~/.hermes/plugin-data/antemuse/` (or
  `ANTEMUSE_STATES_HOME` during tests).
- Per-project walk data: `<your repo>/.antemuse/`.
- `/explore` writes the concepts a person picks to the concept ledger.

No credentials or API keys are required for a state.

## Known limits

- State is profile-wide, while delivery and accounts are owned by the session that entered it.
- The desktop app is required to see the map or cockpit; chat and terminal show text only.
- `spark`, `keep`, and the exploration library are experimental and gated behind
  `experimental.enabled`.
- A state entered with `block: true` can restrict tools for the profile until it ends.
