# Hermes integration — the interfaces we use, and the ones we were getting wrong

Status: **verified** 2026-11-08. Every row was checked against the host source in
`~/.hermes/hermes-agent`, not against our own helpers.

The requirement behind this audit: **any provider, by its default interface.** Nothing
in the plugin may assume a model vendor, a key, a home directory, or a memory backend.
Where the plugin could not reach an interface, the limitation is named in the product
rather than papered over.

## Verdicts

| Mechanism | Host interface (evidence) | What the plugin does | Verdict |
|---|---|---|---|
| Tool | `PluginContext.register_tool(schema=…, handler=…)` — `hermes_cli/plugins.py:462` | one `state` tool, 14 actions, JSON schema, `check_fn`-free | **correct** |
| Commands | `register_command(name=…, handler=…, description=…)` — `:657` | five: the four states and `/return` | **correct** |
| Hooks | `VALID_HOOKS` — `hermes_cli/plugins.py:108` | `pre_llm_call`, `pre_tool_call`, `post_tool_call`, `transform_llm_output`, `on_session_end/finalize/reset/delete` — all in the set | **correct** |
| Per-turn injection | `pre_llm_call` return string → appended to the *user message*, never the system prompt — `agent/turn_context.py:799` | returns the state block; system prompt stays byte-stable for caching | **correct by construction** |
| Model calls | `ctx.llm` → `agent.plugin_llm.PluginLlm` — `:376`; `acomplete_structured(instructions=, input=, json_schema=, max_tokens=, timeout=, purpose=, task=)` — `agent/plugin_llm.py:486` | every branch call goes through it; no SDK, no HTTP, no key of our own | **correct** (fixed: `task=` must be a key we registered — see below) |
| Provider/model choice | overrides are fail-closed and gated by `plugins.entries.<id>.llm.*` — `agent/plugin_llm.py:_check_overrides` | we pass **no** `provider=`/`model=`, so the host's active provider is used | **correct** — this is what makes any provider work |
| Auxiliary tasks | `register_auxiliary_task(key, …)` — `:863`; an unregistered `task=` raises `PluginLlmTrustError` — `agent/plugin_llm.py:207` | declares `antemuse_generate`, `antemuse_select`, `antemuse_refresh` and routes only to those | **correct** (now enforced by a test) |
| Storage | `plugins.plugin_storage.plugin_data_dir(name)` → `<hermes home>/plugin-data/<name>/` — `plugins/plugin_storage.py:22`; quota 10 MB via `PluginState` | `core/storage.data_dir()` resolves it; three modules did not | **fixed** |
| Hermes home | `hermes_constants.get_hermes_home()`; `HERMES_HOME`; profiles | `storage.hermes_home()` resolves host-first, env second, `~/.hermes` last | **fixed** |
| Dashboard backend | `plugin_api.py` router loaded by the host — `hermes_cli/web_server.py:394` | `dashboard/plugin_api.py` serves `/state`, `/select`, `/refresh` | **correct** |
| Memory | `register_memory_provider` is **inert** by design — `:733`; memory is host-owned and provider-pluggable (`memory.provider`) | the plugin never writes memory; daydream reads the **built-in** provider's files only | **partial, now named** |
| Context references | `register_context_reference(provider)` → `@prefix:` refs — `:717` | not used | **deliberately not used** — a state block must land in the turn by itself, not wait to be typed |

## The three defects this audit found

1. **The automation was reading a kwarg the host does not send.** Automatic journalling
   (`/note`'s replacement) read `kwargs["messages"]`; the host passes **`user_message`**
   (`agent/turn_context.py:811`). It worked in my probe because I fabricated `messages`.
   Fixed: `user_message` first, then `messages` / `conversation_history` as older-host
   fallbacks, and content blocks (Anthropic-style lists) are flattened to text so a
   provider swap cannot turn the person's words into a dict repr.

2. **Three modules hardcoded `~/.hermes`.** `core/sources.py`, `core/social.py` and
   `core/walks.py` built their own paths, so under `HERMES_HOME` or a profile they would
   write one profile's data into another's — and `storage.data_dir()`'s standalone
   fallback pointed at `~/.antemuse`, a third tree. All now resolve through
   `core.storage`, with `HERMES_HOME` honoured when the host module is absent.

3. **Memory was read from a file that an external provider does not write.**
   `memory.provider` is `hindsight` on this machine, and `USER.md` does not exist;
   `MEMORY.md` is a 2.2 KB snapshot. Daydream therefore drew from a partial, possibly
   stale file while reporting "no memories on disk" as if the person had none. Now the
   failure names the provider and the limitation: *"memory provider is 'hindsight', which
   this state cannot read (built-in MEMORY.md only)"*.

## The memory question, answered

Hermes memory belongs to the host: `memory.provider` selects between built-in, Hindsight,
Honcho, Mem0 and others, and `register_memory_provider` exists only so a plugin's
`register()` does not fail — it is inert, and activation is owned by `plugins/memory`.
There is **no plugin read API** for memory today. Consequences we accept and state:

- Antemuse does not write to memory and must not: a state is a bounded change to
  behaviour, not a fact about the person.
- Daydream's "stored memories" are only as good as the built-in provider's files. With an
  external bank, that source is unavailable and the state says so.
- The residual journal is not memory. It lives in the plugin's data dir, expires on its
  own caps, and is not injected into other sessions.

If Hermes later exposes a provider-neutral memory read to plugins, daydream should use it
and the file read should go. Until then, naming the gap is the honest option.

## Guarantee this buys

Any provider Hermes supports — OpenRouter, Anthropic, OpenAI, Nous, DeepSeek, a local
endpoint, or a credential pool — works with this plugin without a code change, because:

- the model, provider and key are the host's, chosen at call time;
- no vendor-shaped request, response or message format is constructed by the plugin;
- auxiliary routing uses keys the plugin registered, which the host maps how it likes;
- storage follows the profile; memory follows the host's provider.

## Verification

```
env -u PYTHONPATH NLTK_DATA=~/nltk_data ~/.local/bin/pytest -q   # 699 passed
```

`tests/test_hermes_integration.py` pins each claim above: no hardcoded Hermes home, no
provider SDK in `core/`, the facade's real keyword arguments, the registered-task rule,
the `user_message` path, and the named memory limitation.
