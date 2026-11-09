# Antemuse — before / after

Two development tasks × 3 seeds × 3 conditions, one model (`deepseek/deepseek-v4.1-flash-1017`), identical token budget.

| condition | what changes | n | mean words | mean pairwise distance | distance to baseline |
|---|---|---|---|---|---|
| A — baseline | nothing | 6 | 88.8 | 0.566 | 0.472 |
| B — placebo (creative instruction) | a creativity instruction | 6 | 89.2 | 0.599 | 0.564 |
| D — antemuse material | deterministic collider block | 6 | 141.5 | 0.561 | 0.61 |

## Blind pairwise (both orders, 2 judge families)

- **D_vs_A**: 8/9 consistent decisions (0.889)
- **D_vs_B**: 6/8 consistent decisions (0.75)
- positional (order-inconsistent) decisions: 7/24
- judges: reflection/beam-1.0-501b, upstage/solar-mini4 (the model under test never judges itself)

## Example — same task, same seed

**A — baseline**

> It was set flush into the chalk, a low iron door gone orange with rust, and when he laid his palm against it the metal was warmer than the morning sun should have made it. He told himself the tide had eaten the cliff back in the night, that a spring surge had prised some old smugglers' passage out of the rock—but the door's hinges were oiled, and the step before it was swept clean of shingle, and from somewhere behind the iron came a faint, patient knocking, as though something inside had heard him coming and was being polite about it.

**D — antemuse material**

> The wind was up, so he had to shout to himself to think — *not there yesterday, not there yesterday* — and by the third repetition the words had flattened into noise, pitch climbing, volume climbing, sense draining out, until he wasn't sure whether he was insisting or asking. He stood on the wet ledge with his lantern held high and caught the door's edges in the swing of light, and something in him began quietly tagging the thing: *wrong, wrong, suspect, wrong* — marking it the way a cell marks its broken parts, not to understand it but to have it eaten, engulfed, digested, gone. But the door did not dissolve under the tagging, and the tide was already licking the bottom step.

## What this shows and does not show

- It shows whether the material changes the three paragraphs this model writes, under a fixed budget, on two tasks.
- It does not establish a general effect: n=6 per condition, one model, dev tasks.
- Judges are order-controlled but not human-validated; treat win rates as directional.
- Material-condition outputs are noticeably shorter; length is a plausible confound in both the diversity numbers and the win rates, and is reported in the table for that reason.
- The plugin's preregistered state experiment (`experiments/state-settings/preregistration.md`) remains the evidence path; this page is the demonstration.
