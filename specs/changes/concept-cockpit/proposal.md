# Concept cockpit — fly the graph, shoot to pick

Change id: `concept-cockpit`
Repo: `antemuse-plugin`
Status: implemented, unreleased (working tree; `plugin.yaml` still `0.10.44`)

## Goal

Let a person **stumble into concepts** instead of searching for them. The
existing concept map answers "what is near what" and wants orbiting; this change
adds a second surface that answers "what is over there" and wants a heading.

Delivered as one desktop pane, `cockpit`, reading the same `GET /graph` payload
the map pane already polls. Nothing is re-projected, invented, or fetched from a
second source — a concept without a stored 3D position is dropped, and a concept
is hot only if the walk ledger says it fired.

Three mechanics, in the order they were built:

1. **Flight** — first-person movement through the concept cloud: bank, throttle,
   momentum, pointer capture.
2. **The net** — a thrown cone that lands where the ray is densest and gathers a
   whole knot at once.
3. **Shooting** — Asteroids, not a sniper rifle: hold the trigger and a stream of
   bullets walks across the field. Shots travel, can miss and expire; whatever
   they hit is picked, and repeat hits raise that concept's *interest*, which is
   what orders the pick list. There is no click-to-select step.

Four things were built after this proposal was drafted, and they belong to the same
change rather than to four forgotten ones:

4. **The map edge** — the cloud is bounded at `MAP_RADIUS` (1.9 units). Contact is a
   wall, not a spring: position clamps to the sphere and the whole velocity is zeroed,
   so holding the throttle produces nothing. The boundary is drawn as three great
   circles (so it is visible from any attitude) at 0.9× the stop radius, with a polar
   floor grid when the ship is near the plane, and `EDGE` in the HUD counts the distance
   remaining, negative past the wall.
5. **Legible instruments** — HUD labels and values scale with the canvas (labels
   10–13px, values 13–18px) instead of sitting at a fixed 9px, and when the ship is
   pinned at the boundary an accent `EDGE` label with brackets appears above the
   reticle: from the seat, facing out, the wall is behind you.
6. **Picks that move the map** — every shot is filed as a pick and written to the
   concept ledger as a `served` row with `move='explore'`. The pane's weights and `lit`
   count therefore answer to what the person shot, not only to what a state served.
7. **A door to the surface** — while `explore` is running, the dock pane renders
   "open the cockpit" and the always-on status chip routes there instead of to
   settings. A state whose whole point is another pane cannot leave the person to find
   it in the navigation.

## Non-goals

- No new backend route, no schema change to `/graph`, no second projection.
- No persistence of picks or interest beyond the session (see Open questions).
- No audio.
- No pointer cursor or selection step: aiming shows brackets, the shot is the
  interaction.
- No non-desktop surface: the pane is `placement: 'main'` because a first-person
  view in a 320px rail is a letterbox.
- Not a replacement for the map pane. Both stay.

## Why a second surface instead of a camera mode

The map's core interaction is orbit-and-look-at; the cockpit's is heading-and-go.
Folding them into one surface forces one of the two to be a lie — either the map
inherits a heading you do not want, or the cockpit keeps an orbit you cannot use.
Both surfaces read the same route so they can never disagree about position.

## Why interest is a counter, not a highlight

"More shots = more interest" only means something if interest is *stored and
ordering*. A shot increments `state.hits[label]`; `pickList()` sorts by it. If
the counter lived in the render loop it would tint a light and nothing else.

## Acceptance

See `acceptance.md`. Summary as of the convergence pass: harness 26/26, pane guards
18/18, full suite 922 passed / 1 skipped, installed copy byte-identical at 175,230 B.

## Open questions

- **Interest ordering is session-local; the ledger write is not.** Resolved in part:
  picks now write `served` rows (`move='explore'`), so the map's weights and `lit` move
  with what was shot. What is still local to the session is the *ordering of the pick
  list inside the cockpit* (`state.hits`). Making that survive a reload means giving the
  pane a read of the ledger rather than a counter of its own — a pane-level decision, not
  a schema one.
- **A label with no position cannot light.** A pick of a concept the projection does not
  know counts in the account but changes nothing on the map. Accepted for now; the
  account names it, so the person can see it was counted.
- **One pick reaches the top of the weight scale.** A single hit takes a node to `w 1.000`.
  If that reads as too eager, weighting by count is the fix; the data is already there.
- **Placement hint untested in-app.** `placement: 'main'` was chosen by reasoning
  about rail width, not observed; the host is the authority and the pane has only
  been exercised in a Chromium harness.
- **Pointer lock in Electron** is assumed to work like Chromium. Drag-look
  remains the fallback if a host refuses the capture.
