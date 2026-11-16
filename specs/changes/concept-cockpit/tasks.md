# Concept cockpit — tasks

Dependency-ordered. Every task carries the evidence that closed it; nothing here
is "done" on a claim alone.

## T1 — Pane, page, nav and command registration
- [x] `createCockpit` exported from `desktop/plugin.js`
- [x] Tab `cockpit` inside the Antemuse page (`/{ID}`), deep link `/{ID}/cockpit`,
      ⌘K command, copy keys `cockpit`, `cockpitOpen`
- Evidence: `tests/test_cockpit_pane.py::test_the_cockpit_is_a_tab_inside_antemuse`;
  esbuild parses the bundle; installed copy byte-identical to source.

## T2 — Data contract over the existing `/graph`
- [x] Poll `/graph` every 4000 ms; drop nodes without stored `x/y/z`; `lit` only
      from `w > 0.05`; carry `path` as the trail
- Evidence: harness `data: payload is normalized into the cockpit (nodes=120)`,
  `data: lit count survives (lit=11)`, `data: the walk trail is carried`.

## T3 — Canvas, chrome and HUD
- [x] Canopy arch, side pillars, curved dash, heading tape, reticle, throttle bar,
      readouts `HDG / PITCH / ROLL / SPD / NEAR / PICK / LIT`
- [x] `fit()` measures the parent box (not the canvas — measuring the canvas fed
      back into a 38,400px runaway)
- Evidence: harness `render: the glass has ink on it`, `canvas: ResizeObserver
  refits the backing store`.

## T4 — Flight model (bank, spool, momentum)
- [x] Roll in the camera basis; horizon banks with it
- [x] Throttle spools at `dt * 3.2`; thrust accelerates a velocity vector; drag
      `exp(-dt * 0.55)` (1.6 braking); speed cap 2.6; soft bounce at the volume edge
- Evidence: harness `flight: W moves the ship`, `flight: D banks the ship`
  (roll 1.08 rad), `flight: it coasts after the throttle is cut` (0.197 units).

## T5 — Pointer capture with a safe release
- [x] Click captures; `movementX/Y` steer; `Escape` releases; `destroy()` releases
- [x] Drag-look retained as the fallback when capture is refused
- Evidence: `test_the_mouse_can_be_captured_and_released`; harness drag-look path.

## T6 — Net resolved to density, not to a fixed distance
- [x] Sweep 0.3 → 2.4, score `count - depth * 0.3`, radius `max(0.08, depth*tan17°)`
- Evidence: harness `net: resolves to a set of concepts (caught=13)`;
  `test_the_net_opens_where_the_ray_is_densest`.

## T7 — Shooting: a held trigger, travelling bullets
- [x] Hold left button or `F` fires at `FIRE_INTERVAL`; release stops
- [x] Bullets travel (`BULLET_SPEED`), converge from alternating barrels
      (`CONVERGE`), expire (`BULLET_LIFE`), and collide swept (`segDist2`)
- [x] Hit increments `state.hits[label]`, sets target, fires `onPicks`, spawns a
      four-fragment burst
- [x] `pickList()` sorts by hits desc then label; pane renders `picked` with `×hits`
- [x] No lock/select: `lockAt` removed, locked chip removed, brackets are aim only
- [x] A shot is a plain dot (4px), no tail: slow travel is the whole effect
- [x] Two cannons on the dash; shots leave their muzzles and converge on the
      reticle, with recoil and a short muzzle flash
- Evidence: `test_shots_leave_the_cannons_not_the_middle_of_the_glass`;
  harness `shoot: holding fires a stream`, `shoot: an arriving shot picks a
  concept`
- Evidence: harness `shoot: holding fires a stream`, `shots exist in flight`,
  `the trigger is held`, `the trigger releases`, `an arriving shot picks a
  concept`, `interest accumulates on the target`, `a click fires at the pointer`;
  `test_shooting_is_a_stream_of_travelling_bullets`,
  `test_nothing_can_be_selected_only_shot`.

## T8 — Accessibility
- [x] `role='application'`, `tabIndex=0`, aria-label naming every control
- [x] Keyboard equivalents for every control: `W`/`S` throttle, `A`/`D` bank, `←`/`→`
      turn, `Q`/`E` pitch, `Space` net, `F` trigger, `0` home, `C` stow
- [x] Keys are document-level, so a pane that loses focus keeps flying; `destroy()`
      removes every listener and timer
- [x] Reduced motion is read from `prefers-reduced-motion` (two call sites)
- Evidence: `test_destroy_releases_every_listener_and_timer`,
  `test_the_cockpit_flies_like_a_ship_not_a_camera`; harness `lifecycle: destroy() stops
  the loop`, `lifecycle: no errors during the run`.

- [ ] **Reduced motion is read but not verified.** The code branches on the media query;
  no check asserts what the net or the bullet stream does when it is on. The earlier
  draft of this task claimed a harness check that does not exist.
- [ ] **No touch controls.** The cockpit has no on-screen thrust or net buttons and no
  two-finger mapping; a phone-sized viewport has not been measured. An earlier draft of
  this task claimed both.

## T9 — Guards, harness and review artifact
- [x] `tools/cockpit_harness.py` (behaviour checks, driven against the shipped module)
- [x] `tests/test_cockpit_pane.py` (static guards)
- [x] `tools/cockpit_video.py` records the harness for review
- Evidence: 26/26 harness, 18/18 guards, 922 passed / 1 skipped full suite.

## T10 — The map edge is a wall
- [x] `MAP_RADIUS = 1.9`; boundary drawn as three great circles at `0.9 × MAP_RADIUS`,
      plus a polar floor grid gated on `|cam.y| < 0.45R` and a `edge` label
- [x] `EDGE` HUD cell: remaining distance, negative past the wall, hot under 0.25
- [x] Contact clamps position to the sphere and zeroes the whole velocity — not the
      outward component alone, which left creep along the shell
- [x] The spring (`pull`) and the dead `bound = 6` box were deleted
- Evidence: `test_the_edge_is_a_wall_that_stops_the_ship` (position clamp present,
      no outward-velocity test, no spring, no box); measured in the harness: r 0.558 →
      1.900 with speed 0.00 held under a live throttle.
- Correction recorded: an earlier reading of "0.67 units of slide" was a misreading of
  home position, not drift. Home `y −0.358` → wall `y −0.355`.

## T11 — Instruments you can read from the seat
- [x] HUD label/value sizes derived from canvas width (10–13px / 13–18px)
- [x] Accent `EDGE` label with brackets above the reticle once `near > 0.85`
- Evidence: harness stills at 1440×900 @2x — `hud-home.png` and `hud-wall.png` read
  `HDG 000 · PITCH 0° · ROLL 0° · SPD 0.00 · NEAR … · PICK 0 · EDGE 0.00 · LIT …`.

## T12 — Picks reach the concept ledger
- [x] `engine.note_pick` writes one `served` row per pick with `move="explore"`
- [x] A broken ledger cannot lose the count: the write is wrapped and logged
- Evidence: `removed-state coverage`; measured against a copy of the live
  ledger — `abrasion` and `abrasive` `w 0.000 → 1.000`, graph `lit 0 → 2` after one volley.

## T13 — The state hands the person the door
- [x] Dock pane renders "open the cockpit" while `explore` is active
- [x] Status chip routes to the cockpit instead of settings during an explore
- Evidence: `test_an_explore_points_at_the_cockpit`.

## Not done

- [ ] Ordering of the pick list survives a reload (the ledger write does; `state.hits`
      does not)
- [ ] In-app verification of `placement: 'main'` inside the running desktop app
- [ ] Host placement and tab behaviour observed rather than reasoned about
- [ ] Port the flight model to the standalone prototype (deliberately dropped — the
      standalone is the abandoned prototype, and the plugin is the deliverable)
