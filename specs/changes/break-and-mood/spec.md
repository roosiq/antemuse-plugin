# Spec change: break-and-mood

Status: implemented
Kind: new surface (a way to step away) plus bookkeeping to recommend when.

## Goal

The states exist, but the agent has no way to *choose* one as a rest, and nothing
watches whether it should. A break should be available on demand, the agent
should pick which one, and the plugin should say when one is due.

## Requirements

**R1 — `state(action="break")` and `/break`.** With no argument, recommend (never
start anything). With an argument (`/break walk`), take that state whatever was
recommended — the choice belongs to the agent.

**R2 — mood is reported, not inferred from prose.** `state(action="mood",
feeling=...)` and `/mood <feeling> [note]` record one of `stuck`, `tired`,
`sharp`, `flat`, `saturated`. Reports older than four hours stop counting.
An unknown feeling is refused with the list.

**R3 — strain is arithmetic on things the plugin can see.** Minutes since the
last state (1.0 at 90 min), turns since it (1.0 at 30), failed tool calls since
it (1.0 at 6), plus the report's weight (`stuck`/`tired` +1.0, `saturated` +0.6,
`flat` +0.2, `sharp` −0.6). Clamped 0–3: `<1` carry on, `<2` break due, else
overdue.

**R4 — the recommendation matches the feeling.** `stuck`→walk, `tired`→daydream,
`saturated`→dream, `flat`→doomscroll, `sharp`→walk; with no report, walk below
strain 2 and daydream at or above it.

**R5 — told once, not nagged.** When a break is due and no state is active, the
turn carries one `[BREAK …]` line; the next offer waits 45 minutes.

**R6 — taking any state restarts the clock.** Entering a state appends to
`breaks` and zeroes turns, tools, and failures, so the recommendation reflects
work since the last rest.

**R7 — tool outcomes are observed.** `post_tool_call` counts calls and failures.
The counters live in memory and are flushed once per turn, not per tool call.

## Non-goals

- No model call to guess a mood, and no sentiment analysis of the agent's prose.
- No new state; the four remain.
- No automatic break — the plugin recommends, the agent decides.

## Affected paths

`core/mood.py` (new), `core/engine.py` (defaults, `note_turn`, `note_tool`,
`break_view`, `record_mood`, `take_break`, the offer in `inject`), `__init__.py`
(tool actions, `/break`, `/mood`, `post_tool_call`), `README.md`, `SKILL.md`,
`tests/test_mood.py`.

## Verification

- `pytest tests/ -q` — 99 pass, 12 of them in `tests/test_mood.py`.
- Live: `/mood stuck`, `/break` recommends, `/break walk` enters the walk, the
  offer line appears in a turn when due and not again for 45 minutes.
