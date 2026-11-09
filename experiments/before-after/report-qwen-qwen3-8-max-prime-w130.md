# Antemuse — before / after

Two development tasks × 3 seeds × 3 conditions, one model (`qwen/qwen3.8-max-prime`), identical token budget. Every condition is asked for 120-140 words.

| condition | what changes | n | mean words | mean pairwise distance | distance to baseline |
|---|---|---|---|---|---|
| A — baseline | nothing | 6 | 112.3 | 0.542 | 0.452 |
| B — placebo (creative instruction) | a creativity instruction | 6 | 125.8 | 0.447 | 0.465 |
| D — antemuse material | deterministic collider block | 6 | 123.8 | 0.433 | 0.476 |

## Blind pairwise (both orders, 2 judge families)

- **D_vs_A**: 5/9 consistent decisions (0.556)
- **D_vs_B**: 4/10 consistent decisions (0.4)
- positional (order-inconsistent) decisions: 17/36
- judges: deepseek-v4.1-flash, reflection/beam-1.0-501b, upstage/solar-mini4 (the model under test never judges itself)

## Example — same task, same seed

**A — baseline**

> He descended the slick stone steps, oil lamp trembling in his grip, and found the door set into rock where only barnacled granite had stood at dusk. It was pale as driftwood, banded with iron that wept rust into the salt air, and its handle wore the shape of a curled wave. When he pressed his ear to it, he heard not the hollow hush of a sea cave but the slow turning of gears, distant bells, and a voice reciting the names of ships lost decades ago. The keeper knew every tide, every crack in this coast, yet the keyhole breathed warm light against his boot, as though some patient room beyond had been waiting all night for him to remember how to enter.

**D — antemuse material**

> He pressed his ear to the door and heard the sea amplified into a speech too loud to understand, each wave shouting louder until the warning became mere roar. His pulse climbed into his throat, and he called out to himself, but the noise stripped his words of their edges, turning his name into a blunt, useless bell. In the lamp room above, the light swept the same black water it had always swept, while below, the cliff seemed to digest the old stone steps, swallowing their cracks and salt scars into a new dark frame. He realized the door had not been added; the rock had eaten yesterday’s absence and left only a mouth where memory could no longer find its footing.

## What this shows and does not show

- It shows whether the material changes the three paragraphs this model writes, under a fixed budget, on two tasks.
- It does not establish a general effect: n=6 per condition, one model, dev tasks.
- Judges are order-controlled but not human-validated; treat win rates as directional.
- Material-condition outputs are noticeably shorter; length is a plausible confound in both the diversity numbers and the win rates, and is reported in the table for that reason.
- The plugin's preregistered state experiment (`experiments/state-settings/preregistration.md`) remains the evidence path; this page is the demonstration.
