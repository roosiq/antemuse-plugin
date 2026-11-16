# Concept cockpit — acceptance

Run from the repository root.

## Commands

```bash
# full plugin suite
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q

# pane guards only
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with pytest --quiet pytest tests/test_cockpit_pane.py -q

# behaviour harness against the shipped module
/usr/bin/python3 tools/cockpit_harness.py

# bundle parses (no third-party module resolved by the host)
npx --yes esbuild@0.28.2 desktop/plugin.js --bundle --format=esm \
  --platform=browser --external:@hermes/plugin-sdk --external:react \
  --external:react/jsx-runtime --outfile=/tmp/p.js

# review artifact (synthetic payload, captioned in-frame)
/usr/bin/python3 tools/cockpit_video.py && \
  ffmpeg -y -i /tmp/cockpit-video/cockpit.webm -c:v libopenh264 -b:v 4M \
  -pix_fmt yuv420p -movflags +faststart /tmp/cockpit-video/shots.mp4
```

## Results (2026-11-14, convergence pass)

| Check | Result |
| --- | --- |
| `pytest tests/` | **922 passed, 1 skipped** |
| `pytest tests/test_cockpit_pane.py` | **18 passed** |
| `tools/cockpit_harness.py` | **26/26 passed** |
| esbuild bundle | parsed |
| installed copy | byte-identical to `desktop/plugin.js`, **175,230 B** |

The earlier rows in this file said 15 guards, harness 24/24, 893 passed and 153,170 B.
Those were true when written and had been false for several features' worth of work; the
numbers above are what the commands print now.

## Behaviour actually observed

Canvas and data:

- payload normalized into the cockpit (`nodes=120`, `lit=11`, trail 4 steps); backing
  store `1800×1120` at dpr 2
- every concept carries its stored position or is dropped; `lit` only from `w > 0.05`
- the pane's counts line for a dose-less state renders `3 picked · you end it · all tools`,
  never a countdown

Flight:

- `W` moves the ship 0.22; `D` banks it 1.08 rad; it coasts 0.197 units after the throttle
  is cut; `0` returns to home
- home to wall: `r 0.558 → 1.900`, and at the wall `speed 0.00` under a live throttle, with
  `y` unchanged (−0.358 → −0.355)

Edge:

- the boundary is three great circles at `0.9 × MAP_RADIUS`; the polar grid appears only
  near the plane
- `EDGE` reads remaining distance and goes negative past the wall; at the wall it reads
  `0.00`, with the accent `EDGE` label and brackets above the reticle

Shooting:

- holding the trigger fires a stream; shots exist in flight; release stops them
- an arriving shot picks a concept, a repeat hit raises interest to ×2, a deliberate miss
  at (4,4) leaves picks unchanged
- shots leave the two dash cannons, not the middle of the glass

Net and lifecycle:

- the net resolves to 13 concepts where the ray is densest; the caught list reaches the
  pane as 13 labels
- frames stop after `destroy()`, the pointer is released, no console errors
- lifecycle: keys are document-level, so the run continues when the canvas is not focused

Ledger:

- one volley of four shots on two known labels, measured against a copy of the live
  ledger: `w 0.000 → 1.000` for each label, graph `lit 0 → 2`

## Not covered here

- **In-app layout.** The harness proves the renderer in Chromium with a stubbed SDK; host
  placement (`placement: 'main'`) and tab behaviour are the host's business and have not
  been observed in the running desktop app.
- **Live `/graph` from the app.** The harness uses a synthetic payload because the route
  needs the gateway cookie. The live route was exercised through the plugin's own HTTP
  client against a copy of the ledger, not from the app.
- **Pointer lock inside Electron.** Wired and released correctly in Chromium; the Electron
  capture path has not been driven.
- **Light theme.** The cockpit now derives its ground from the resolved
  `--ui-background`; Playwright verifies `rgb(244, 244, 244)` under a light fixture.
- **Touch and narrow viewports.** Coarse pointer mounts named 44px touch controls,
  while the 390px Playwright run reports no horizontal overflow.
- **Reduced motion.** Playwright emulates `reduce`; it verifies a static initial
  frame, no free-running loop, and a responsive one-frame steer.
- **Pick-list ordering across a reload.** `state.hits` is session-local; the ledger write
  is not, so the map remembers and the list does not.
