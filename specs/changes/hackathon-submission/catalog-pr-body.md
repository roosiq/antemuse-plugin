# Catalog PR body — NousResearch/hermes-agent

Title: `plugin-catalog: add antemuse`

## What this adds

One file, `plugin-catalog/antemuse.yaml`, for **antemuse**, a community plugin that
lets a Hermes agent take a bounded state — walk, daydream, doomscroll, dream, or
unstuck — while it keeps working. A state injects material into the conversation
that started it, can close tools when the entry asks for it (`block: true`), ends
by its dose, and comes back with an account. The person watches it as a live
concept graph in the desktop app's Antemuse pane.

Surfaces used: one tool (`state`), eight hooks (`pre_llm_call`, `pre_tool_call`,
`post_tool_call`, `transform_llm_output`, and the four session-boundary hooks),
slash commands, a bundled skill, a desktop pane (`desktop/plugin.js`, SDK only),
a dashboard route, and a manifest `config_schema` rendered by Settings ▸ Plugins.

## Pin

- Repo: https://github.com/roosiq/antemuse-plugin
- SHA: `PIN_SHA_40`
- Verified at that commit, on a clean clone:
  - `pytest -q` → **700 passed, 1 skipped** (after `npm ci`)
  - `hermes plugins validate . --install-deps --json` → **16/16 checks ok,
    `warnings: []`**, security scan `safe`
  - `hermes plugins doctor` → **1 tool, 8 hooks**
  - the entry loads through `hermes_cli.plugin_catalog.load_catalog`

## Disclosures (rule 13)

| behaviour | where |
|---|---|
| `doomscroll` fetches public RSS/JSON feeds over `urllib` (8 s timeout, no credentials) and places feed text in the agent's context as untrusted material | `core/sources.py`, `core/social.py` |
| `daydream` reads the operator's Hermes memory files (`MEMORY.md`, `USER.md`) | `core/sources.py`, `core/history.py` |
| session scan reads up to 300 recent messages from the Hermes session store, once per session, in a background thread; `ANTEMUSE_NO_SCAN=1` disables it | `core/history.py` |
| writes go only to the plugin data dir and `<repo>/.antemuse/` | `core/storage.py` |
| the terminal takeover may spawn `node` to rasterise the scene; falls back to cached frames without it | `core/tui.py` |
| `suggest_autofollow` (default **off**) lets a suggestion enter the state it names; otherwise the plugin never starts a state on its own | `__init__.py::_follow` |
| a state is scoped to the conversation that entered it; `/return` from another conversation changes nothing | `core/engine.py::inject`, `stop` |
| no pictures or media are posted into chat | `__init__.py::_pane_only` |
| dev scripts under `tools/` make network calls and spawn browsers; none is imported at registration | `tools/` |
| no credentials, no telemetry, no self-updater, no model call on entry, exit, expiry or rendering | — |

## Claim discipline

The plugin claims a mechanism: material in the right conversation, tool policy
when asked, dose-bounded endings, an account on return. It does **not** claim
better or more creative output; its own measurements found no ideation effect
after length control (32 pairs per condition, p = 0.365). The research harness
and raw runs are not in the published tree.

## License

MIT, Copyright (c) 2026 Ryan Cook. Bundled three.js is MIT; `data/collider/` is
CC BY 4.0 with attribution in the tree.
