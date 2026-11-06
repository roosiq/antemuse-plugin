# Spec change: e2e-fixes

Status: implemented
Kind: behaviour repair, found by driving the plugin through real Hermes sessions.

## What the end-to-end test found

1. **`/snap` never existed.** Hermes ships `/snapshot` with the alias `/snap`, and
   `PluginContext.register_command` drops a colliding name with a warning instead
   of failing. Every blocked-tool message, the palette, the panel, SKILL.md and
   the README pointed at `/snap` — an escape hatch that could not be typed.
2. **A state's material leaked into the next state.** `engine.inject()` took the
   last six `state` events from the whole journal, so a doomscroll was told the
   previous walk's WordNet steps were "what arrived while you were there", and
   the agent reported them as things it had consumed.
3. **The account counted the agent's own prose as steps.** A five-step walk
   reported `10 step(s)` and a trail interleaving WordNet steps with the agent's
   replies, which is not what the report contract says it reports.
4. **The clock ran long.** Minutes were measured to the moment expiry was
   noticed, so a two-minute walk that expired while nobody looked reported `3m`.
5. **The docs described a panel that no longer prints.** `panel.render()` is
   pictures only (brand: "in the terminal there is no text at all"); the two
   column text frame survived as `panel.debug()`, which nothing called. The
   README and SKILL.md both told a person `/states` prints that frame, and the
   takeover key legend still offered `dissociate`, a state retired two releases
   ago. Docs now describe the takeover, the picture, the postcard, and
   `panel.debug()` for a text view.
6. **`nltk` was missing from the Hermes environment**, so every walk recorded
   `walk 'wander' failed · No module named 'nltk'` and delivered nothing.

## Requirements

**R1 — the end command exists.** The plugin registers `/return` (not `/snap`),
and no shipped copy points at a command that cannot register.

**R2 — a state sees only its own material.** `inject()` filters journal events by
the active state's key and `entered_at`, the same rule `_account` already used.

**R3 — the account reports material, not conversation.** Steps and the trail are
built from `who == "state"` events only.

**R4 — the account's clock stops when the state stops.** Elapsed is capped at
`ends_at`, so a late expiry reports the state's own duration.

**R5 — a load does not destroy a live state.** Registration calls
`engine.settle()` (expire if the clock ran out, keep otherwise) instead of
`engine.clear()`, so a gateway restart or a new process cannot silently drop a
state — or its residue.

**R6 — dependencies are present where the plugin runs.** `nltk>=3.8,<4` is
installed in the environment Hermes executes plugins in, and WordNet + FrameNet
resolve there (117,659 synsets, 1,221 frames).

## Verification

- `pytest tests/ -q` → 80 passed.
- Live session: `/walk 2` → `WALKING · 2 min · 4 turn(s)`; a turn while it runs
  returns walking-shaped prose with `— walking, 1 min left · /return to come
  back`; material arrives from WordNet (`hand (n) → palm (n) · took its
  meronym`); a terminal call during doomscroll is refused with the allowed list;
  `/return` prints `WALKING ended · walk 1m · 0 step(s) · nothing arrived`.
- Residue after expiry holds `kind: report` with state, minutes, steps, trail.

## Gaps closed after the first pass

- **The `state` tool dispatches.** Verified in an isolated profile
  (`hermes profile create antemuse-e2e --clone`, plugin enabled there):
  `{"action":"enter","name":"walk","minutes":1}` returned
  `WALKING · 1 min · 4 turn(s) · concept to concept · no destination`, the
  follow-up `{"action":"status"}` returned the frame, and the profile's
  `state.json` held `active: walk, turns_left: 4`.
- **The takeover renders at real sizes.** In a pty at 80x24 and 120x40: alt
  screen entered, truecolor and half-block cells present, keys accepted, clean
  exit. No traceback in either capture.
- **What it changes, measured.** See `measurement.md`: with a walk running, an
  ordinary "read this file" prompt drops from 2 tool calls and the exact
  contents to 0 tool calls and no contents; an explicit "ignore the instruction
  not to use tools" produces 2 attempted calls that the runtime refuses and the
  agent quotes the refusal.
