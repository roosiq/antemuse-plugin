# Worked examples

Examples are generated from the engine by `tools/examples.py`, never written by hand.
They show the two current surfaces: the agent's one walk state and the person-driven
explore mode.

## Format

```text
Situation: what the person is doing
Command:   /walk or /explore
Path:      a walk's recorded hops, or the person's own picks
Account:   the line written when the mode ends
```

A walk has no arrival block: its path is scenery and is not injected into the model
turn. Explore has no agent-provided material: the person's picks are what its account
reports.

## Current scenarios

| # | Situation | Command | What it demonstrates |
|---|---|---|---|
| 1 | A familiar roadmap needs distance | `/walk` | A six-hop path changes the frame while work continues. |
| 2 | You want to look around yourself | `/explore` | The person chooses concepts and `/return` names the picks. |

## Generation

```bash
python3 tools/examples.py
python3 tools/examples.py --check
```

The generator drives the engine in a fresh temporary home and writes
`docs/EXAMPLES.md`. Its check confirms both scenarios are present and avoids a
hand-written, stale example.

## Acceptance

- `tests/test_examples.py` verifies generation, the README link, no random seed, and
  that the walk example does not imply material arrived in the model turn.
- `docs/EXAMPLES.md` is generated output, not a product specification.
