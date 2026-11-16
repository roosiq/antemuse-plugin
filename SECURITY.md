# Security

## Runtime surface

`__init__.py` registers `/walk`, `/explore`, and `/return`; four turn/tool hooks
(`pre_llm_call`, `pre_tool_call`, `transform_llm_output`, `post_tool_call`); four
session-boundary hooks; and one tool, `state(action=...)`. `core/states.py` defines
only the `walk` agent state. `/explore` is separate, person-driven, and ends on
`/return`.

The runtime imports no network client and starts no subprocess. The state path makes
no model call. Development experiments are not imported by plugin registration.

`core/history.py` may scan Hermes `state.db` through SQLite read-only mode. An
automatic scan is limited to the previous 14 days, 300 user/assistant messages, and a
2-second budget; it is globally limited to once per 30 minutes. It records extracted
terms and message identifiers in the ledger, not message bodies. It does not read
`config.yaml`, the Hermes authentication JSON file, `MEMORY.md`, or `USER.md`.

## Persistence

The plugin data directory (or `ANTEMUSE_STATES_HOME`) contains:

- `state.json`: active state, residue, and bounded state-journal entries.
- `recent_turns.json`: at most 24 short current-turn text entries, each capped at 400
  characters.
- `concepts.db`: the SQLite ledger of extracted terms, scan cursors, and related
  metadata.
- `walks/*.json`: user-defined walk specifications.
- `walk_cursor.json`: walk continuation data.

When a project is detected, its `.antemuse/walk_cursor.json` holds the project-local
walk cursor. Files are created with the process's normal filesystem permission
defaults; the plugin does not relax permissions or call `chmod`.

## Reporting

Report vulnerabilities privately through a GitHub security advisory for
`roosiq/antemuse-plugin`, or to the email address on the repository profile. Include
the version, command or tool call, and observed behavior. Do not include credentials,
private session text, or local plugin data.

## Scope

In scope: `__init__.py`, `core/`, `desktop/`, `plugin.yaml`, and the plugin data path.
Out of scope: Hermes itself, bundled WordNet data, and development-only experiments.
