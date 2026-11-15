# State experience — findings and plan

Change id: `state-experience`
Status: **proposal — nothing built beyond one defect fix (see F8)**
Source: `specs/changes/state-audit/` (behaviour audit), `docs/design/states-context.html` (per-state
context), and a survey of the 14 plugins installed in this profile.

## The problem in one line

A state changes what the agent's turn is made of, and the person gets a line of arithmetic back. The
mechanism is sound; the outcome is invisible, and the display does not distinguish one state from
another.

## Findings

### F1 — The turn pays for the whole experimental engine

Measured from `__init__.py`: the `state` tool schema is **3,461 characters**, of which 810 is the
description. It carries `walk_new`, `walk_del`, `spark`, `keep`, `method`, `budget` and a `spec`
object in **every** turn of every conversation, whether or not a state is running. For comparison,
plan-mode's tool description is 506 characters.

Measured block sizes, first turn of each state: walk 437, daydream 528, dream 656, doomscroll 559,
unstuck 687, explore 427 characters. So the fixed schema costs roughly 5–8× a state's own material,
permanently.

### F2 — The account reports counts, not what happened

`_account()` builds `2 of 2 pairs · JOINED · joined ×2` and `1 of 1 directions`. The privacy rule
(`test_the_account_never_quotes_the_material_it_was_given`) forbids quoting daydream and dream
material, so counts were the safe choice — but the person learns nothing from a count. The safe
alternative was never built: name the *shared terms*, the *possibility*, or the *first move*, none
of which are the private text.

### F3 — The commonest ending has the weakest line

`stop()` returns a state-specific closing for `dry`, `failed`, `returned` and open-ended states, but
for `reason == "complete"` — the ordinary, successful ending — it returns the same sentence for
every state: *"The act is done, so the state is over. Carry what it gave you into the work."*
`states.after()` already has a better closing per state; it is used in the injected block but not in
the command reply.

### F4 — The pane cannot tell you what state you are in

The map shows the concept cloud, the walk's trail and the explore picks. There is no per-state mark
for daydream, dream, doomscroll or unstuck, and no strip showing the dose. The status chip says
"no state" or the label; that is the whole of it.

### F5 — A third visual language is still in the file

`desktop/plugin.js` carries an older ASCII/3D scene kit — `SCENES` with per-state strand counts, a
chamfered-box mesh kit, `probe.mode = 'ascii3d'`. It is used by that older surface only, and the map
never touches it. Either it should be deleted or deliberately revived as the state signature; leaving
it is a third language nobody can read.

### F6 — The outcome dies with the chat

Nothing a state produces is durable. The account is a residue report with a two-turn life, then gone.
A daydream's possibility, a dream's cross-project connection, an unstuck direction — all of it exists
only in the transcript. The one exception is `/explore`, whose picks reach the concept ledger.

### F7 — Discovery depends on knowing the commands

This historical proposal was superseded by the one-state cut: `/walk` is the only agent state and `/explore` remains person-driven. The pane nav has Antemuse and Cockpit; there is no catalogue, no contract
list, no "try it" affordance. The README explains them; the product does not.

### F8 — The tool schema omitted a state (fixed today)

The description and the `name` parameter both spelled five states — `walk|daydream|dream|doomscroll|explore`
— omitting `unstuck`, while the manifest, README and command surface had six. An agent reading the
schema had no reason to know `/unstuck` existed. Fixed in `__init__.py`, guarded by
`test_the_tool_schema_names_every_state` in `tests/test_session.py`.

### F10 — a repeated line spends a unit

Reproduced 2026-11-14 while prototyping examples: with a thin pool, `daydream` served **the same
pair twice** — turn 0 `1/2 pairs left` (pair A), turn 1 `0/2 pairs left` (pair A again) — and closed
`complete`. The dose counter counts lines, not distinct material, so a state can claim its full dose
while delivering one thing. `_is_failure_line` already filters failures out of the count; the same
filter does not exist for repeats. Candidates: dedupe against what this state has already served
before incrementing, and end `dry` when the pool cannot produce distinct material.

### F9 — Comparison with the plugins that share this profile

See `research-community-ux.md` for the ecosystem-wide version of this comparison: 1,379 catalog
entries, hook frequencies, and the UX patterns community plugins converge on. Two claims here were
narrowed by that research — `transform_llm_output` is used by 51 community plugins (not "only us and
plan-mode", which was true only of the four installed here), and the status bar is already occupied
by our chip.

Production lines (excluding tests), test lines, hook registrations:

- antemuse — 17,459 / 10,324 / 9
- tool-slimmer — 10,666 / 2,995 / 1
- toolaria — 6,549 / 7,475 / 3
- hermes-verifier — 6,527 / 5,692 / 5
- memlock — 4,745 / 4,133 / 3
- plan-mode — 3,465 / 9,306 / 11
- custodian — 3,099 / 1,121 / 4

Of the plugins installed in this profile, what only we do: served-vs-seen accounting, a
person-terminated state, a `specs/` directory with acceptance evidence, and no model calls on the
state path. What peers do that we do not:
`transform_tool_result` (plan-mode, toolaria) so a blocked tool says why; an approval surface with a
reason (plan-mode); `post_api_request` cost telemetry (plan-mode).

Our test-to-production ratio (59%) is healthy against the median (~60%) and far below plan-mode's
269% — but our absolute size is the largest in the set, and the schema cost in F1 is where it shows
up in the product.

## Options

### Outcomes

**O1 — A receipt instead of a count.** The account names what arrived safely (shared terms, the
possibility, the connection's two sides, the first move), what the model did with it, and one next
action. Constrained: never quote memory text; only terms and the model's own line.
*Cost*: `_account()` rewrite + one privacy test extension. *Risk*: leaking memory phrasing — bounded
by allowing only single terms and text the model already said in chat.

**O2 — Give `complete` its own closing per state.** Use the existing `states.after()` text in the
command reply, so a daydream ends by naming the possibility, a dream by naming the connection,
doomscroll by saying there was nothing to keep.
*Cost*: a few lines in `stop()`. *Risk*: none material; it is copy already written.

**O3 — An outcomes journal.** Append each state's product to `.antemuse/outcomes.jsonl` (state,
timestamp, project, the safe reference, the model's line), expose `state(action='outcomes')`, and
show the last three in the pane. The person accumulates a record instead of losing it.
*Cost*: new module + storage + pane read. *Risk*: clutter and a retention question; bounded to one
line per state by a cap.

**O4 — Make the obligation checkable.** Each state already tells the model what its reply must
contain. A structural check could catch the case where the reply ignores it (no judge, just shape:
does the closing turn contain the state's required element?). *Cost*: medium. *Risk*: nagging; only
worth it if receipts show the obligation is often missed.

### Display

**D1 — A state strip on the map.** Label, units served/seen, and the ending reason when it closes,
rendered in the pane the way the HUD is rendered in the cockpit. *Cost*: small, one JS file; reads
`/state` which already carries the governor.

**D2 — A signature per state on the map.** walk: the trail (exists). explore: picks (exists).
daydream: the two anchors pulse and a faint link between them. dream: an arc between the two
projects' clusters. doomscroll: a scatter of unrelated nodes, briefly lit. unstuck: a halo on the
unexplored gap the direction points at. *Cost*: medium; needs `/state` to carry the anchors.
*Risk*: decoration that implies more than the data knows — the arc must be a real relation or nothing.

**D3 — The receipt as a card.** The pane's corner note becomes a small end-of-state card with O1's
contents. *Cost*: small once O1 exists.

**D4 — A states page in the pane nav.** The catalogue: each state, its contract, its dose, what it
produces, and a button that enters it. *Cost*: medium (a new route + copy). *Risk*: none; this is the
discoverability fix.

**D5 — Retire or revive the ASCII scene kit.** Delete `SCENES`/`ascii3d` if the map is the surface,
or make it the signature vocabulary (D2) rather than a parallel language.

## Recommended plan

**Phase 1 — outcomes, cheap and honest.** O2 + O1 + D1. Every ending names its own product; the
account names what arrived within the privacy rule; the pane shows the dose. No new routes, no new
storage.

**Phase 2 — the map earns the state.** D2 + D3, with D5 decided first: the signatures either reuse
the scene vocabulary or replace it.

**Phase 3 — the record.** O3 + D4, once the receipts show what is worth keeping.

## Non-goals

- No model calls on the state path; a state stays arithmetic and memory.
- No rewriting the conversation history; the block is appended to the current turn only.
- No quoting of memory text in any person-facing surface.
- No approval cards; a state is an aside, not a gate.
- No new states and no change to the six doses.

## Open questions for the owner

1. Is a durable outcomes journal (O3) wanted, or is a better line per state (O1/O2) enough?
2. Should the map be state-specific (D2), or stay a neutral map with a strip (D1) and a card (D3)?
3. Chat stays text-only — confirm, or should the ending be allowed a small card?
