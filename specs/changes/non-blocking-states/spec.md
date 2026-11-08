# Spec: a state should not cut the chain it runs inside

Status: **implemented** 2026-11-08 (683 tests pass). Owner direction: *"Do these states need to be
blocking? Update the spec so they don't block message chains by default unless the
user wants that. Configurable via args."*

Companion changes: this amends the tool-policy clause of the §18 must-not-change set
in `creative-state-evidence`. Nothing else in that set moves.

## 1. The problem, stated as observed behaviour

A state currently carries a tool policy and `engine.policy()` enforces it before any
tool runs:

| state | `tools` in `core/states.py` | what the agent experiences |
| --- | --- | --- |
| walk | `None` | everything allowed |
| doomscroll | `["web_search", "web_extract", "read_file", "search_files", "browser_exec"]` | writes, patches, git, deploys all refused |
| daydream | `[]` | **every** tool refused |
| dream | `[]` | **every** tool refused |

So entering `daydream` or `dream` ends the work in progress. The state was meant to
change *how* the agent works for a few minutes, and instead it stops it. Observed
directly during the asset build on 2026-11-08: an asset generation run was interrupted
twice, once by `doomscroll` ("only web_search, … are available") and once by `dream`
("no tools in this state"), and each time the work could not continue until `/return`.

That is the wrong default. A state is a cognitive aside, not a lock. Nothing about a
daydream requires the file system to be unreachable — the directive and the art already
shape the reply, and the human-facing card is wordless regardless.

## 2. Decision

**States do not restrict tools unless asked to.**

- Default (`block` unset or `false`): every tool stays available for the whole state.
  The state still injects its directive, still marks the reply, still draws its art,
  still accrue its residue and its turn budget.
- Opt-in (`block: true`): the state's declared `tools` policy is enforced exactly as it
  is today — `None` means all, `[]` means none, a list means only those.
- Opt-in with a narrower set (`block: true, allow: [...]`) lets the caller keep a small
  list without editing `core/states.py`.

The rule this replaces, stated positively: **a state may never surprise the chain it is
running inside. If it is going to take tools away, the caller has to have said so.**

## 3. Arguments

`state(action="enter", …)` — the existing arguments are unchanged; three are added.

| arg | type | default | meaning |
| --- | --- | --- | --- |
| `name` | str | — | which state (`walk`, `daydream`, `doomscroll`, `dream`) |
| `minutes` | int | state default | duration, clamped as today |
| `walk` | str | `outer` | walk spec, unchanged |
| `block` | bool | **`false`** | enforce the state's tool policy |
| `allow` | list[str] | unset | with `block: true`, the tools to permit (overrides `tools`) |
| `method` / `seed` / `budget` | — | unset | unchanged; still gated by `experimental.enabled` |

`allow` without `block: true` is a caller mistake: it is refused with a message that
names the fix (`allow needs block: true`), not silently ignored.

Slash commands take the same flag: `/daydream --block`, `/dream --block --allow
read_file,search_files`, `/walk --block`. A flag that arrives without a value means
`true`.

The entry record keeps the shape it has: `active["options"]` already exists and is
"recorded, never acted on here", so `block` and `allow` live there. The projection must
carry a state's effective policy so the pane and the panel can say which mode is on.

## 4. What each surface says

| surface | non-blocking (default) | blocking (`block: true`) |
| --- | --- | --- |
| turn injection | `Tools are open in this state.` | today's text: `No tools in this state.` / `Only these tools: …` |
| `policy()` hook | returns `None` for every tool | blocks as today |
| panel / projection `tools` | `{"mode": "free", "allowed": [], "blocked": []}` | `none` / `some` / `all` as today |
| desktop pane | unchanged — counts, contract, art | unchanged |
| reply annotation | unchanged | unchanged |

`CONTROL_TOOLS = {"state"}` keeps working in both modes: `/return` and `state` are never
blocked, blocked mode included.

## 5. Non-goals

- No new states, no changed durations, cadence, turn budgets, or contracts.
- Not a change to what a state *is*: the directive still governs the reply, the art
  still governs what the human sees.
- No creative-quality claim either way. Turning blocking off is not a claim that states
  help; it removes an artefact that made them hard to run.
- No state may become always-on, and no default enables methods (`experimental.enabled`
  still gates `method`/`seed`/`budget`).

## 6. Acceptance criteria

1. With `block` unset, `engine.policy("write_file")` returns `None` while `daydream` and
   `dream` are active.
2. With `block: true`, the same call returns `{"action": "block", …}` for `daydream`,
   and `doomscroll` blocks `write_file` while allowing `web_search`.
3. With `block: true, allow: ["read_file"]`, `read_file` is allowed and `write_file` is
   blocked, for any state.
4. `allow` without `block: true` is refused, naming the fix; no state is entered.
5. The turn injection contains `Tools are open in this state.` in non-blocking mode and
   the existing block-language text in blocking mode; the directive and contract lines
   are byte-identical in both modes.
6. `CONTROL_TOOLS` stays available in blocking mode.
7. `projection.tools_of` reports `mode: "free"` for a non-blocking active state and the
   existing modes for a blocking one; the `FORBIDDEN` key tuple is unchanged, so no
   candidate text reaches a human surface.
8. `/return` works in both modes, unchanged.
9. The desktop pane renders identically in both modes — the state's card is wordless
   either way (`test_card_is_only_a_picture` unchanged).
10. The suite stays green with the *existing* denial tests rewritten to pass
    `block=True` rather than deleted — a behaviour change must not quietly drop the
    test that pinned the old behaviour.

## 7. Affected paths

- `core/states.py` — unchanged data; a comment that `tools` is now an opt-in policy.
- `core/engine.py` — `enter()` stores `block`/`allow`; `policy()` consults them;
  `inject()` picks the tool-rule line from the same decision.
- `core/options.py` — `block`/`allow` validation beside `method`/`seed`/`budget`.
- `__init__.py` — `enter` passes them; refusal text for `allow` without `block`.
- `dashboard/projection.py` — `tools_of` gains `free`.
- `plugin.yaml` — the description currently promises states "block forbidden tools
  before they run"; it must say "when asked".
- Slash commands — `--block`, `--allow`.
- `tests/test_states.py`, `tests/test_runtime.py`, `tests/test_plugin_api.py` — the
  denial tests gain `block=True`; new tests for the default.

## 8. Must not change

Durations, cadence, turn budgets, contracts, directives, residue labels, journal cap
(60), residue cap (3), the two-turn report decay, hook contracts, `/return`,
`CONTROL_TOOLS`, entry/exit/expiry without an LLM, and the wordless card. The asset work
in `immersive-visuals` is unaffected.

## 9. Verification

```bash
cd ~/antemuse-plugin
env -u PYTHONPATH /home/ryan/.local/bin/pytest -q                     # all
env -u PYTHONPATH /home/ryan/.local/bin/pytest -q tests/test_states.py tests/test_runtime.py
ANTEMUSE_STATES_HOME=$(mktemp -d) env -u PYTHONPATH python3 -c "
import sys; sys.path.insert(0,'.')
from core import engine
engine.enter('daydream')                       # no block: tools stay
print(engine.policy('write_file'))             # None
engine.stop(); engine.enter('daydream', block=True)
print(engine.policy('write_file'))             # {'action': 'block', ...}
"
```

## 10. Open questions for the owner

1. Should `block` default *off* on every state, or should `walk` keep `None` (all tools,
   effectively the same) and only the two no-tool states change? Proposal: one default
   for all four, so the rule is learnable.
2. Should the pane show a small marker when blocking is on (`tools closed`), or stay
   entirely wordless? Proposal: the panel and the injection say it; the pane does not.
3. Should a *user-facing* slash command be able to force blocking on a state the agent
   asked for? Proposal: not yet — one input path, args only.

## 11. What was built (2026-11-08)

Verified by running the engine, not by reading it:

```
enter daydream (default) -> DAYDREAMING · 3 min · 2 turn(s) · two memories · join only if it holds
  write_file: None
  terminal  : None
  injection : Tools are open in this state.
enter dream block=True   -> DREAMING · 30 min · 2 turn(s) · recombine stored concepts into new things
  write_file: {'action': 'block', 'message': 'the agent is dreaming; no tools in this state. /return to come back.'}
enter doomscroll block=True -> DOOMSCROLLING · 8 min · 3 turn(s) · random feed · consume, do not synthesize
  web_search: None | terminal: block
enter walk block=True     -> terminal: None        (walk declares no restriction, so asking changes nothing)
```

- `core/engine.py`: `_effective_tools()` is the single decision; `_tool_rule()` and
  `policy()` both read it, so the turn text and the hook cannot disagree. `enter()`
  takes `block=False, allow=None` as convenience kwargs and folds them into the
  existing `options` record.
- `core/options.py`: `block` must be a bool; `allow` without `block` is refused with
  *"allow needs block: true — without it every tool stays open"*.
- `dashboard/projection.py`: `tools_of(..., block=, allow=)` reports `mode: "free"` by
  default. The `FORBIDDEN` key tuple is untouched.
- `__init__.py`: only `method`/`seed`/`budget` require `experimental.enabled` now —
  the old check would have made `block` an experimental feature by accident.
- The three tests that pinned the old denial behaviour were **rewritten to ask for it**
  (`block=True`), not deleted; new tests cover the default, `allow`, and the refusal.

**Not done:** the slash-command flags (`/daydream --block`) in §3 are still unbuilt —
there is no command surface in `plugin.yaml` for them to hang on. Everything above is
reachable through `state(action="enter", block=true, allow=[...])`.
