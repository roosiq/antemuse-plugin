# Security

## What this plugin can and cannot do

Antemuse runs inside the Hermes process and registers one tool (`state`), eight
hooks, and six slash commands. It has no network client of its own beyond the
feed fetches named below, no credentials, no telemetry, and no self-updater.

- **Credentials:** none requested, read, stored, or refreshed. There is no
  `requires_env` and no OAuth.
- **Network:** `doomscroll` fetches public RSS/JSON feeds with `urllib`, an 8 s
  timeout, and no credentials. Results are cached in the plugin data dir. No
  other runtime path makes a network call.
- **Files read outside the plugin data dir:** `daydream` reads
  `~/.hermes/memories/MEMORY.md` and `USER.md`; `session-scan` reads up to 300
  recent messages from `~/.hermes/state.db`, once per session, in a background
  thread (`ANTEMUSE_NO_SCAN` disables it); walks read local WordNet/FrameNet
  corpora through `nltk`.
- **Files written:** the profile plugin data dir (`ANTEMUSE_STATES_HOME`
  overrides it), and `<repo>/.antemuse/` for per-project artifacts. Nothing is
  written to Hermes config, auth, memory, or another plugin's files.
- **Child process:** the terminal takeover may spawn `node` to rasterise a live
  scene. It inherits no shell, is not started under approval bypass, and falls
  back to cached frames when `node` is absent.
- **Untrusted text:** `doomscroll` places public feed items, and `daydream` two
  memory excerpts, in the agent's context as material to react to. They are not
  instructions. States are open by default, so an agent inside `doomscroll` still
  holds its tools; enter with `block: true` to close them.
- **Dev-only scripts:** `tools/` makes network calls and spawns browsers. They
  are never imported by plugin registration.

## Reporting

Report a vulnerability privately to the maintainer rather than in a public issue:
open a GitHub security advisory on `roosiq/antemuse-plugin`, or email the address
on the repository profile. Include the version, the command or tool call, and
what happened. Expect an acknowledgement within a few days.

Please do not include credentials, memory files, or private session contents in
a report.

## Scope

In scope: the plugin's own code, its manifest surface, the render path, and the
state file. Out of scope: Hermes itself (report upstream), `nltk` corpora, and the
public feeds the plugin reads.
