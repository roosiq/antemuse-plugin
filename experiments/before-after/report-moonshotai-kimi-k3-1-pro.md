# Antemuse — before / after

Two development tasks × 3 seeds × 3 conditions, one model (`moonshotai/kimi-k3.1-pro`), identical token budget.

| condition | what changes | n | mean words | mean pairwise distance | distance to baseline |
|---|---|---|---|---|---|
| A — baseline | nothing | 6 | 107.7 | 0.565 | 0.471 |
| B — placebo (creative instruction) | a creativity instruction | 6 | 102.2 | 0.509 | 0.515 |
| D — antemuse material | deterministic collider block | 6 | 136.2 | 0.488 | 0.536 |

## Blind pairwise (both orders, 2 judge families)

- **D_vs_A**: 9/9 consistent decisions (1.0)
- **D_vs_B**: 5/6 consistent decisions (0.833)
- positional (order-inconsistent) decisions: 21/36
- judges: deepseek-v4.1-flash, reflection/beam-1.0-501b, upstage/solar-mini4 (the model under test never judges itself)

## Example — same task, same seed

**A — baseline**

> Elias had kept the light for thirty-one years, and in all that time the cliff had shown him nothing but gulls, guano, and the long white scars left by winter storms. Now a narrow door stood in the rock, painted the same blistered red as the lamp room, its brass handle green with age. He touched the stone around the frame; it was cold, solid, unbroken. From beyond the door came three slow knocks—not the tapping of a branch or a boat adrift, but three measured knocks, followed by silence, as if someone were listening. Elias glanced up at the lamp, still turning though dawn had paled the sky, and thought of the logbook upstairs, where yesterday’s entry ended in his own hand: *All quiet. Nothing to report.* Then the handle began to turn, and a voice he had not heard since he was nine years old said, “You took your time.”

**D — antemuse material**

> The keeper leaned into the gale and shouted, but the harder he tried to be heard, the louder and shriller his voice became, until his question—*Who’s there?*—reached him as nothing but a shapeless cry. He closed his mouth. Beneath the boom of the surf he heard a soft ticking: pale flecks had gathered around every split plank and rusted bolt, and the damaged wood was drawing inward in gray threads, leaving clean grain where the rot had been, as if the door were patiently devouring its broken parts to keep itself whole. Then the flecks went dark one by one. The door opened a finger’s width, and from the black gap his own voice said, quiet and perfectly clear, “You should not have let it mend.”

## What this shows and does not show

- It shows whether the material changes the three paragraphs this model writes, under a fixed budget, on two tasks.
- It does not establish a general effect: n=6 per condition, one model, dev tasks.
- Judges are order-controlled but not human-validated; treat win rates as directional.
- Material-condition outputs are noticeably shorter; length is a plausible confound in both the diversity numbers and the win rates, and is reported in the table for that reason.
- The plugin's preregistered state experiment (`experiments/state-settings/preregistration.md`) remains the evidence path; this page is the demonstration.
