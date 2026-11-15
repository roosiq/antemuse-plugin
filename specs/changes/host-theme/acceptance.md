# Acceptance — host theme

## Commands and results

| Check | Result |
| --- | --- |
| `pytest tests/` | **893 passed, 1 skipped** |
| `pytest tests/test_cockpit_pane.py` | **15 passed** |
| `tools/cockpit_harness.py` | **24/24 passed** |
| esbuild bundle | parsed |
| installed copy | byte-identical to `desktop/plugin.js` |

## Observed

- Harness page declares `--ui-panel-background:#131313`, `--ui-text-secondary:#d9d3c8`,
  `--ui-accent:#d2643f`: the still's field is `#111`-range after grain, type is the
  warm light grey, and the only chromatic pixels are accent marks.
- No page errors; flight, net and shooting unchanged.

## Not done

- No per-theme retuning of contrast: `dim` is `text` at 0.6 alpha, which is fine on
  the dark themes checked and unverified on a light theme.
- ~~The harness and video pages stub the host variables; the pane has not been
  screenshotted inside the running desktop app in this change.~~ **Verified in the
  running app** (CDP on the desktop build, port 9444): route `#/antemuse/cockpit`,
  canvas 2140x1306, palette read from the app's own variables, no render error,
  and firing with `F` picked `author` (×9) in the pane's panel.
- A stale module load showed `BRAND is not defined` until the plugin file was
  touched to force a hot reload. The pane needs a reload after a palette change;
  the error was the old module, not the new code.
