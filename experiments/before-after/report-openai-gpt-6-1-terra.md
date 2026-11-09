# Antemuse — before / after

Two development tasks × 3 seeds × 3 conditions, one model (`openai/gpt-6.1-terra`), identical token budget.

| condition | what changes | n | mean words | mean pairwise distance | distance to baseline |
|---|---|---|---|---|---|
| A — baseline | nothing | 6 | 84.8 | 0.548 | 0.457 |
| B — placebo (creative instruction) | a creativity instruction | 6 | 92.0 | 0.461 | 0.476 |
| D — antemuse material | deterministic collider block | 6 | 85.8 | 0.579 | 0.53 |

## Blind pairwise (both orders, 2 judge families)

- **D_vs_A**: 2/4 consistent decisions (0.5)
- **D_vs_B**: 3/7 consistent decisions (0.429)
- positional (order-inconsistent) decisions: 25/36
- judges: deepseek-v4.1-flash, reflection/beam-1.0-501b, upstage/solar-mini4 (the model under test never judges itself)

## Example — same task, same seed

**A — baseline**

> The door was painted the same salt-white as the lighthouse, though the cliff around it was black stone. Its brass knob was warm. The keeper stood for a moment with his hand on it, listening to the sea drag pebbles across the shore below. Then something knocked from the other side: three quick taps, a pause, and two more. It was the signal his wife used to give when she came home with her hands full. She had been buried eleven years. He turned the knob, and the door opened inward onto a flight of stairs climbing through the rock, lit by the slow sweep of a lamp that should have been shining out to sea.

**D — antemuse material**

> The keeper climbed down to it through the spray. A ring of white shells had been pressed into the rock around the door, each one marking a crack; as he watched, the cracks narrowed and the shells sank out of sight. He called to the assistant above, raising his voice against the surf until the words broke into a shrill cry. The door opened a finger’s width. In the darkness beyond it, another hand gripped the edge—his own hand, with yesterday’s cut still fresh across the knuckles.

## What this shows and does not show

- It shows whether the material changes the three paragraphs this model writes, under a fixed budget, on two tasks.
- It does not establish a general effect: n=6 per condition, one model, dev tasks.
- Judges are order-controlled but not human-validated; treat win rates as directional.
- Material-condition outputs are noticeably shorter; length is a plausible confound in both the diversity numbers and the win rates, and is reported in the table for that reason.
- The plugin's preregistered state experiment (`experiments/state-settings/preregistration.md`) remains the evidence path; this page is the demonstration.
