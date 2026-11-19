# Worked examples

Examples are generated from the engine by `tools/examples.py`, never written by hand.
They show one worked example for every agent state: `walk`, `daydream`, `doomscroll`,
`dream`, and `unstuck`.

## Format

```text
Situation: what the person is doing
Command:   one state command
Material:  the provider output, where the state has material
Account:   the line written when the state ends
```

A walk has no arrival block: its path is scenery and is not injected into the model
turn. Daydream, doomscroll, dream, and unstuck show provider material. Doomscroll's
feed text is shown only in its labelled untrusted block and is never persisted.

## Current scenarios

| # | Situation | Command | What it demonstrates |
|---|---|---|---|
| 1 | Distance while work continues | `/walk` | A six-hop path changes the frame while work continues. |
| 2 | Two things you said make an idea | `/daydream` | Two of this chat's own messages, what links them, one idea. |
| 3 | Three useless things from the feed | `/doomscroll` | Gated public feed material is distraction, not instruction. |
| 4 | The day recombines within the project | `/dream` | Local git subjects connect without reading transcripts. |
| 5 | One move breaks the stall | `/unstuck` | Your commits and an unused map link ground one next move. |

## Generation

```bash
python3 tools/examples.py
python3 tools/examples.py --check
```

The generator drives the engine in a fresh temporary home and writes
`docs/EXAMPLES.md`. Its check confirms every state scenario is present and avoids a
hand-written, stale example.

## Acceptance

- `tests/test_examples.py` verifies generation, the README link, no random seed, and
  that the walk example does not imply material arrived in the model turn.
- `docs/EXAMPLES.md` is generated output, not a product specification.
