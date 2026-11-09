# Plugin settings — what a person may change, and what stays fixed

Status: **implemented** 2026-11-08. Owner: Ryan Cook. No new command.

### Revision 2026-11-08: the desktop app renders it

Ryan asked for the settings to be editable in the Hermes desktop app as well. That
settles open decision 2, and it changes the shape of the surface in a useful way: the
desktop renders a **form automatically for any plugin whose manifest declares
`config_schema`** (`apps/desktop/src/app/settings/plugin-settings.tsx`, saving through
`plugins.manage` → `save_plugin_setting`). So there is no bespoke UI to write and nothing
to keep in sync — the schema *is* the settings page.

Two consequences:

1. Keys are **flat** (`recommend_enabled`, not `recommend.enabled`). The host's form
   addresses top-level schema keys, and a nested form nobody renders is not a setting.
2. The plugin's own `registerSettingsPage` was **removed** from `desktop/plugin.js`. It
   rendered the state pane under a settings title, which would have shadowed the real
   form with a second, divergent copy of the same controls.

Verified against the host: the schema validates with no warnings, a wrong type warns
rather than blocking, and `ctx.get_config` reads exactly the path the form writes.

## Where settings actually live

Grounding, checked against the host rather than assumed:

- Values live in `config.yaml` at `plugins.entries.antemuse.settings.<key>`.
- The plugin declares its keys in the manifest's `config_schema`; the host validates
  settings against it (`hermes_cli/plugins_manifest.py::validate_config_schema`) and
  reports mismatches as **warnings, never load failures**.
- The plugin reads them through `PluginContext.get_config(key, default)`; it must not
  hand-edit `config.yaml`.
- The rendering surface is the host's plugins area (desktop settings / config UI). This
  spec does not build a second settings app: the plugin's contract is the schema plus
  the read, and any host that shows `config_schema` will show these.

## The rule

**A setting may change how loud or how long a state is. It may not change what a state
is.** Everything that makes the plugin honest — the directives, the contracts, the
residue labels, `/return`, the tool policy default, the wordless card, the no-model rule
on the state path — is not configurable, because a plugin whose identity can be switched
off in a dropdown has no identity.

## Settings, v1

| key | type | default | bounds | what it does |
|---|---|---|---|---|
| `recommend_enabled` | bool | `true` | — | may the recommender speak at all |
| `recommend_cooling_minutes` | int | `45` | 10–240 | how long one recommendation holds |
| `long_stretch_minutes` | int | `0` (measured) | 0 or 30–360 | `0` keeps the measured p75; any other value overrides it, and the line says `fixed at N` |
| `picture_enabled` | bool | `true` | — | post the state picture into the chat on entry |
| `picture_narrow` | bool | platform default | — | force the narrow card on wide clients |
| `journal_cap` | int | `60` | 20–60 | **reduce only**: the journal may be shortened, never lengthened past the spec's cap |
| `states.<name>.minutes` | int | state default | 1 … default | **reduce only**: a state may be made shorter, never longer. The long states are long on purpose |

Nine settings at most, and every one of them is bounded in both directions. Nothing here
can add a command, a state, or a model call.

## Explicitly not settable

- state definitions, directives, contracts, residue labels, `feeds`, `restart`
- tool policy (the default stays `free`; blocking stays opt-in per entry)
- `CONTROL_TOOLS`, `/return`, the 45-minute cooling floor, the residue cap of 3, the
  two-turn report decay
- the wordless card (BR-5) — no setting may put words on the picture
- the rule that entry, exit, expiry, tool restoration and rendering never call a model
- the recommendation patterns themselves. A person may silence the recommender; they may
  not author a pattern, because a hand-tuned trigger is an opinion wearing a counter's
  clothes.

## Behaviour under bad settings

1. **Unknown keys** are ignored by the plugin (the host may warn). They never raise.
2. **Out of range** is clamped to the nearest bound, and the clamp is reported once per
   session in the plugin's own log — silently changing a person's number is worse than
   telling them.
3. **Wrong type** falls back to the default; the host's validation warning is the record.
4. **Absent** means default. A fresh install has no `settings` block and behaves exactly
   as the spec says today.
5. Settings are read at the moment of use, not cached at load: editing config then
   restarting is not required for a plugin that reads per turn.

## Acceptance criteria (for the implementation phase)

1. `plugin.yaml` declares every v1 key in `config_schema` with type, default and bounds;
   `hermes plugins doctor` stays clean.
2. Each key is read through `ctx.get_config` with the documented default — no direct
   `config.yaml` reads, no hardcoded duplicate constants.
3. Out-of-range values clamp and log; `/state` still renders; a state still expires.
4. `recommend.enabled: false` produces turns with no recommendation at all.
5. `states.walk.minutes: 10` clamps to the state's default (3), and the clamp is visible.
6. A settings block with a wrong type and an unknown key loads the plugin and behaves as
   if unset.

## Open decisions

1. **Per-state durations at all?** Reducing `dream` from 30 minutes turns the longest
   state into a different product. My recommendation: ship v1 *without*
   `states.*.minutes` and add it only if the short states prove too long in use.
2. **Where the settings are edited.** There is no `hermes plugins config` subcommand,
   and I have not verified that the desktop plugins area renders `config_schema`. The
   first surface that certainly exists today is the general config editor:

   ```
   hermes config set plugins.entries.antemuse.settings.recommend.enabled false
   hermes config get plugins.entries.antemuse.settings
   ```

   Ship v1 against that, and treat the desktop pane as an addition to verify rather than
   a promise to make.
3. **Whether `picture.enabled` belongs to settings or to the chat client.** A person on
   Discord may want the picture always; that is closer to a platform profile than a
   plugin setting.

## Must not change

`/return`, `CONTROL_TOOLS`, state definitions and directives, durations as *defaults*,
cadences, the residue caps, the journal cap as an upper bound, the wordless card, the
recommendation patterns, and the rule that nothing on the state path needs a model call.
