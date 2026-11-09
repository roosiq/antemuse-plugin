# Antemuse — before / after

Two development tasks × 3 seeds × 3 conditions, one model (`moonshotai/kimi-k3.1-pro`), identical token budget. Every condition is asked for 120-140 words.

| condition | what changes | n | mean words | mean pairwise distance | distance to baseline |
|---|---|---|---|---|---|
| A — baseline | nothing | 6 | 134.7 | 0.462 | 0.385 |
| B — placebo (creative instruction) | a creativity instruction | 6 | 121.3 | 0.497 | 0.445 |
| D — antemuse material | deterministic collider block | 6 | 126.7 | 0.534 | 0.545 |

## Blind pairwise (both orders, 2 judge families)

- **D_vs_A**: 9/9 consistent decisions (1.0)
- **D_vs_B**: 5/6 consistent decisions (0.833)
- positional (order-inconsistent) decisions: 21/36
- judges: deepseek-v4.1-flash, reflection/beam-1.0-501b, upstage/solar-mini4 (the model under test never judges itself)

## Example — same task, same seed

**A — baseline**

> By noon the fog had thinned enough for Elias to see it plainly: a narrow iron door set into the black rock, its handle green with salt, though the stone around it was dry. He descended the cliff path with a lantern, counting the steps he had taken every morning for thirty years, and found the tide whispering behind him in a voice almost human. There was no keyhole, only his own name scratched beneath the hinge. When he touched the letters, something knocked once from within. Elias snatched back his hand. Above, the great lamp flared though he had left it cold, and its beam swept across the water, stopping on a small boat where a figure stood waving. The figure wore his oilskin coat, and even at that distance, Elias knew the face was his.

**D — antemuse material**

> Elias descended the cliff stairs through the storm and stopped where the rock had been solid at dusk. The door was narrow, iron-banded, wet with red rust. He shouted for Thomas, though Thomas had drowned eleven winters ago; the gale drove his voice higher until the name came back off the rock as a thin, shapeless cry. Something behind the iron answered in his own voice, gentler and perfectly clear: *Not Thomas. You.* Along the lintel, white marks circled splits in the stone, each one ticking like a finger bone. As Elias watched, the nearest fissure darkened, folded inward, and vanished, leaving the cliff smoother than before. The door was not opening, he realized. It was feeding. Then the lighthouse lamp went out above him, and from the black keyhole came the slow, patient sound of chewing.

## What this shows and does not show

- It shows whether the material changes the three paragraphs this model writes, under a fixed budget, on two tasks.
- It does not establish a general effect: n=6 per condition, one model, dev tasks.
- Judges are order-controlled but not human-validated; treat win rates as directional.
- Material-condition outputs are noticeably shorter; length is a plausible confound in both the diversity numbers and the win rates, and is reported in the table for that reason.
- The plugin's preregistered state experiment (`experiments/state-settings/preregistration.md`) remains the evidence path; this page is the demonstration.
