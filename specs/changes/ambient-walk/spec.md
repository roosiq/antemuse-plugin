# Spec change: ambient-walk

Status: implemented
Kind: behaviour change to the `walk` state and to what happens when it ends.

## Goal

A walk should run *beside* the work, not instead of it. Today it takes every
tool away for twelve minutes, so any task in flight stops dead — measured on the
pelican job: the edit was refused, the file stayed byte-identical, and the work
waited for `/return`. A person who wants the agent to think while it works
cannot use it.

The walk becomes ambient: longer, sparser, tools open. When it ends the agent
summarises what the walk was and gets on with the job.

## Requirements

**R1 — longer.** Default 30 minutes (was 12), 12 turns (was 4). A walk is
something that happens across an afternoon's work, not a coffee break.

**R2 — sparser.** One step every 90 s (was 18 s): 20 steps over half an hour
instead of 40 over twelve minutes. Material should arrive between actions, not
compete with them. `ticker` and `deliver_if_due` already honour `cadence`.

**R3 — tools stay open.** `tools: None` for walk: every tool remains available.
The walk no longer blocks anything, so `pre_tool_call` returns None and the
escape hatch matters less — `/return` still ends it early.

**R4 — the directive is about company, not substitution.** It must say the work
continues: react to a step when it arrives, let it touch the work if it touches
it, do not stop, do not pad, do not turn the reply into a walk essay.

**R5 — the account names the relations.** The return line says how the walk
moved, not only where: `hand→metacarpal vein [meronym]`. This also removes the
repeated shared node (`hand (n) → metacarpal vein (n) → metacarpal vein (n)`).

**R6 — summarise, then resume.** On exit the injected block asks for three
lines — where it went, what it touched in the work, what happens next — and
then to continue the task. The account stays the same length; only the framing
changes.

## Non-goals

- No new state. The other three keep their strict tool policy; `dream` still
  closes everything.
- No change to how material is chosen (WordNet `wander`, glossed steps).
- No model call to produce the walk itself.

## Affected paths

`core/states.py` (walk spec), `core/engine.py` (`_account` trail, the return
block), `README.md`, `SKILL.md`, `tests/test_states.py`.

## Verification

- `pytest tests/ -q` green, including a test that a walk permits a tool call
  and that `dream` still refuses one.
- Live: start a task, enter the walk, take a turn that needs a tool — it must
  run — then `/return` and check the summary/resume block and the account.

## Verification: live

Run on the pelican session (`--resume`), with the plugin reloaded:

- `/walk 30` → `WALKING · 30 min · 12 turn(s) · work continues · a step may interrupt`, palette shows `/walk 30 min · 12 turn(s) · all tools`.
- A tool-needing turn **mid-walk** read and patched the SVG (8,014 → 11,912 B) with nothing refused. Under the old contract that edit was blocked and the file stayed byte-identical.
- `/return` →
  `WALKING ended · walk 5m · 5 step(s) · vein→brachial vein [hyponym] → brachial vein → walk→wading [hyponym] → wading → night→lights-out [meronym]`
  and the block asks for three lines, then work.
- Next turn opened with exactly three lines — where the walk went, what it touched in the drawing ("brachial veins are the ones running down the thing that grips a bar… the grip read as flat"), and what happens next — then went straight back to editing (11,912 → 12,484 B, six vision passes on the grip).

**Timing note:** that resume turn exceeded a 300 s harness timeout and was interrupted mid-verification. Ambient walking plus an exacting visual task can run for minutes; the walk did not cause it (the agent was doing vision checks on the drawing). Give long turns a longer ceiling.

## Revision: sped up, same dose

Measured first, then tuned. The creativity probe found no dose-response and almost
no uptake (1 of 30 delivered hops used), so the half-hour length bought nothing
measurable. It also overshot the evidence it was based on: the walking study in
`docs/creativity-exercises.md` ran **eight minutes**, not thirty.

`walk` is now **10 minutes at one step every 30 s** — still 20 steps, the same
dose, in a third of the time and inside a single work session. Turns 12 → 8.

Verified: `/walk` reports `WALKING · 10 min · 8 turn(s) · work continues · a step
may interrupt`; the palette agrees; a unit test pins the arithmetic
(`minutes * 60 // cadence == 20`) and another proves material waits the cadence
and then arrives again. 101 tests pass.
