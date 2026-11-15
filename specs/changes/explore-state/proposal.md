# `/explore`: the state a person drives

## Goal

A sixth state whose whole point is that the human is at the controls. `/explore`
opens a mode with no dose, no clock, and no machine-side material: the person flies
the concept map in the cockpit, shoots the concepts they want, and ends the state
themselves with `/return`. What they shot is the residue — counted per concept, named
back to them, and available to the agent on the next turn.

## Why a state and not a pane

The plugin already draws a map, but a pane is a thing you visit and close. A state is a
thing the agent knows it is in: it changes the directive the model is held to ("stay out
of the way"), it shows in every surface (pane, CLI status line, `/state`), and it ends
with an account. Entering `/explore` is the trigger; nothing takes over the app on its
own.

## Non-goals

- No automatic ending: no dose, no dry-turn close, no timer.
- No agent-side picking. The agent may answer questions during the state; it may not
  choose concepts, propose a route, or narrate the session.
- No new persistence store. Picks live in the state record that already exists.
- No change to the five existing states' doses or contracts.

## Acceptance

1. `/explore` is registered like the other state commands and appears in `/state`,
   the pane's counts line, and the tool's schema.
2. An explore cannot be closed by the engine: not by dose, not by a dry turn, not by
   expiry. `peek()` still reports it after several turns and deliveries.
3. The pane posts picks to `POST /api/plugins/antemuse/picks`; outside an explore the
   same call records nothing, and each pick becomes a `served` row (`move='explore'`) so
   the map's weights move with what the person chose.
4. `/return` names the picks by count and asks the agent to work one of them.
5. No hook can be taken down by a state record missing a field: `_pre_tool_call`
   returns a decision or nothing, never an exception.
