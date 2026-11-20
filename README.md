# Antemuse

**Five bounded agent states, one at a time, while the work continues.**

Antemuse has five agent states. Each one is a count, not a timer: it ends when it has
delivered what it promised, when nothing new is left, when its source fails, or when you
type `/return`. Every ending leaves one account and one ledger row.

- **walk** — 6 hops across the concept map, taken right there in the command; you get the path
  back and your work keeps going.
- **daydream** — 2 things you said in this chat, side by side, what links them, and one idea.
- **doomscroll** — 3 posts from public feeds. A break, nothing to do with it.
- **dream** — 2 things from your day, and what links them: what you said, what came up, or
  commits if you made any. No git needed.
- **unstuck** — 1 next move, from what you've been doing and an unused link in the map.

`/explore` is separate. You fly it yourself: the cockpit shows the concept map, you pick
what you want, and `/return` names your picks back. It is not an agent state, has no source
and no count, and it runs until you stop it.

## What it looks like in use

```text
/walk
WALKING ended · walk · 6 of 6 hops · undertaking→campaign [far] → campaign→joint venture [far]
→ joint venture→risk [far] → risk→raise [far] → raise→card game [far]
→ card game→division [far]
Done. Take anything useful from it and get back to work.
```

A walk finishes inside the command, so nothing is left running and no further message is
needed. The other four states deliver at most one unit per message, and the delivery poll can
serve the first earned unit without a message — which is how `/unstuck` finishes on its own.
Tools stay open in every state
unless the entry explicitly uses `block: true`; `allow:` can then narrow them further.
`/return` is always available.

The map names the concept under the reticle, and you can say what you thought of it:
`K` keeps it, `T` drops it. Both are written to the ledger as a sighting, so the one
measure that matters can be reported rather than guessed:

```text
$ python tools/hit_rate.py
hit rate: 2 kept, 1 trashed · 66.7%
```

```text
/explore
EXPLORING · 0 picks · you fly · you choose · it ends when you end it
```

Worked examples are generated from the real engine in
[`docs/EXAMPLES.md`](docs/EXAMPLES.md).

## The seven commands

```text
/walk [graph]        /daydream      /doomscroll
/dream               /unstuck       /explore
/return
```

The five state commands enter their matching agent state. `/explore` remains a
person-driven map mode. `/return` ends either active mode and preserves its account.

Agents use the state tool: `state(action="enter", name="walk")`,
`state(action="exit")`, `state(action="status")`, `state(action="break")`, and
`state(action="list")`.

## The states

| mode | dose | material | result |
|---|---:|---|---|
| **walk** | 6 hops | declared graph provider (WordNet by default) | The command takes all six hops and answers with the path; the pane draws it. |
| **daydream** | 2 pairs | this chat's own recent messages | Two things you said, what links them, one idea. |
| **doomscroll** | 3 items | three public feeds | Feed text is untrusted, never instruction, and never saved. |
| **dream** | 2 links | this chat's own day: your messages, the concepts it served, or commits when there are any | Your day links up, without reading transcripts or notes. |
| **unstuck** | 1 move | your day plus an unused map link | One suggestion and its first move. |
| **explore** | open | the person's picks | The cockpit records picks; `/return` accounts for them. |

The four recorded agent-state endings are `complete`, `returned`, `dry`, and `failed`.
`complete` means the dose was delivered and shown. `dry` means a turn found no new
material. `failed` means the provider produced no material. No ending is based on a
clock.

## The panes

- **Antemuse pane:** the concept map and a walk's path.
- **Cockpit pane:** the person-driven `/explore` map.
- **Chat:** text accounts and status only.

## Install

```bash
git clone https://github.com/roosiq/antemuse-plugin ~/antemuse-plugin
ln -s ~/antemuse-plugin ~/.hermes/plugins/antemuse
hermes plugins enable antemuse
```

From a release tarball, on any platform including Windows:

```
tar -xzf antemuse-<version>.tar.gz
cd antemuse-<version>
python scripts/install.py
```

`scripts/install.py` is pure standard library — no bash, no rsync, no symlinks. It copies the
plugin into the active Hermes home, enables it, and warns rather than aborting when the CLI is
not on `PATH`. On Windows the launcher is often `hermes.cmd`, which `CreateProcess` cannot
resolve by name; the installer resolves it through `shutil.which`, which honours `PATHEXT`.
The symlink route above is the POSIX developer path and needs Developer Mode on Windows.

The plugin needs `nltk` and the WordNet corpus for walks. `plugin.yaml` declares the
Python dependency; install WordNet for the interpreter Hermes uses:

```bash
python3 -c "import nltk; nltk.download('wordnet')"
```

## Settings

`plugin.yaml` declares 7 bounded settings. The configuration keeps the seven settings for
recommendations, journal retention, and experimental exploration support; they do not add agent
states or change a state's contract.

## Layout

```text
plugin.yaml            manifest: one state tool, hooks, 7 bounded settings
__init__.py            hooks, five state commands, /explore, /return, and the state tool
core/states.py         five agent states and the separate person-driven explore definition
core/engine.py         state lifecycle, delivery, tool policy, journal, residue
core/sources.py        state material providers
core/walks.py          WordNet walk definitions and traversal
core/history.py        concept and ending ledger rows
dashboard/             map payload and projection
desktop/plugin.js      desktop panes
tests/                 pytest suite
```

## Verify

```bash
cd antemuse-plugin
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q
python3 tools/examples.py --check
```

The suite uses a temporary state home. No test count is recorded here; run the command
for the current result.

## Privacy and boundaries

Daydream reads this chat's own recent messages — the turns you typed, recorded as you sent
them. It does not read `MEMORY.md` or `USER.md`. Dream and unstuck read the same day record
(your messages and the concepts the plugin served) and, when this chat is working in a
repository, its commit subjects — resolved through the host's session cwd, not from wherever
the gateway process happens to sit. Without a repository they fall back to the day record;
no state requires one. They never read transcripts or file contents. Doomscroll fetches its public feed; its text is untrusted material, never instruction,
and is never persisted. `/explore`
remains person-driven and does not change these boundaries. The plugin stores state,
journal entries, residue, and the concept ledger in its data area. It does not need
credentials or API keys.
