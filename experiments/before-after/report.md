# Antemuse — before / after

Two development tasks × 3 seeds × 3 conditions, one model (`Qwen3.8 Flash Next`), identical token budget.

| condition | what changes | n | mean words | mean pairwise distance | distance to baseline |
|---|---|---|---|---|---|
| A — baseline | nothing | 6 | 113.8 | 0.594 | 0.495 |
| B — placebo (creative instruction) | a creativity instruction | 6 | 76.5 | 0.559 | 0.55 |
| D — antemuse material | deterministic collider block | 6 | 77.0 | 0.548 | 0.623 |

## Blind pairwise (both orders, 2 judge families)

- **D_vs_A**: 3/7 consistent decisions (0.429)
- **D_vs_B**: 2/11 consistent decisions (0.182)
- positional (order-inconsistent) decisions: 6/24

## Example — same task, same seed

**A — baseline**

> He wiped his rain-slicked glasses and leaned closer, his breath fogging in the sudden drop of temperature that seemed to radiate from the rock face. The stone was smooth and dark, lacking the usual jagged texture of the eroding cliffside, and a faint, briny scent drifted up from the seam where the door met the earth—a smell not of seawater, but of deep, stagnant caverns untouched by sunlight for centuries. His hand trembled as he reached out, not because he feared what might be behind it, but because the iron handle was warm, pulsing with a rhythm that matched the frantic beating of his own heart.

**D — antemuse material**

> Elias shouted his name into the salt-thick gale, his voice fracturing into a high, desperate shriek that distorted the very identity he sought to confirm; in that moment of self-preservation, he began to devour his own certainty, tagging every memory of yesterday’s solid rock with the suspicion of decay until the door itself seemed less like an intrusion and more like a necessary excision of a flaw he had previously ignored.

## What this shows and does not show

- It shows whether the material changes the three paragraphs this model writes, under a fixed budget, on two tasks.
- It does not establish a general effect: n=6 per condition, one model, dev tasks.
- Judges are order-controlled but not human-validated; treat win rates as directional.
- Material-condition outputs are noticeably shorter; length is a plausible confound in both the diversity numbers and the win rates, and is reported in the table for that reason.
- The plugin's preregistered state experiment (`experiments/state-settings/preregistration.md`) remains the evidence path; this page is the demonstration.
