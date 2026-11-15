# Lessons

Design and engineering mistakes this project has already made, so the next pass does not make
them again. Each one is a correction from the person using it, or an incident that shipped.

## The display is retro, the resolution is not

"Retro" means CRT: phosphor, grain, scanlines, a vignette. Downsampling the render to look
old is a different thing and it was rejected. **The tube is an effect layer over a crisp
canvas, never a low-resolution render.**

## The pane wears the app's theme, not the plugin's

A brand palette was built, installed, and then replaced: `--ui-accent`, `--ui-text`,
`--ui-stroke`, `--ui-panel-background`. A pane with its own colours is a second product that
has to be re-skinned every time the app changes. **Read the host's variables; keep only
neutrals for the hardware.**

## Motion has to be visible in the first second

A recording of the cockpit was reported as "literally nothing happens". Two causes: the pane
was measuring the wrong box (a 38,400px canvas), and the flight was too fast to stay in frame
— at `THRUST 0.2` the ship left the cloud in four seconds and the last third of every take was
empty glass. **Prove motion from the first frame, and keep the subject in frame for the whole
shot.**

## A wall stops the ship

A soft spring is not a wall. Thrust and pull equilibrated at `r ≈ 1.95` with a residual
`0.002 u/s` of tangential creep, which reads as "still moving". Contact clamps position and
zeroes velocity outright. **If the design says wall, the code says zero.**

## Keys must not depend on focus

`Input.dispatchKeyEvent` stopped reaching the page once the ship stalled, and a canvas-scoped
listener meant a pane that lost focus stopped flying. **Listen at the document, and remove the
listener in `destroy()`.**

## A state with no dose cannot count down

Three surfaces printed `0 picks left` for `/explore`: `status_line`, `annotate`, `status()`.
A countdown to zero reads as already finished. **One helper produces the phrase
(`_left_phrase`), and every surface calls it.**

## Bookkeeping must never cost a turn

A `KeyError: 'turns_left'` in the residue tick raised inside `_pre_tool_call`, and a raising
policy hook closes the tool channel for the whole profile. **Fail open at a lockout, fail
closed at a write, and log the cause.**

## Evidence is not the harness

The harness renders the shipped module in Chromium with a synthetic payload. That is good
evidence about the renderer and no evidence about the app: placement, pointer lock in Electron,
the live `/graph` route and the light theme are all unobserved. **Say which one you measured.**

## A spec that cites a test nobody wrote is worse than no spec

Four plausible test names were invented in a draft, and two older specs were still citing
guards deleted with a palette. **`tests/test_docs_current.py` now checks every citation
against the suite and the harness.**

## A state that serves nothing cannot be shown as one that serves something

`walk` injects a directive and no material, by design. Prototyping an example produced a block that
would have read "Arrived: (nothing)" — true, and it looks like a bug. **Examples have to show the
thing the state actually produces: the path for walk, arrivals for the rest.**

## A repeated line is not new material

A thin pool made `daydream` serve the same pair twice and close `complete`. Counts are not material:
**dedupe against what the state already served before a unit is spent.** Generated content is where
this shows up first, because a generator asks the engine for something a human would have skimmed
past.

## Numbers in documentation rot

"Six commands" survived the seventh, "the pane is the only visual surface" survived the
cockpit, "12 properties" survived a harness that grew to 26. **Derive counts from code in a
test; never write a test count in prose.**
