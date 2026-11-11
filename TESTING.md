# Testing

What to run, and what each check actually proves.

## Requirements

- Hermes Agent **0.21.6 or newer** (`hermes --version`).
- Python 3.11+ (Hermes's own runtime is fine).
- Optional: `node` + `npm`, only for the pane harness. Nothing at runtime needs them.
- Linux or macOS. Windows is unverified.

## Install from a tarball

```bash
# 1. unpack somewhere permanent (the tarball has one top-level directory)
mkdir -p ~/antemuse-plugin
tar -xzf antemuse-<version>.tar.gz -C ~/antemuse-plugin --strip-components=1

# 2. link it into Hermes and enable it
ln -s ~/antemuse-plugin ~/.hermes/plugins/antemuse
hermes plugins enable antemuse

# 3. restart the gateway, then check the host can load it
hermes gateway restart
hermes plugins doctor antemuse      # expect: 1 tool, 8 hooks, OK
```

No credentials, no API keys and no configuration are required. The one Python dependency
(`nltk`) is declared in `plugin.yaml` and prepared by Hermes at install time.

## First run

```bash
hermes chat -q '/walk'        # 3 minutes of work, tools open
hermes chat -q '/daydream'    # 3 minutes, tools open unless you ask for block
hermes chat -q '/return'      # end it, keep the account
```

The commands are one per state plus `/return` — `/walk`, `/daydream`, `/doomscroll`,
`/unstuck`, `/dream`, `/return`. There is no `/break`, `/mood`, `/note`, `/watch` or
`/states` command: those are **actions on the `state` tool** the agent calls when you ask in
words ("is a break due?").

What you should see:

- `/walk` → `WALKING · 3 min · 6 turn(s) · work continues · distant concepts, still a path back to the task`
- `/daydream` → `DAYDREAMING · 3 min · 2 turn(s) · two memories · what they touch · one possibility`
- `/return` → `DAYDREAMING ended · daydream 1m · 0 step(s) · nothing arrived` and
  `Summarise it in three lines — where it went, what it touched — then get back to work.`
- `state(action="break")` → the counters (`0m since the last state · 0 turn(s)`) followed by
  one named recommendation with its reason, e.g.
  `this looks like a rut · the last state was walk too · /daydream`.
- A reply made while a state is active ends with a marker such as
  `— daydreaming, 2 min left · /return to come back`.

There is no terminal takeover to run: `core/tui.py` and the alt-screen surface were deleted
in 0.10.30, so a terminal gets the same text record the chat gets. The picture is the desktop
app's pane. Nothing in a state ever blocks the agent's work unless you ask for `block: true`.

## Verify it yourself

```bash
cd ~/antemuse-plugin
tools/test.sh                    # suite in a temp data home
tools/test.sh --with-renderers   # npm ci in the harness dir, then mount the pane
hermes plugins validate . --install-deps   # what catalog CI runs
hermes plugins doctor antemuse
```

No test count is recorded here on purpose: it rots with the next test. Run the command and
read the number it prints. A single green run is not proof of stability either — the suite
has one stochastic case, so treat a lone failure as worth a second run before believing it.

## What each check proves

| command | what a green result means |
|---|---|
| `tools/test.sh` | the shipped code does what the tests name, in a temp data home, with no model calls |
| `tools/test.sh --with-renderers` | the pane's JavaScript mounts in jsdom and 12 properties hold: registration, settings page, helpers, DOM text, frame, aria, poll tick, idle, unavailable, layer/placement, conversation scope, chat left clean |
| `hermes plugins doctor antemuse` | the host can discover, parse, import and register the plugin: 1 tool, 8 hooks |
| `hermes plugins validate .` | the manifest, declared capabilities, dependency bounds, desktop surface and safety scan all hold |

Validate a **clone or the packed tarball**, not your working tree. `experiments/` and
`evaluation/` are gitignored, so a local checkout keeps raw model transcripts the install
scanner rightly refuses; a clone has none of them and is what catalog CI reads.
| `tar -tzf … \| grep -E 'pyc\|\.antemuse'` | the package carries no bytecode and no local state |

## Where it writes

- State, journal, residue, cursors: `~/.hermes/plugin-data/antemuse/` (or the active
  profile's equivalent). Override with `ANTEMUSE_STATES_HOME` for testing.
- Per-project artefacts: `<your repo>/.antemuse/`.
- Nothing else. No config, auth, memory or credential files are written. `daydream` does read
  your own `~/.hermes/memories/` files as its material, and `doomscroll` fetches public feeds.

## Known limits

- **The pane needs the desktop app.** Built and exercised from the shipped package, but there
  is no picture at all in a terminal or a chat-only install.
- **State is profile-wide**, not per-session: it is about the agent, so every chat in that
  profile sees the same state until it ends or expires.
- `spark`, `keep` and the exploration library are present but runtime-gated behind
  `experimental.enabled`; leave it off.
- A state entered with `block: true` closes tools for the whole profile until it ends. Do not
  do that in a profile that runs unattended work.

## Uninstall

```bash
hermes plugins disable antemuse
rm ~/.hermes/plugins/antemuse          # removes the symlink, not your clone
rm -rf ~/.hermes/plugin-data/antemuse  # optional: drop state and journal
```
