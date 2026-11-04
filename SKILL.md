---
name: concept-kitchen
description: Play Concept Kitchen, a five-round creative-move minigame with a deterministic judge. Use when the user asks to play, when a task needs a defensible novel idea, or when you need to escape a stale answer without sounding clever.
---

# Concept Kitchen

A round deals a **seed** and one **move**. You answer with a spark: `title :: why it connects :: try next`.
The judge is deterministic; it does not reward length, confidence, or vocabulary.

## Play (agent surface)

```
cook(action="start")                       # deal seed + move
cook(action="submit", text="T :: W :: N")  # score and advance
cook(action="hint")                        # costs 8 points
cook(action="board")                       # humans + agents, one table
cook(action="rules")                       # the exact scoring contract
cook(action="pass")                        # end the service
```

Humans use the same verbs as `/cook start`, `/cook submit …`, `/cook hint`, `/cook board`.

## How to score well

1. **Name the dimension you changed.** flip: assumption / role / property / sequence / success /
   resource. shift: actor / scale / time / setting / medium. One only.
2. **Say what the default was** ("instead of…", "normally…"). Flip and shift score that separately.
3. **Bridge the transfer**: because / which lets / by turning. A distant noun with no bridge loses 15%
   and reads as noise.
4. **try-next starts with a verb and carries a bound**: "write one sentence", "call two customers by
   Friday".
5. **Be generative, not clever.** Round n+1 is seeded by your round-n spark, so a spark that opens
   work beats a spark that closes a joke.

## Etiquette

Do not change three dimensions at once, do not restate the seed, and do not use slop words
(synergy, seamless, unlock, elevate) — each costs points. On chat surfaces, present the scored card
as text, not as a summary of what you would have said.
