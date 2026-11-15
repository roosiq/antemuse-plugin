# Nous brand pass — acceptance

Run from the repository root.

## Commands

```bash
# full plugin suite
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q

# cockpit guards only
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with pytest --quiet pytest tests/test_cockpit_pane.py -q

# behaviour harness against the shipped module, with a still for review
COCKPIT_SHOT=/tmp/brand-cockpit.png /usr/bin/python3 tools/cockpit_harness.py

# bundle parses
npx --yes esbuild@0.28.2 desktop/plugin.js --bundle --format=esm \
  --platform=browser --external:@hermes/plugin-sdk --external:react \
  --external:react/jsx-runtime --outfile=/tmp/p.js
```

## Results (2026-11-13)

| Check | Result |
| --- | --- |
| `pytest tests/` | **893 passed, 1 skipped** (59.4s) |
| `pytest tests/test_cockpit_pane.py` | **15 passed** |
| `tools/cockpit_harness.py` | **24/24 passed** |
| esbuild bundle | parsed, `Done in 6ms` |
| installed copy | byte-identical to source (153,170 B) |

## What review of the stills changed

Two vision passes over harness stills, each finding a real defect:

1. Concept labels ran off the left edge (`cept-29`) and heading numbers were cut
   mid-glyph (`010`, `060`). Fixed: labels flip to the other side of the point
   and are dropped when neither side fits; tape numbers only draw when fully
   inside the tape.
2. `LIT` read as an in-joke and every readout was yellow. Fixed: renamed
   `FIRING`, and yellow is now reserved for `PICK` and `FIRING` — interest, not
   decoration.

## Not verified

- **DOM panels in a browser.** The harness renders the canvas only; the net list,
  pick list and locked chip are covered by static guards and were not
  photographed. In-app inspection after a plugin reload is the honest next check.
- **The display face.** `Rules Gothic Condensed` is proprietary and absent here,
  so stills show the `Liberation Serif` fallback. Machines with Bodoni or Didot
  will differ.
- **Light app theme.** The cockpit ground is opaque blue by design; nobody has
  looked at it inside a light-themed app.
- **Full-bleed legibility at small pane sizes.** Reviewed at 1280×760 and
  900×560; a 320px-tall pane was not re-checked after the type changes.
