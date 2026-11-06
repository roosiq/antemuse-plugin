# Spec change: state-return-report

Status: implemented
Kind: behaviour change to `core/engine.py` (no interface changes to `/walk`, `/dream`, `/snap`, `state`)

## Goal

Every state ends with an account of itself. When the agent comes back from a
walk, a daydream, a doomscroll or a dream, it says what happened in there — and
it says it because the plugin handed it the facts, not because the model was
asked to remember.

A state currently ends on a fixed line (`walked: a path through the graph, no
destination`). That line is a category, not an account: it is identical for every
walk and carries none of what actually arrived. The person watching saw the
pictures, so the agent is the only one who can tell them what it was.

## Non-goals

- Not a summary of the agent's own prose. The plugin reports the material it
  delivered; what the material meant stays the agent's job.
- Not persistence. The account decays on the same two-turn clock as residue.
- No model call. Producing the account must never wait on inference; states
  resolve without one and must keep doing so.
- No change to the panel, the scenes, the ticker cadence, or the journal cap.

## Requirements

**R1 — the account is built from the journal, not from a template.**
For the active state, take journal events whose `state` matches and whose `at`
is at or after `entered_at`. Report: state key, elapsed minutes, step count, and
a condensed trail (up to five distinct four-word heads, joined by `→`).

**R2 — every ending produces one.** `/snap`, `state(action="exit")`, turn
exhaustion, and clock expiry all produce the same account. Expiry is not a
silent path.

**R3 — the account is durable for two turns.** It is stored as a residue entry
with `kind: "report"` and `state`, and appended to the journal as an event named
`report`, so `watch_state` and the board can both see it after the fact.

**R4 — the agent is told to speak.** `stop()` returns the account in its tool
result, and the next turn's injected block leads with
`[YOU JUST CAME BACK — say what happened in there, in your own words, before
anything else]` followed by the trail.

**R5 — empty is still an account.** A state that received nothing reports
`nothing arrived` rather than an empty line or a false claim of activity.

**R6 — reports are distinguishable from the old canned residue.** Any residue
without `kind: "report"` keeps rendering as `[RESIDUE: ...]`. Nothing that reads
the residue list may assume every entry is a string.

## Acceptance criteria

1. `enter("walk")`, three `record("state", ...)` calls, `stop()` → message
   contains `WALKING ended`, `3 step(s)`, a word from each step, and an
   instruction to tell the person.
2. The same run leaves exactly one residue entry with `kind == "report"`,
   `state == "walk"`, `steps == 3`, and one journal event with
   `event == "report"`.
3. `inject()` on the following turn contains `YOU JUST CAME BACK` and the trail.
4. Forcing `ends_at` into the past yields the same injected block on the next
   `inject()`, with no `/snap`.
5. A state that recorded nothing reports `nothing arrived`.
6. `status()` and `watch_state()` still return, with reports shown as text.

## Affected paths

- `core/engine.py` — `_account`, `_expire`, `stop`, `inject`
- `tests/test_report.py` — new

## Must not change

- `definitions.STATES` fields, including the `residue` string, which stays as the
  short label for anything that still wants a category.
- Journal cap of 60, residue cap of 3, two-turn decay.
- `ticker` cadence and provider failure strings.
- Tool policy, `CONTROL_TOOLS`, and the `/snap` escape hatch.

## Verification

- `tests/test_report.py` (5 cases) exercises R1–R5 directly.
- The suite cannot currently be collected in the uvx environment: `PIL` ships a
  broken `_imaging` module there, and `tests/test_states.py` (unmodified) fails
  at import for the same reason. Behaviour verified by direct execution against
  a temporary `ANTEMUSE_STATES_HOME` instead; both endings and the empty case
  confirmed by hand.

## Open questions

- ~~Should the account include the events' edge names (`hypernym`, `antonym`) for
  walks, so a return can say *how* it moved rather than only *where*?~~
  **Resolved: yes.** Scheduled as task T7 in
  `specs/changes/scenes-per-surface/tasks.md`; the trail keeps its five-head cap
  and gains the relation in brackets.
