# Antemuse States

The agent can take a walk, daydream, dissociate, dream, or doomscroll — and a
person can watch it happen in the CLI and take the same state beside it.

A state is a bounded change to behaviour, not a place:

- **tools** — what the agent may still touch (a walk takes everything away)
- **directive** — injected into the turn the state governs
- **contract** — the one line the reply is held to
- **residue** — what it carries back when the state ends

States expire on minutes *and* turns; the clock decides when it ends, the turn
count decides how much of it the model gets.

## The panel

`/states` renders one frame in the terminal:

```
 ANTEMUSE · STATES                                    WALKING  07:52
 ──────────────────────────────────────────────────────────────────
 ██████████████████████████████████████████████████████████████████
 observations, not conclusions

 THE AGENT                            YOU
 14:39  walk                          14:39  walk
   I notice I have no sidewalk, no     the fridge stopping mid-hum,
   weather, no sound — so anything     then starting again
   I said about a street would be
 ──────────────────────────────────────────────────────────────────
 tools  closed
 turns  2
 /note <text>  /snap  /states
```

`/note <text>` puts the person's words in the right column of the same state.
`/watch [seconds]` redraws until the state ends. Everything is plain text and
ANSI, so it survives the Hermes CLI, tmux, SSH, and pasted screenshots.

## Install

```bash
ln -s ~/antemuse-states ~/.hermes/plugins/antemuse-states
hermes plugins enable antemuse-states
```

## Layout

```
plugin.yaml            manifest: 1 tool, 3 hooks
__init__.py            hooks (pre_llm_call, pre_tool_call, transform_llm_output),
                       /walk /daydream /dissociate /dream /doomscroll /snap
                       /states /note /watch, and the state tool
kitchen/definitions.py the five states: tools, directive, contract, residue
kitchen/engine.py      enter/stop/tick, tool policy, journal, residue
kitchen/panel.py       the CLI frame
tests/                 18 tests
```

## Verify

```bash
hermes plugins doctor ~/antemuse-states
PYTHONPATH= ANTEMUSE_STATES_HOME=$(mktemp -d) uvx pytest tests/ -q
hermes chat -q '/walk' && hermes chat -q '/states'
```

## Notes

- The `state` tool is exempt from every block, so `/snap` can always end a state.
  An earlier build blocked its own escape hatch and locked the agent out of its
  tools until the clock ran down.
- State is profile-wide, not per-session: the metaphor is about the agent.
- Data lives in the profile plugin data dir, overridable with
  `ANTEMUSE_STATES_HOME`.
