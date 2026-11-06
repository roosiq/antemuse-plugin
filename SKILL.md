---
name: antemuse
description: Take and leave agent states — walk, daydream, dream, doomscroll — and watch them as imagery. Use when the user asks the agent to step away from the desk, work at a distance, or when a state is already active and governs this turn.
---

# Antemuse

A state is a bounded change to how the agent behaves, not a place it goes.

- `tools` — what it may still touch (a walk takes everything away)
- `directive` — injected into the turn it governs
- `contract` — the one line the reply is held to
- `residue` — what it carries back when the state ends

## Entering and leaving

```
/walk [minutes]      /daydream      /dissociate
/dream               /doomscroll    /snap
/states              the panel      /note <text>
```

Agents use `state(action="enter", name="walk")`, `state(action="exit")`,
`state(action="status")`, `state(action="watch")`, `state(action="list")`.

## The panel

`/states` prints one frame: the state, its clock, what is closed, the agent's
words on the left and yours on the right. `/note <text>` puts your observation
into the same state you are both in. `/watch [seconds]` redraws the panel until
the state ends.

## Rules

- Never enter a state to avoid work; enter it to change what the work looks like.
- Obey the contract literally — a walk that plans is a desk with extra steps.
- When the state ends, say what it left behind. Residue is the only output.
- A state that blocks tools also blocks you; `/snap` is always available and is
  exempt from the block.


## Verifying in this environment

The shell exports a `PYTHONPATH` pointing at a Python 3.14 site-packages, which
breaks both `pytest` collection and `PIL` inside any other interpreter. Clear it
for every test run:

```bash
env -u PYTHONPATH NLTK_DATA=/home/ryan/nltk_data ANTEMUSE_STATES_HOME=/tmp/check \
  uvx --with pillow --with nltk --quiet pytest tests/ -q
```

And always point `ANTEMUSE_STATES_HOME` somewhere temporary during verification —
the plugin shares one state file with the live agent, so a test that enters a
state will lock the agent's own tools until it exits.
