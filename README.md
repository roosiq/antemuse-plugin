# Antemuse

**Take a walk while the work continues.**

Antemuse has one agent state: **walk**. A walk follows six hops on its declared graph provider (WordNet by default) while the agent continues the task with its tools open. The path is visible in the pane but is
not injected as material; it changes the frame, not the facts in the next reply.

`/explore` is separate. It is person-driven: the cockpit shows the concept map, the
person chooses what to shoot, and `/return` names those picks back. It is not an
agent state, has no provider or dose, and its behaviour is unchanged by the one-state
cut.

A walk is a dose, not a timer. It ends when its six hops have been delivered and
shown, when it runs dry, when its provider fails, or when `/return` ends it. Each
ending leaves an account and one ledger row.

## What it looks like in use

```text
/walk
WALKING · 6 hops · work continues · the frame is elsewhere · different on return
```

A running walk keeps work going. Tools remain open unless the entry explicitly uses
`block: true`; `allow:` can then narrow the available tools.

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

## The three commands

```text
/walk [graph]
/explore
/return
```

`/walk` is the only agent-state command. `/explore` remains a person-driven map mode.
`/return` ends either active mode and preserves its account.

Agents use the state tool: `state(action="enter", name="walk")`,
`state(action="exit")`, `state(action="status")`, `state(action="break")`, and
`state(action="list")`.

## The walk

| mode | dose | material | result |
|---|---:|---|---|
| **walk** | 6 hops | WordNet | The pane records a six-hop path; the agent receives no hop material while walking. |
| **explore** | open | the person's picks | The cockpit records picks; `/return` accounts for them. |

The four recorded walk endings are `complete`, `returned`, `dry`, and `failed`.
`complete` means the dose was delivered and shown. `dry` means a turn found no new
material. `failed` means the provider produced no material. No ending is based on a
clock.

## The panes

- **Antemuse pane:** the concept map and the walk's path.
- **Cockpit pane:** the person-driven `/explore` map.
- **Chat:** text accounts and status only.

## Install

```bash
git clone https://github.com/roosiq/antemuse-plugin ~/antemuse-plugin
ln -s ~/antemuse-plugin ~/.hermes/plugins/antemuse
hermes plugins enable antemuse
```

The plugin needs `nltk` and the WordNet corpus for walks. `plugin.yaml` declares the
Python dependency; install WordNet for the interpreter Hermes uses:

```bash
python3 -c "import nltk; nltk.download('wordnet')"
```

## Settings

`plugin.yaml` declares 7 bounded settings. The configuration keeps the seven settings for
recommendations, journal retention, and experimental exploration support; they do not add agent
states or change the walk's contract.

## Layout

```text
plugin.yaml            manifest: one state tool, hooks, 7 bounded settings
__init__.py            hooks, /walk, /explore, /return, and the state tool
core/states.py         the walk and separate person-driven explore definition
core/engine.py         state lifecycle, delivery, tool policy, journal, residue
core/sources.py        the walk provider
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

A walk reads WordNet. `/explore` records only the concepts the person chooses. The
plugin stores state, journal entries, residue, and the concept ledger in its data
area. It does not need credentials or API keys for the walk.
