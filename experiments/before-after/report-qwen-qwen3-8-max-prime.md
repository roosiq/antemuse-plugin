# Antemuse — before / after

Two development tasks × 3 seeds × 3 conditions, one model (`qwen/qwen3.8-max-prime`), identical token budget.

| condition | what changes | n | mean words | mean pairwise distance | distance to baseline |
|---|---|---|---|---|---|
| A — baseline | nothing | 6 | 96.7 | 0.507 | 0.422 |
| B — placebo (creative instruction) | a creativity instruction | 6 | 76.7 | 0.533 | 0.49 |
| D — antemuse material | deterministic collider block | 6 | 103.7 | 0.52 | 0.498 |

## Blind pairwise (both orders, 2 judge families)

- **D_vs_A**: 6/10 consistent decisions (0.6)
- **D_vs_B**: 4/10 consistent decisions (0.4)
- positional (order-inconsistent) decisions: 16/36
- judges: deepseek-v4.1-flash, reflection/beam-1.0-501b, upstage/solar-mini4 (the model under test never judges itself)

## Example — same task, same seed

**A — baseline**

> He descended the slick stone steps with the wind still tasting of salt and lamp oil on his lips, telling himself it must be a trick of storm-light or a trick of memory—until his boot struck wood where there had only ever been rock. The door was old, swollen with damp, its grain whorled like something grown rather than built, and set into the cliff face as though it had waited there for centuries. A rusted handle curved from its center, and when he leaned closer, he heard not the sea beyond it, but the faint, deliberate sound of breathing.

**D — antemuse material**

> He stepped closer, and the sea’s roar seemed to push a higher, thinner note out of him, as if his voice were trying to climb above the storm and tearing itself apart in the effort; the louder he called, the less his words meant, until even his own name sounded like a warning from someone else. The cliff face around the door was scarred with old salt and fresh scratches, and in his mind he began sorting the impossible details the way a body might mark damaged tissue for disposal—yesterday’s blank stone, today’s black hinge, the faint warm breath leaking beneath the wood—quietly feeding the broken facts to whatever part of him still had to keep watch.

## What this shows and does not show

- It shows whether the material changes the three paragraphs this model writes, under a fixed budget, on two tasks.
- It does not establish a general effect: n=6 per condition, one model, dev tasks.
- Judges are order-controlled but not human-validated; treat win rates as directional.
- Material-condition outputs are noticeably shorter; length is a plausible confound in both the diversity numbers and the win rates, and is reported in the table for that reason.
- The plugin's preregistered state experiment (`experiments/state-settings/preregistration.md`) remains the evidence path; this page is the demonstration.
