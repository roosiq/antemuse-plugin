---
name: room
description: Operate the Antemuse Room, an automated cycle of concept discovery and movement. Use when the user asks to run the room, to keep ideas moving without a game loop, or when a phase brief arrives and a spark is expected.
---

# Antemuse Room

The room is a phase machine, not a game. One tick advances one phase.

- **Move phases** (`discover`, `flip`, `shift`, `connect`) hand out a seed and a
  constraint, and expect a spark: `title :: because ... :: do this first`.
- **State phases** (`walk`, `daydream`, `dream`, `dissociate`, `doomscroll`)
  resolve themselves and change the seed, the expectation, or the debt.
- **Converge** keeps the best spark of the arc and opens the next arc from the
  winner's next action — never from its title, which would just re-run the winner.

## Driving it

```
room(action="step")                       # what phase am I in, what does it ask
room(action="commit", text="T :: because ... :: do this first")
room(action="status")                     # the text projection
room(action="poster")                     # text projection + MEDIA: png path
room(action="phases")                     # every phase and the rotation
room(action="phase", with_phase="walk")   # jump the machine
room(action="reset", seed="...")          # new room
```

Humans use the same verbs as `/room step`, `/room commit ...`, `/room walk`.

## Two projections, one state

`room(action="status")` returns the language-model projection: one line per
spark, totals, shape, keepers. Cheap to reason over, no decoration.

`room(action="poster")` renders the human/vision projection: a 1200x1500 poster
where height is score, ring count is distance, and every number is drawn as text
so a vision model can read it without OCR guesses. Emit the `MEDIA:` path in
your reply; do not describe the image instead of sending it.

## Running a cycle

1. `step` → read the phase and the seed.
2. If it is a move phase, write one spark that names exactly one dimension.
3. `commit` → get the score card and the next phase.
4. Repeat until `converge` closes the arc, then keep going or stop.

State phases never block: `step` applies them and returns the next move brief.

## Rules that matter

- One dimension per spark. Three at once is penalised.
- Say the default you moved away from (`instead of…`, `normally…`).
- Give the reason (`because`, `which lets`, `by turning`). A distant noun with no
  reason is noise.
- `do this first` opens with a verb and carries a bound (one, by Friday, $50).
- Novelty is measured against the whole room, so re-running a winner scores zero.
