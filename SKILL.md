---
name: antemuse
description: Take and leave agent states — walk, daydream, dream, doomscroll — and watch them as imagery. Use when the user asks the agent to step away from the desk, work at a distance, or when a state is already active and governs this turn.
---

# Antemuse

A state is a bounded change to how the agent behaves, not a place it goes.

- `tools` — what it may still touch (a walk takes nothing; a dream takes everything)
- `directive` — injected into the turn it governs
- `contract` — the one line the reply is held to
- `residue` — what it carries back when the state ends

## Entering and leaving

```
/walk [minutes]      /daydream      /dissociate
/dream               /doomscroll    /return
/states              the panel      /note <text>
```

Agents use `state(action="enter", name="walk")`, `state(action="exit")`,
`state(action="status")`, `state(action="watch")`, `state(action="list")`.

## The panel

`/states` takes over a terminal: the state, its clock, what is closed, the
agent's words on the left and yours on the right. `/state` prints the same
moment as a picture. In chat you get one image, no caption. `/note <text>` puts
your observation into the same state you are both in. `/watch [seconds]`
redraws until the state ends.

## Taking a break

`state(action="break")` recommends; `state(action="break", name="walk")` takes
it. `state(action="mood", feeling="stuck")` is how you say how the work feels —
`stuck`, `tired`, `sharp`, `flat`, `saturated`. Strain comes from minutes, turns,
and failed tool calls since the last state, so the recommendation is arithmetic,
not a guess. Ignore it when the work is nearly done; the nudge waits 45 minutes.

## Rules

- Never enter a state to avoid work; enter it to change what the work looks like.
- A walk is ambient: keep working, and let a step brush the work only if it belongs there.
- When the state ends, say what it left behind. Residue is the only output.
- A state that blocks tools also blocks you; `/return` is always available and is
  exempt from the block.


## Verifying in this environment

The shell exports a `PYTHONPATH` pointing at a Python 3.14 site-packages, which
breaks both `pytest` collection and `PIL` inside any other interpreter. Clear it
for every test run:

```bash
env -u PYTHONPATH NLTK_DATA=/home/ryan/nltk_data ANTEMUSE_STATES_HOME=/tmp/check \
  uvx --with pillow --with nltk --quiet pytest tests/ -q
```

The plugin declares `pillow` and `nltk`, but Hermes does not install plugin
dependencies into its own interpreter: if a state enters and every walk records
`failed · No module named 'nltk'`, install them where Hermes runs:

```bash
uv pip install --python "$(hermes --version >/dev/null; python3 -c 'import sys;print(sys.executable)')" \
  "pillow>=10,<14" "nltk>=3.8,<4"
```

And always point `ANTEMUSE_STATES_HOME` somewhere temporary during verification —
the plugin shares one state file with the live agent, so a test that enters a
state will lock the agent's own tools until it exits.
