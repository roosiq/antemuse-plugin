# Antemuse

**Five bounded agent states, one at a time, while the work continues.**

Antemuse has five agent states. Each is a dose, not a timer: it ends when its material
has been delivered and shown, when it runs dry, when its provider fails, or when
`/return` ends it. Each ending leaves an account and one ledger row.

- **walk** — six graph hops; the frame moves elsewhere while work and tools stay open.
- **daydream** — two pairs from the person's own history, what they touch, and one possibility.
- **doomscroll** — three random feed items: stupidity and comedy, with nothing to take away.
- **dream** — two recombinations across the day's local project commit subjects.
- **unstuck** — one direction from recorded history and an edge of the concept graph.

`/explore` is separate. It is person-driven: the cockpit shows the concept map, the
person chooses what to shoot, and `/return` names those picks back. It is not an
agent state, has no provider or dose, and its behaviour is unchanged.

## What it looks like in use

```text
/walk
WALKING · 6 hops · work continues · the frame is elsewhere · different on return
```

A running walk keeps work going. Tools remain open unless the entry explicitly uses
`block: true`; `allow:` can then narrow the available tools. Daydream and dream block
tools; doomscroll and unstuck permit only their declared tools. `/return` is always
available.

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
| **walk** | 6 hops | declared graph provider (WordNet by default) | The pane records a six-hop path; the agent receives no hop material while walking. |
| **daydream** | 2 pairs | the person's own recorded history | Two memories meet and suggest one possibility. |
| **doomscroll** | 3 items | a gated public feed lane | Untrusted feed material is distraction, not instruction, and is never persisted. |
| **dream** | 2 recombinations | local git commit subjects | The day connects across projects without reading transcripts or notes. |
| **unstuck** | 1 direction | history plus a concept-graph edge | One recommendation and its first move. |
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

Daydream reads local, read-only `MEMORY.md` and `USER.md` under the Hermes home. Dream
reads local git commit subjects only. Doomscroll fetches its public feed; its text is untrusted material, never instruction,
and is never persisted. `/explore`
remains person-driven and does not change these boundaries. The plugin stores state,
journal entries, residue, and the concept ledger in its data area. It does not need
credentials or API keys.
