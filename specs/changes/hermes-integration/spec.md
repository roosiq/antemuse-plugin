# Hermes integration — use the host's interfaces, not our own

Status: **verified** 2026-11-08. Owner: Ryan Cook.

## Goal

Any Hermes provider works with this plugin through that provider's default interface:
no vendor SDK, no plugin-owned key, no assumed home directory, no assumed memory
backend. A provider swap must be a config change, never a plugin change.

## Requirements

1. Every model call goes through `ctx.llm` (`PluginLlm`) with no `provider=`/`model=`
   override, so the host's active model and credentials are used.
2. Every `task=` value names an auxiliary task the plugin registered itself; an
   unregistered key raises in the host and must never be reachable.
3. No module imports a provider SDK or reaches the network for model traffic.
4. Paths resolve through `plugins.plugin_storage.plugin_data_dir` /
   `hermes_constants.get_hermes_home`, honouring `HERMES_HOME` and profiles.
5. Hooks used are members of the host's `VALID_HOOKS`; per-turn text rides
   `pre_llm_call` (appended to the user message, never the system prompt).
6. Memory stays host-owned: the plugin neither writes memory nor registers a memory
   provider, and any source it cannot reach is named as a limitation.
7. Because Hermes exposes no plugin-facing memory read, daydream's material comes from
   a **provider-neutral** source first: the last turns of the live conversation, captured
   from the host's `pre_llm_call` payload and kept in a bounded ring. The built-in
   `MEMORY.md`/`USER.md` files are enrichment when they exist, never the only source.

## Acceptance criteria

1. `tests/test_hermes_integration.py` passes, pinning 1–4 plus the `user_message` path.
2. Automatic journalling fires from the host's real kwargs (`user_message`,
   `conversation_history`), including Anthropic-style content blocks.
3. `docs/hermes-integration.md` records one verdict per mechanism with the host source
   line it was checked against.
4. Daydream's memory failure names the active provider when it is external.
5. With `memory.provider: hindsight` and an empty data dir, a daydream still produces two
   memories from the conversation that just happened — and says so if it cannot.

## Non-goals

Not a memory provider. Not a context engine. Not a dashboard replacement. No change to
state semantics, timing, or rendering.

## Must not change

`/return`, `CONTROL_TOOLS`, state definitions, durations, turn budgets, cadences, the
injection format, the no-words rule on the human card, and the rule that rendering never
needs a model call.
