# Catalog PR body — NousResearch/hermes-agent

Title: `plugin-catalog: add antemuse`

## What this adds

One file, `plugin-catalog/antemuse.yaml`, for **antemuse** — a community plugin
that gives a Hermes agent deliberate, bounded states (walk, daydream, doomscroll,
unstuck, dream) with host-enforced tool policy, reply contracts, wordless imagery
for the person, and an account on return.

## Pin

- Repo: https://github.com/roosiq/antemuse-plugin (public, cloneable without credentials)
- SHA: `ff1d515842c32362c89db75437463181416d66b4`
- Verified at that commit: `tools/test.sh --with-renderers` → 906 passed, 1 skipped;
  `hermes plugins validate . --install-deps --json` → 16/16 checks, no warnings;
  `hermes plugins doctor .` → 1 tool, 8 hooks, OK.

## Disclosures

- `doomscroll` fetches public RSS/JSON feeds over `urllib` (8 s timeout) and places
  feed text in the agent's context.
- `daydream` reads the operator's `~/.hermes/memories/MEMORY.md` and `USER.md`.
- `session-scan` reads up to 300 recent messages from `~/.hermes/state.db`, once per
  session, in a background thread; `ANTEMUSE_NO_SCAN` disables it.
- Writes go to the profile plugin data dir and `<repo>/.antemuse/` only.
- The terminal takeover may spawn `node` to rasterise live scenes.
- Scripts under `tools/` make network calls and are never imported at registration.
- No credentials, no telemetry, no self-updater, no model call on entry, exit,
  expiry or rendering.

## Claim discipline

The plugin claims a mechanism change — tool availability, reply shape, and an
account on return — not improved creativity. Its own measurements show no
ideation effect after length control (32 pairs per condition, p = 0.365).

## License

MIT, Copyright (c) 2026 Ryan Cook.
