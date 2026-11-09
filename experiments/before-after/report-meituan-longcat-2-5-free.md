# Antemuse — before / after

Two development tasks × 3 seeds × 3 conditions, one model (`meituan/longcat-2.5:free`), identical token budget.

| condition | what changes | n | mean words | mean pairwise distance | distance to baseline |
|---|---|---|---|---|---|
| A — baseline | nothing | 6 | 135.2 | 0.564 | 0.47 |
| B — placebo (creative instruction) | a creativity instruction | 6 | 119.0 | 0.5 | 0.499 |
| D — antemuse material | deterministic collider block | 6 | 142.2 | 0.487 | 0.583 |

## Blind pairwise (both orders, 2 judge families)

- **D_vs_A**: 2/6 consistent decisions (0.333)
- **D_vs_B**: 2/8 consistent decisions (0.25)
- positional (order-inconsistent) decisions: 10/24

## Example — same task, same seed

**A — baseline**

> The keeper, a man named Aldric who had tended the light for thirty-one years without once finding anything new in the rock, knelt and pressed his palm flat against the door. It was warm. Not sun-warmed—something deeper, something that pulsed faintly against his lifeline like a second heartbeat. There was no handle, no keyhole, only a seam of pale light that traced the outline and widened by a hair when he leaned close enough to hear the sea moving on the other side. Except the sea, he realized with a stillness creeping up his spine, was not on the other side of this wall. The sea was forty feet to the east, and what he heard through the stone was water moving in a current, steady and patient, going somewhere it had been going long before the lighthouse was built. He stood, wiped the salt from his hands onto his coat, and went back up the spiral stairs to log the hour, because the light did not tend itself, and because he had learned in three decades that some doors announce themselves only after you have decided not to open them.

**D — antemuse material**

> The keeper shouted into the howling wind, but his words came out twisted and unrecognizable, as if the noise had eaten the meaning before it could escape his lips.

He pressed closer, and the door seemed to watch him the way a cell marks its damaged parts for destruction—tagging this impossible intrusion, this broken piece of the cliff, to be swallowed and digested by whatever machinery kept the world whole.

He reached for the handle. The metal was warm.

## What this shows and does not show

- It shows whether the material changes the three paragraphs this model writes, under a fixed budget, on two tasks.
- It does not establish a general effect: n=6 per condition, one model, dev tasks.
- Judges are order-controlled but not human-validated; treat win rates as directional.
- Material-condition outputs are noticeably shorter; length is a plausible confound in both the diversity numbers and the win rates, and is reported in the table for that reason.
- The plugin's preregistered state experiment (`experiments/state-settings/preregistration.md`) remains the evidence path; this page is the demonstration.
