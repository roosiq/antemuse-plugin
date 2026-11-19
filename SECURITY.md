# Security

## Runtime surface

`__init__.py` registers seven public commands: `/walk`, `/daydream`, `/doomscroll`,
`/dream`, `/unstuck`, `/explore`, and `/return`; four turn/tool hooks
(`pre_llm_call`, `pre_tool_call`, `transform_llm_output`, `post_tool_call`); four
session-boundary hooks; and one tool, `state(action=...)`. `core/states.py` defines
five agent states. `/explore` is separate, person-driven, and ends on `/return`.

- **Runtime network:** no network client is used except doomscroll's gated public feed
  fetch. The restored state path otherwise starts no network client and makes no model call.

## Data access and trust boundaries

- **Daydream reader:** `daydream` reads the plugin's own bounded recent-turn history,
  filtered to the chat that started the state. It does not read `MEMORY.md`, `USER.md`,
  or any Hermes memory backend, and it does not write to Hermes memory or configuration.
- **Dream readers:** `dream` reads the same session-filtered recent turns, then the
  concepts the ledger served that chat, and falls back to local git commit subjects when
  the chat is inside a repository. Git is optional: dream starts without it. It never
  reads commit bodies, transcripts, notes, or repository credentials, and it never reads
  another chat's turns or ledger rows.
- **Doomscroll feed:** `doomscroll` fetches its gated public feed lane. Feed text is
  untrusted data, explicitly labelled as material rather than instruction, and is never
  persisted in the journal, ledger, account, or another durable store. Its default
  behavior is enabled; hosts can disable it with the `doomscroll_feed` setting, which
  makes the state fail with a named reason.
- **Session scan:** `core/history.py` may scan Hermes `state.db` through SQLite
  read-only mode. An automatic scan is limited to the previous 14 days, 300 user/assistant messages,
  and a 2-second budget; it is globally limited to once per 30 minutes. It records
  extracted terms and message identifiers in the ledger, not message bodies. It does not read
  `config.yaml` or the Hermes authentication JSON file.
- **Subprocesses:** the optional git-subject reader used by dream and unstuck invokes git with an argv list,
  never a shell. No subprocess is otherwise started by the restored state path.
- **Credentials:** none requested, read, stored, refreshed, or sent. There is no
  `requires_env` and no OAuth.

## Persistence

The plugin data directory (or `ANTEMUSE_STATES_HOME`) contains:

- `state.json`: active state, residue, and bounded state-journal entries.
- `recent_turns.json`: at most 24 short current-turn text entries, each capped at 400
  characters and stamped with the session it was said in. A state reads only its owning
  chat's entries (plus unattributed ones); it never serves another chat's turns.
- `concepts.db`: the SQLite ledger of extracted terms, scan cursors, and related
  metadata.
- `walks/*.json`: user-defined walk specifications.
- `walk_cursor.json`: walk continuation data.
- `delivery_trace.log`: one line per delivery decision — counters and a 12-character digest
  of each unit's material key. No material text is written: not the person's turns, and not
  doomscroll's untrusted feed items. Capped at 200 lines once it passes 64 KB.

When a project is detected, its `.antemuse/walk_cursor.json` holds the project-local
walk cursor. Files are created with the process's normal filesystem permission
defaults; the plugin does not relax permissions or call `chmod`.

## Reporting

Report vulnerabilities privately through a GitHub security advisory for
`roosiq/antemuse-plugin`, or to the email address on the repository profile. Include
the version, command or tool call, and observed behavior. Do not include credentials,
private session text, local memory files, or local plugin data.

## Scope

In scope: `__init__.py`, `core/`, `desktop/`, `plugin.yaml`, and the plugin data path.
Out of scope: Hermes itself, bundled WordNet data, development-only experiments, and
public feed content.
