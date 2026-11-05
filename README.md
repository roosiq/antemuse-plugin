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

Two surfaces, one state:

- **`hermes-states`** — a full-screen takeover for any terminal: block-digit
  clock, draining bar, both columns, live keys. This is the one to watch.
- **`/states`** — a text panel printed inside the Hermes chat, for when a
  takeover is not available (the Ink TUI runs tools without a tty, so the
  takeover is its own process rather than an agent tool result).

```
hermes-states
 1 walk  2 daydream  3 dissociate  4 dream  5 doomscroll
 n note  space snap  q quit
```

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
kitchen/panel.py       the printed text frame
kitchen/tui.py         the full-screen takeover (alt screen, truecolor, keys)
bin/hermes-states      launcher on PATH
tests/                 18 tests
```

## Verify

```bash
hermes-states                # full-screen view
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

## three.js backdrop

The takeover can carry a real 3D animation. WebGL does not run in a terminal, so
the pipeline is: headless Chromium + swiftshader renders the scene to PNG, the
PNG is quantised to upper-half blocks (`▀` = two vertical pixels per cell), and
the takeover replays the cached frames at animation speed.

```bash
cd ~/antemuse-states && python3 tools/render_three.py    # 12 frames, ~0.65 s each
```

Frames land in `<plugin data>/three_frames/`; `kitchen/three_backdrop.py` loads
them at whatever cell size the terminal can afford (44x14 in the takeover, 96x26
full-screen). Playback is free — pre-built strings, so the clock and spinner keep
their own timing.

Live WebGL at 60 fps inside a terminal is not a thing: one headless render costs
~0.65 s. For real images rather than blocks, the same PNGs can go through the
kitty graphics protocol or sixel where the terminal supports it.
