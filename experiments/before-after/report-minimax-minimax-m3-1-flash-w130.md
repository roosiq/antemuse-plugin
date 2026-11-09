# Antemuse — before / after

Two development tasks × 3 seeds × 3 conditions, one model (`minimax/minimax-m3.1-flash`), identical token budget. Every condition is asked for 120-140 words.

| condition | what changes | n | mean words | mean pairwise distance | distance to baseline |
|---|---|---|---|---|---|
| A — baseline | nothing | 6 | 119.7 | 0.524 | 0.437 |
| B — placebo (creative instruction) | a creativity instruction | 6 | 138.7 | 0.501 | 0.486 |
| D — antemuse material | deterministic collider block | 6 | 142.5 | 0.564 | 0.571 |

## Blind pairwise (both orders, 2 judge families)

- **D_vs_A**: 9/10 consistent decisions (0.9)
- **D_vs_B**: 11/11 consistent decisions (1.0)
- positional (order-inconsistent) decisions: 15/36
- judges: deepseek-v4.1-flash, reflection/beam-1.0-501b, upstage/solar-mini4 (the model under test never judges itself)

## Example — same task, same seed

**A — baseline**

> The door was old oak, its surface silvered with salt, and its hinges set directly into the living rock. He ran his fingers along the frame, searching for the gap where the cliff

**D — antemuse material**

> He shouted for his partner, and the wind took the shout and twisted it, so what reached the gallery above was a mangled thing, high and cracked, carrying no word but the alarm in it. He tried again, louder

## What this shows and does not show

- It shows whether the material changes the three paragraphs this model writes, under a fixed budget, on two tasks.
- It does not establish a general effect: n=6 per condition, one model, dev tasks.
- Judges are order-controlled but not human-validated; treat win rates as directional.
- Material-condition outputs are noticeably shorter; length is a plausible confound in both the diversity numbers and the win rates, and is reported in the table for that reason.
- The plugin's preregistered state experiment (`experiments/state-settings/preregistration.md`) remains the evidence path; this page is the demonstration.
