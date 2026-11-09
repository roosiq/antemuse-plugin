# Antemuse — before / after

Two development tasks × 3 seeds × 3 conditions, one model (`minimax/minimax-m3.1-flash`), identical token budget.

| condition | what changes | n | mean words | mean pairwise distance | distance to baseline |
|---|---|---|---|---|---|
| A — baseline | nothing | 6 | 223.3 | 0.524 | 0.436 |
| B — placebo (creative instruction) | a creativity instruction | 6 | 145.0 | 0.51 | 0.479 |
| D — antemuse material | deterministic collider block | 6 | 286.2 | 0.517 | 0.55 |

## Blind pairwise (both orders, 2 judge families)

- **D_vs_A**: 9/10 consistent decisions (0.9)
- **D_vs_B**: 11/11 consistent decisions (1.0)
- positional (order-inconsistent) decisions: 15/36
- judges: deepseek-v4.1-flash, reflection/beam-1.0-501b, upstage/solar-mini4 (the model under test never judges itself)

## Example — same task, same seed

**A — baseline**

> He stood a long while before touching it, because the cliff had taught him patience and the sea had taught him caution, and because the door — old iron, green with the particular green of things that have been drowned and brought up again — was set into the granite as cleanly as a keyhole, no mortar, no chisel marks, as though the rock had simply been persuaded to make room. He held his lantern up and looked at the hinges, at the sill worn pale in a shallow arc, at the flagstones below the threshold polished by feet that had gone out and in for a hundred years without once troubling the salt. And he noticed, in the same glance, that there was no salt on them. No weed, no crust, no droppings. The ledge before the door was swept clean. He had a lantern in one hand and no reason in the world to open it, and he thought of the logbook in his room upstairs with its columns of weather and its careful, unembellished sentences, and he thought of the winter coming, and the Relief boat that came twice a season and never on time. The door was warm. It breathed out at the edges of the frame a thin, slow exhalation of air that smelled of lamp oil and, under that, of something sweet and green, like apples left in a cellar. Somewhere above him the great lens began its nightly turn, and the light swept out over the water, and for one full revolution it did not touch the door at all, as if it knew better.

**D — antemuse material**

> The wind came up before he could reach the door, and he had to lean into it and shout — a shout that climbed in pitch and volume the way a voice always does against noise, strained past the point of carrying, so that the words he put into the gale came back from the rocks altered, their consonants eaten, his own warning returned as something that might have been a name. He drew back and listened, and the sea kept saying it in a lower register, patiently, without information, until the shape of what he had heard settled into a guess he was afraid to make.

By morning he had gone down to the store and come back with a stub of chalk and a coil of line, and he marked the door the way one marks a wound — a small cross, a tag on a thing not yet decided about. Then he set the lamp to its long turning rhythm and let the light find it. The beam swept the face of the cliff and touched the chalk, and the chalk, and the seam of stone around the frame, and the rock began, in the way rock does under a burning lens, to give. He watched a century of grit slough into the surf and thought of a body that had found something broken in itself and could not leave it lying there, and so had eaten it. By noon the door was a stain of pale sand, the cliff was whole, and he wrote in the log that the sea had done the work, which was almost true.

*Mechanisms used: the Lombard effect drives the keeper's shouted warning — pitched up by the storm and stripped of its content, so the message he sends is the message that returns to him distorted; selective autophagy drives the closing, as the chalk "tag" marks the intrusion and the lamp's beam mounts the digestion that removes it, leaving the cliff whole but the keeper's log incomplete.*

## What this shows and does not show

- It shows whether the material changes the three paragraphs this model writes, under a fixed budget, on two tasks.
- It does not establish a general effect: n=6 per condition, one model, dev tasks.
- Judges are order-controlled but not human-validated; treat win rates as directional.
- Material-condition outputs are noticeably shorter; length is a plausible confound in both the diversity numbers and the win rates, and is reported in the table for that reason.
- The plugin's preregistered state experiment (`experiments/state-settings/preregistration.md`) remains the evidence path; this page is the demonstration.
