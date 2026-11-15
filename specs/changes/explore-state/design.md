# `/explore` — design

The decisions this change is made of, and the alternatives each one replaced.

## A state, not a trigger

`/explore` is a state because a state is the only thing the agent already knows how to be
*inside*. It changes the directive the model is held to (stay out of the way), it appears in
every surface (`/state`, the pane, the reply annotation), and it ends with an account.

Alternatives rejected:

- **Open the cockpit when `/walk` runs.** A walk is the agent moving; a person flying the
  same map would be a second driver on a trip that already has one.
- **Take over placement `main` when a map-shaped state is active.** A surface that changes
  under a person because a state happened is a takeover, and the app already has a nav.
- **Replace the Antemuse page entirely.** Two surfaces reading one payload is the design;
  deleting one to add the other loses the survey view.

## No dose, and three places that had to stop counting

A dose is how a state ends itself. An explore has none, so every path that ends a state on
its own had to learn that "nothing owed" is not "nothing left":

- `_expire` returns early when the dose is zero — otherwise `served >= 0` is true on
  arrival and the state would close inside its own `enter`.
- `complete_if_dosed` returns early for the same reason: a state cannot be complete when it
  never had a target.
- `note_turn`'s dry-turn rule skips the open-ended case, because serving nothing is normal
  when the person is the one choosing.

The fourth place is language, and it came last: `status_line`, `annotate()` and
`state(action="status")` each printed "N picks left" from their own copy of the arithmetic.
Two of them said `0 picks left` — a countdown to nothing, which reads as already over. All
three now go through `_left_phrase`, which returns `open · you end it` when the dose is zero.
Three surfaces, one lie is what duplicated arithmetic produces.

## Picks are posted as deltas

The pane keeps what it has already sent per label and posts only the difference, debounced,
flushing on `destroy()`. Posting the cumulative list on every hit would multi-count: three
hits on `salt` would file six rows.

The route refuses to record anything when no explore is running, so a stray volley after
`/return` cannot attach to the next session. A non-list body is a 400, not a 500.

## A pick is a sighting, not just a counter

The first version wrote the counter into the state record and stopped there. The count moved
and the map did not, which is the one thing the person is looking at. Each pick is now also a
`served` row with `move='explore'`, which both moves the pane's weights and records the
provenance honestly: chosen by a human, served by no state.

The ledger write is wrapped and logged. A broken ledger must not lose the count, and it must
not fail the shot.

## The state offers its own surface

While `explore` is active the dock pane renders "open the cockpit" and the status chip
routes to the cockpit instead of settings. No automatic navigation: the person decides to
fly, and the state hands them the door rather than opening it for them.

## What this design does not claim

- No efficacy claim: nothing here says flying the map produces better ideas.
- No persistence of pick *ordering* — `state.hits` is session-local. The ledger write
  survives; the cockpit's own ranking does not.
- A pick of a label the projection does not know is counted in the account and cannot light
  anything on the map.
