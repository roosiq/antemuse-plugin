# Antemuse — before / after

Two development tasks × 3 seeds × 3 conditions, one model (`openai/gpt-6.1-terra`), identical token budget. Every condition is asked for 120-140 words.

| condition | what changes | n | mean words | mean pairwise distance | distance to baseline |
|---|---|---|---|---|---|
| A — baseline | nothing | 6 | 128.8 | 0.499 | 0.416 |
| B — placebo (creative instruction) | a creativity instruction | 6 | 127.5 | 0.507 | 0.451 |
| D — antemuse material | deterministic collider block | 6 | 129.0 | 0.538 | 0.502 |

## Blind pairwise (both orders, 2 judge families)

- **D_vs_A**: 3/5 consistent decisions (0.6)
- **D_vs_B**: 3/8 consistent decisions (0.375)
- positional (order-inconsistent) decisions: 23/36
- judges: deepseek-v4.1-flash, reflection/beam-1.0-501b, upstage/solar-mini4 (the model under test never judges itself)

## Example — same task, same seed

**A — baseline**

> At low tide, Mara took the iron stairs down to the cliff and found the door standing where a seam of black rock had always been. Its paint was the faded red of a lifeboat, and a brass knocker hung from it in the shape of a hand. She touched the knocker; it was warm. From the other side came three slow knocks, followed by the scrape of a chair. “Just a moment,” called a voice she had not heard since the sea took her father twenty years before. Above her, the lighthouse lamp swung across the water, and for an instant the door’s keyhole shone blue. Mara put her eye to it. She saw the lamp room, the empty chair beside the window, and herself climbing the stairs.

**D — antemuse material**

> The keeper steadied himself on the wet steps and leaned close to the door. Its paint was the green of deep water, except where a white cross marked a splinter beside the latch. As he watched, thin black threads emerged from the crack and wrapped the marked wood. The splinter disappeared; the paint closed over it. Above him, the lamp swept the sea, its familiar sequence breaking into longer, brighter flashes until the whole horizon was a single white band. He shielded his eyes. When he looked back, a second cross had appeared, this one on the back of his hand. The threads slipped beneath the door and pooled around his boot. He lifted his hand toward the latch, and the white mark began to spread.

## What this shows and does not show

- It shows whether the material changes the three paragraphs this model writes, under a fixed budget, on two tasks.
- It does not establish a general effect: n=6 per condition, one model, dev tasks.
- Judges are order-controlled but not human-validated; treat win rates as directional.
- Material-condition outputs are noticeably shorter; length is a plausible confound in both the diversity numbers and the win rates, and is reported in the table for that reason.
- The plugin's preregistered state experiment (`experiments/state-settings/preregistration.md`) remains the evidence path; this page is the demonstration.
