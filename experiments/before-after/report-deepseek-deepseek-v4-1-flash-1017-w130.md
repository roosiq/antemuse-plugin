# Antemuse — before / after

Two development tasks × 3 seeds × 3 conditions, one model (`deepseek/deepseek-v4.1-flash-1017`), identical token budget. Every condition is asked for 120-140 words.

| condition | what changes | n | mean words | mean pairwise distance | distance to baseline |
|---|---|---|---|---|---|
| A — baseline | nothing | 6 | 126.5 | 0.574 | 0.479 |
| B — placebo (creative instruction) | a creativity instruction | 6 | 115.0 | 0.544 | 0.525 |
| D — antemuse material | deterministic collider block | 6 | 137.7 | 0.489 | 0.562 |

## Blind pairwise (both orders, 2 judge families)

- **D_vs_A**: 8/9 consistent decisions (0.889)
- **D_vs_B**: 6/8 consistent decisions (0.75)
- positional (order-inconsistent) decisions: 7/24
- judges: reflection/beam-1.0-501b, upstage/solar-mini4 (the model under test never judges itself)

## Example — same task, same seed

**A — baseline**

> The door was set into the limestone where no seam had been before, its iron hinges rusted as though they had held for a century. Keeper Elias Thorne pressed his palm against the salt-bleached wood; it was cold, colder than the cliff around it, and when he pulled his hand away, moisture clung to his fingers like breath on glass. Gulls wheeled overhead, suddenly silent. He told himself the tide had shifted the rockface, that winter storms did such things—but the door had a brass handle, worn smooth by hands that were not his. Below, the sea sucked at the cave mouth with a sound almost like whispering. Elias fetched the lamp-room key ring, though he knew, even before he tried them, that none of the keys would fit.

**D — antemuse material**

> The wind was up and the sea noisy, so when he shouted back at the cliff — a startled, wordless *hello?* — his own voice pitched high and loud, and the answer he thought he heard was swallowed by the distortion of it; whatever the door was for, shouting at it told him nothing. He climbed down anyway, and as he went he found himself doing what the body does with damage: tagging it, marking the wrong thing for removal. The green paint blistered where yesterday there had been clean stone; rust freckled the hinges; a hairline crack ran the lintel. His mind kept wrapping those flaws in little flags, as if to say *this is broken, take it away,* and he noticed he was already deciding how to report it — how to have it eaten, quietly, before anyone asked why it hadn't been there before.

## What this shows and does not show

- It shows whether the material changes the three paragraphs this model writes, under a fixed budget, on two tasks.
- It does not establish a general effect: n=6 per condition, one model, dev tasks.
- Judges are order-controlled but not human-validated; treat win rates as directional.
- Material-condition outputs are noticeably shorter; length is a plausible confound in both the diversity numbers and the win rates, and is reported in the table for that reason.
- The plugin's preregistered state experiment (`experiments/state-settings/preregistration.md`) remains the evidence path; this page is the demonstration.
