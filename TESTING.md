# Trying Antemuse

This is a pre-release build for a test user. It is a Hermes plugin: it changes
*how the agent works* for a bounded time — walk, daydream, doomscroll, dream —
and shows the person a wordless picture of the state while it runs.

What it does not do: it does not make the agent more creative, it calls no model
on entry, exit, expiry or rendering, and it does not send anything to a channel
by itself.

## Requirements

- Hermes Agent **0.21.6 or newer** (`hermes --version`).
- Python 3.11+ (Hermes's own runtime is fine).
- Optional: `node` + `npm` for live terminal scenes; without them the takeover
  falls back to static art.
- Linux or macOS. Windows is untested.

## Install

```bash
# 1. unpack somewhere permanent (the tarball has one top-level directory)
mkdir -p ~/antemuse-plugin
tar -xzf antemuse-plugin.tar.gz -C ~/antemuse-plugin --strip-components=1
#    preferred, if you want history and `git pull` later:
#    git clone antemuse-plugin.bundle ~/antemuse-plugin

# 2. link it into Hermes and enable it
ln -s ~/antemuse-plugin ~/.hermes/plugins/antemuse
hermes plugins enable antemuse

# 3. restart the gateway, then check the host can load it
hermes gateway restart
hermes plugins doctor antemuse      # expect: 1 tool, 8 hooks, OK
```

No credentials, no API keys, no configuration are required. Python dependencies
(`pillow`, `nltk`) are declared in `plugin.yaml` and prepared by Hermes at install
time.

## First run

```bash
hermes chat -q '/walk'        # 3 minutes, tools open
hermes chat -q '/daydream'    # 3 minutes, tools closed
hermes chat -q '/return'      # end it, keep the account
```

The commands are one per state plus `/return` — `/walk`, `/daydream`,
`/doomscroll`, `/unstuck`, `/dream`, `/return`. There is no `/break`, `/mood` or
`/states` command in this build; those are **actions on the `state` tool** the
agent calls when you ask in words ("is a break due?").

What you should see:

- `/walk` → `WALKING · 3 min · 6 turn(s) · work continues · distant concepts, still a path back to the task`
- `/daydream` → `DAYDREAMING · 3 min · 2 turn(s) · two memories · what they touch · one possibility`
- `/return` → `DAYDREAMING ended · daydream 1m · 0 step(s) · nothing arrived` and
  `Summarise it in three lines — where it went, what it touched — then get back to work.`
- `state(action="break")` → the counters (`0m since the last state · 0 turn(s)`)
  followed by one named recommendation with its reason, e.g.
  `this looks like a rut · the last state was walk too · /daydream`.
- A reply made while a state is active ends with a marker such as
  `— daydreaming, 2 min left · /return to come back`.

The full-screen takeover is `python3 -m core.tui` from the plugin directory and
needs a real terminal; in this build it is not bound to a slash command. It never
blocks the agent's work.

States are **open by default** in this build: entering one does not remove tools.
To close them, ask the agent to enter with `block: true`
(`state(action="enter", name="daydream", block: true)`), which is what the
blocked-tool behaviour is for.

## Verify it yourself

```bash
cd ~/antemuse-plugin
tools/test.sh                    # suite, ~30 s, temp data dir
tools/test.sh --with-renderers   # npm ci first, so renderer tests run too
hermes plugins validate . --install-deps --json   # what catalog CI runs
```

At this build: **906 passed, 1 skipped** with `--with-renderers`; **900 passed,
7 skipped** on a fresh clone before `npm ci` (those seven are the renderer tests).
Validation is 16/16 checks, no warnings.

## Where it writes

- State, journal, residue, cursors: `~/.hermes/plugin-data/antemuse/` (or the
  active profile's equivalent). Override with `ANTEMUSE_STATES_HOME` for testing.
- Per-project artifacts: `<your repo>/.antemuse/`.
- Nothing else. No config, auth, memory or credential files are read or written.
  `daydream` does read your own `~/.hermes/memories/` files as its material, and
  `doomscroll` fetches public feeds.

## Known limits in this build

- **Desktop pane**: built, but not confirmed rendering inside the packaged app on
  this machine. The CLI takeover is the verified surface.
- **State is profile-wide**, not per-session: it is about the agent, so every
  chat in that profile sees the same state until it ends or expires.
- `/spark`, `/keep`, `/again` and the exploration library are present but
  runtime-gated behind `experimental.enabled`; leave it off.
- The renderer writes to a terminal that supports truecolor and half-block
  glyphs. Redirected output gets a single picture instead of the takeover.

## Uninstall

```bash
hermes plugins disable antemuse
rm ~/.hermes/plugins/antemuse          # removes the symlink, not your clone
rm -rf ~/.hermes/plugin-data/antemuse  # optional: drop state and journal
```

## What I want to know

1. Did install and `doctor` work without edits?
2. Did `/break`, a state, and `/return` behave as described?
3. Did the takeover render, and did `q` return you to the shell cleanly?
4. Anything that read as jargon, a dead end, or a surprise.
5. Any state that felt wrong to be in — too long, too short, too noisy.

Send notes with the exact command and the line you saw. A screenshot of a broken
takeover is worth more than a description.
