# Comparison: the same task with a walk in the middle, and without

Run 2026-11-05, `antemuse 0.9.0`, live profile, one continuous session per column
(`hermes chat --resume`), same prompts, same model.

Task: "an SVG of a pelican riding a bicycle, 800x600", then "make the pouch beak
bigger and put a fish in it".

| step | with a walk | without |
|---|---|---|
| create the SVG | 5 files touched, 12 tool calls, 55s, 8,014 B | generator written + 2 vision passes, 35 tool calls, 2m55s, 10,657 B |
| refine (beak + fish) | **refused: 0 tool calls, file byte-identical**, deferred with the exact edit named | 2 tool calls (read + patch the generator), same turn, 11,440 B |
| finish | one word ("go ahead") after `/return` → 1 patch, 9,681 B | already done |
| turns to a finished artifact | 3 (+1 for the command) | 2 |
| renders as a pelican with a fish | yes | yes |
| vision-found defects | one visible leg, wing near but not gripping the bar, no chain | human-shaped bird knee, fish tail out the back of the beak |

## What the comparison says

The state does not damage the task. The thread survived the interruption: mid-walk
the agent named the precise edit (widen the pouch, add a fish with its tail past
the jaw), and after `/return` it applied that edit on the first word.

The state costs one interrupted turn and defers the edit by however long the
state runs. Nothing in either column suggests the walk made the drawing better or
worse — the 12-vs-35 tool-call gap is run-to-run variance in the *create* step,
which happened before any state existed.

So the effect measured here is scheduling, not quality: with a walk, work stops
for the duration and resumes from an account; without one, it never stops.

## Limits

One run per column, one model, one task. The create step differed by 3× in tool
calls with no state involved, which is exactly why no quality claim is made.
