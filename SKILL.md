---
name: antemuse
description: Take and leave the one agent state (walk) and the person-driven map (explore). Use when the user asks the agent to step away from the desk, work at a distance, or when a state is already active and governs this turn.
---

# Antemuse

A state is a bounded change to how the agent behaves, not a place it goes.

- `tools` — what it may still touch (a walk takes nothing)
- `directive` — injected into the turn it governs
- `contract` — the one line the reply is held to
- `residue` — what it carries back when the state ends

## Entering and leaving

```
/walk [graph]        /explore        /return
```

That is the whole command surface — three verbs, nothing else. `walk` is the only
state the agent enters: six hops, one bought per turn, recorded for the pane and
never injected into the turn. `/explore` is the one state a person drives: it has
no dose and no end of its own, the cockpit is the map, and what you keep is
counted (`K` keeps, `T` drops, `tools/hit_rate.py` reports the rate). It closes
when they type `/return`, and the account names the concepts they picked, by count. A person's own
message is journalled as a note automatically while a state runs, so there is no
`/note`; the recommendation arrives in the turn by itself, so there is no `/watch`.

Agents use the tool instead: `state(action="enter", name="walk")`,
`state(action="exit")`, `state(action="status")`, `state(action="break")`,
`state(action="list")`. There is no action that asks for a picture: the pane draws
the state you are already in.

## The panes

The picture lives in two desktop panes and nowhere else: the Antemuse pane draws
the map, and the cockpit tab flies it in first person for `/explore`. In chat a
state posts its account as text, on entry, without media. There is no terminal
takeover and no image frame: `/state` is not a command, and a terminal reads the
same text record the chat gets.

## Taking a break

`state(action="break")` recommends; `state(action="break", name="walk")` takes
it. `state(action="mood", feeling="stuck")` is how you say how the work feels —
`stuck`, `tired`, `sharp`, `flat`, `saturated`. The measurement comes from turns,
and failed tool calls since the last state, so the recommendation is arithmetic,
not a guess. Ignore it when the work is nearly done; the nudge waits ten turns.

## Rules

- Never enter a state to avoid work; enter it to change what the work looks like.
- A walk is ambient: keep working. The walked path is scenery, not a hint, and
  no walk material is injected into the working turn.
- When the state ends, say what it left behind. Residue is the only output.
- A state that blocks tools also blocks you; `/return` is always available and is
  exempt from the block.

## Experimental development (not runtime-active)

An experimental exploration layer lives in the library. Its modules
(`core/collider.py`, `core/collision.py`, `core/llm.py`,
`core/orchestrator.py`, `core/selection.py`, `core/feedback.py`,
`data/collider/`) exist. Three auxiliary task routes (`antemuse_generate`,
`antemuse_select`, `antemuse_refresh`) are declared — a routing entry, not a call —
and the four session-boundary hooks are registered; on a session boundary they
release any material bound to that session. `/spark` is the first thing that binds material;
it is also the only runtime path that can reach a model, and only when the flag
is on.

- `/spark <goal>` exists and runs one bounded pass. With
  `plugins.entries.antemuse.settings.experimental.enabled: true` and a host that
  exposes `ctx.llm`, it takes the branch path (one auxiliary call per budgeted
  source, then deterministic selection). With the flag off it stays
  deterministic and calls nothing. `/keep love|like|trash <#n|candidate-id>`
  records a verdict by its account handle; `/again` re-runs the last goal with
  the sources that verdict points at (`deepen` from loved, `refresh` from liked).
- The two audiences are separate by contract: the model receives the candidates,
  the person receives a line of counts (`spark · 2 candidate(s) · 1 kept · kept #1`).
  Never read candidate text into a human-facing line.
- Do not claim the library improves responses, diversity, or creativity. No
  protected comparative evaluation has been run, and runtime selection scores
  are not improvement evidence.
- The base state lifecycle stays deterministic: entry, exit, expiry, tool
  restoration, and rendering never require inference, and `/return` remains
  available under every state.
- Any promotion of a method is gated on protected comparative evaluation under
  the governing spec.

## Verifying in this environment

The shell exports a `PYTHONPATH` pointing at a Python 3.14 site-packages, which
breaks both `pytest` collection and `PIL` inside any other interpreter. Clear it
for every test run:

```bash
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q

# `--with nltk` alone is not enough: the dashboard tests import fastapi/httpx
# and the catalog test imports pyyaml, so collection aborts with three errors on
# a clean machine. requirements-test.txt is the list that actually runs.

# NLTK_DATA is only needed if your corpora live outside the default lookup:
#   NLTK_DATA=~/nltk_data ...
```

The plugin declares `nltk`, but Hermes does not install plugin dependencies into
its own interpreter: if a state enters and every walk records
`failed · No module named 'nltk'`, install it where Hermes runs:

```bash
uv pip install --python "$(hermes --version >/dev/null; python3 -c 'import sys;print(sys.executable)')" \
  "nltk>=3.8,<4"
```

And always point `ANTEMUSE_STATES_HOME` somewhere temporary during verification —
the plugin shares one state file with the live agent, so a test that enters a
state will lock the agent's own tools until it exits.
