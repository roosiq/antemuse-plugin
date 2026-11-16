# Concept cockpit — design

## Surface

`desktop/plugin.js`, one uncompiled ES module. Registrations:

| Kind | Id | Detail |
| --- | --- | --- |
| Pane | `cockpit` | `placement: 'main'`, title copy `cockpit` |
| Page | `/{ID}/cockpit` | survives a collapsed tab |
| Sidebar nav | `cockpit` | codicon `rocket`, label `cockpitOpen` |
| Command | ⌘K | "Open concept cockpit" |

Constants: `COCKPIT_POLL_MS = 4000`, `COCKPIT_MEET = 0.16` (world units that
count as met), `COCKPIT_GLASS_FRACTION = 0.15` (dash height share),
`REDUCED_LIFE = 260` ms (tracer lifetime).

## Data contract

One route: the same `GET /graph` the map pane polls, on a 4s cadence. Nodes carry
stored `x/y/z`; the cockpit drops any node without one rather than guessing a
position. `w > 0.05` marks a fired concept (`lit`), and `path` is the walk trail.
Render budget: labels only under `dist < 0.34`, capped at 40, so 1400 nodes do not
label the sky.

## Flight model

Camera state is `{x, y, z, yaw, pitch, roll, speed, vx, vy, vz}`.

- **Basis** — forward from yaw/pitch; right and up built level, then banked around
  forward by `roll`. Roll reaching the basis is what makes a turn read as flying.
- **Roll** — `A`/`D` at `1.6 * 1.5` rad/s, wrapped to ±π. Keyboard parity: `←`/`→`
  yaw, `Q`/`E` pitch.
- **Throttle** — `W`/`S` (or `↑`/`↓`), `Shift` ×2.2. Spools at `dt * 3.2`; the
  ship has weight instead of snapping to full.
- **Momentum** — thrust (`THRUST = 2.1`) accelerates a velocity vector; drag is
  `exp(-dt * 0.55)`, or `1.6` while braking with `S`. Cut the throttle and the
  ship keeps gliding, so a turn slides through the cloud.
- **Limits** — speed capped at 2.6 u/s; pitch clamped to ±1.15 rad (66°); the
  ±1.6 unit volume **bounces** at 0.35 restitution rather than clamping to a stop.
- **Horizon** — drawn rotated by `-roll`; a level horizon under a rolled view is
  the one cue that betrays a panning camera dressed as a cockpit.

## Aiming

Two paths, same handler:

- **Pointer capture** — first click requests pointer lock; relative `movementX/Y`
  steer, the reticle is the aim, `Escape` releases and exits (a drawn button does the
  same), and `destroy()` releases too so
  the pane can never trap the app.
- **Drag-look** — fallback when a host refuses capture (and what the harness uses).

## The net (area gather)

`space` throws a cone. `resolveNet` sweeps depth 0.3 → 2.4 in 0.1 steps and scores
`countAt(depth) - depth * 0.3`, where `countAt` counts nodes within
`max(0.08, depth * tan(17°))` of the ray. The net lands at the best depth, so a
throw into a gap still lands on a knot instead of teaching that empty space is a
catch. Caught nodes feed `onCatch` and the pane's list.

## Shooting (Asteroids)

- **Hold** the left button or `F` to fire. `FIRE_INTERVAL = 0.16` s — four to six
  shots a second, the Asteroids cadence. Right-drag looks; a click also captures
  the pointer.
- **The map has an edge, and it is a wall.** `MAP_RADIUS = 1.9` is drawn as
  three great circles — a sphere, not a flat ring, because a flat circle sits
  entirely behind you when you are below the plane or nose-out at the limit —
  over a faint polar floor grid of two rings and twelve spokes, which only draws
  when the ship is near the cloud's plane. Contact clamps the position to the
  radius and zeroes the velocity: flying into it stops the ship dead with the
  map in front of you. Cancelling only the outward component left enough
  tangential creep to walk the ship along the shell, so contact is a full stop.
  An earlier radial spring reached equilibrium with the throttle and pinned the
  ship at the boundary instead of stopping it; the box bound at 6 was dead code
  behind it and is gone. The edge brightens to `--ui-accent` and labels itself
  `edge` as you approach, and `EDGE` in the HUD reads the distance to it,
  negative once past. The grid is painted in `--ui-text` at low alpha —
  `--ui-stroke-secondary` is already a translucent mix and disappears when
  multiplied down again.
- **Two cannons** sit on the dash at `GUN_X = 92` px either side of the
  centreline, `GUN_LEN = 30` px tall, canted 22 px outward — solid barrels with a
  dark bore, a bright lip, a mount plate and a short muzzle flash for the first
  frames after a shot. Shots leave those muzzles, not the middle of the glass.
- `shootAt(aim)` builds a bullet: origin at the muzzle, `MUZZLE_REACH = 0.12`
  units from the eye (the cloud is only about a unit across, so a longer reach
  started every shot inside a neighbour and swallowed it), velocity
  `BULLET_SPEED = 0.45` u/s — at 1.0 the shot crossed the glass in a couple of
  frames and was never seen.
- The muzzle aims at `aimPoint(d)`: the nearest concept under the reticle, or a
  point `CONVERGE = 1.4` units out when the crosshair is on nothing. A fixed
  convergence distance made the guns shoot wide at every other depth, because the
  muzzle sits well below the eye line.
- `gunScreen(side)` returns the muzzle position and applies `GUN_KICK = 0.09` s
  of recoil, which decays in the frame loop.
- `stepBullets(dt)` advances each shot, decrements `BULLET_LIFE = 3.2`, and tests
  **swept** collision (`segDist2`) against nodes within `BULLET_R = 0.055`. A
  point test tunnels at these speeds; a miss keeps flying and expires.
- A hit increments `state.hits[label]`, sets the target, calls `onPicks`, and
  pushes a four-fragment burst for 340 ms.
- Rendering: each shot is a plain white dot, 4 px, with no tail, no flare and no
  glow. Asteroids is a dot that moves slowly; the movement is the effect.
- `pickList()` filters to hit nodes and sorts by `hits` desc, then label.
- There is no `lockAt`: the pane drops the locked chip, and the reticle brackets
  are an aiming aid, not a selection.

## HUD

`HDG / PITCH / ROLL / SPD / NEAR / PICK / LIT` across the curved dash, a heading
tape with a centre pointer, throttle bar bound to actual airspeed, and a net/pick
panel in the pane's DOM. `SPD` is `|v|`, not the throttle setting — those diverge
the moment you coast.

## Accessibility and safety

- `role: 'application'`, `tabIndex: 0`, and an `aria-label` naming every control.
- Keyboard equivalents for all gestures: fire, net, home, throttle, yaw, pitch.
- `prefers-reduced-motion` resolves the net immediately and skips flight easing.
- Mobile: touch controls present, no horizontal overflow at 390×844.
- Listener hygiene: `pointerlockchange` removed and pointer released on destroy;
  the frame loop stops.
- Colours only from `--ui-accent`, `--ui-text-secondary`, `--ui-text-quaternary`,
  `--ui-stroke-secondary`, `--ui-panel-background`. No literals.

## Verification surfaces

- `tools/cockpit_harness.py` — import-map + stub-SDK harness importing the
  **shipped** file, driving it on a real canvas. Behaviour, not markup.
- `tests/test_cockpit_pane.py` — static guards: one route, no random positions,
  theme-only colours, box tracking, balanced listeners, densest-ray net,
  poll pacing, interest ordering, pointer release.
- `tools/cockpit_video.py` — records the harness for review (synthetic payload,
  captioned in-frame).
