---
name: antemuse
description: Take and leave five bounded agent states — walk, daydream, doomscroll, dream, and unstuck — alongside the person-driven map (explore). Use when the user asks the agent to step away from the desk, work at a distance, or when a state is already active and governs this turn.
---

# Antemuse

A state is a bounded change to how the agent behaves, not a place it goes.

- `tools` — what it may still touch (walk stays open; daydream and dream take tools away)
- `directive` — injected into the turn it governs
- `contract` — the one line the reply is held to
- `residue` — what it carries back when the state ends

## Entering and leaving

```
/walk [graph]        /daydream      /doomscroll
/dream               /unstuck       /explore
/return
```

That is the whole command surface — seven verbs. `/walk` follows six hops on its
declared graph provider (WordNet by default), one bought per turn, recorded for the
pane and never injected into the turn. `/daydream` lets two memories meet and name one
possibility; `/doomscroll` delivers three random feed items without turning them into a
lesson; `/dream` recombines local commit subjects across the day; `/unstuck` names one
direction from history and the concept graph. `/explore` is person-driven: it has no
dose and no end of its own, the cockpit is the map, and what you keep is counted (`K`
keeps, `T` drops, `tools/hit_rate.py` reports the rate). It closes when the person types
`/return`, and the account names the concepts they picked, by count. A person's own
message is journalled as a note automatically while a state runs, so there is no
`/note`; the recommendation arrives in the turn by itself, so there is no `/watch`.

Agents use the tool instead: `state(action="enter", name="walk")`,
`state(action="exit")`, `state(action="status")`, `state(action="break")`,
`state(action="list")`. There is no action that asks for a picture: the pane draws
the state you are already in.

## The panes

The picture lives in two desktop panes and nowhere else: the Antemuse pane draws
the map, and the cockpit tab flies it in first person for `/explore`. In chat a
state posts its account as text, on entry, without media. There is no terminal
takeover and no image frame: `/state` is not a command, and a terminal reads the
same text record the chat gets.

## Taking a break

`state(action="break")` recommends; `state(action="break", name="walk")` takes
it. `state(action="mood", feeling="stuck")` is how you say how the work feels —
`stuck`, `tired`, `sharp`, `flat`, `saturated`. The measurement comes from turns,
and failed tool calls since the last state, so the recommendation is arithmetic,
not a guess. Ignore it when the work is nearly done; the nudge waits ten turns.

## Rules

- Never enter a state to avoid work; enter it to change what the work looks like.
- Never encode a defect in a test, and never assert a substring as if it were behaviour:
  `assert js.count("onExit()") >= 2` passed with the Escape call deleted, because the button
  and the teardown also call it. Slice to the branch, or drive it in a harness.
- Verify the environment the app actually runs in. The packaged pane refuses
  `requestPointerLock()` with `WrongDocumentError: The root document of this element is not
  valid for pointer lock`, so steering rides document-level pointer events with a sticky
  `engaged` flag — not the lock, and not `setPointerCapture` (it throws `InvalidStateError`).
- A harness that grants what the app refuses proves nothing: `tools/cockpit_harness.py` stubs
  `requestPointerLock` to reject so the captured-steering path is the one exercised.
- Every behavioural claim in a release note needs an assertion that fails when the claim is
  false. If no mutation makes it fail, the claim is inspected, not proven — and four releases in
  a row shipped a true-but-unpinned claim: a file-wide `count()`, a substring, a harness that was
  never run, then a precedence rule whose assertions only covered `active: null`.
- Entering a pane is not leaving it: every full-bleed view needs a drawn exit and a key for it.
- Leaving the cockpit files the flight (`POST /flight`: trail in order, plus keeps and
  trashes) as residue — never as a state — and posts one line into the conversation
  (`left the cockpit · N concepts · a → b → c`) so the person's choices come back to the chat
  they are in, not only to the next turn's context.
- A new backend route is not live until the gateway restarts; say so instead of claiming the
  wire works. Diagnose a silent client→server call by driving the packaged app and reading the
  refusal (`404 {"detail":"Not Found"}` meant the route, not the client).
- Never swallow an error you would have to explain later: `.catch(() => {})` made a refused
  flight indistinguishable from a filed one. Keep the outcome where a person can read it.
- A module-level helper cannot use a component-local `window`; resolve it where it is used, or
  the fallback path throws ReferenceError into the same silent catch.
- A walk is ambient: keep working. The walked path is scenery, not a hint, and
  no walk material is injected into the working turn.
- When the state ends, say what it left behind. Residue is the only output.
- Tools stay open unless the entry asks for `block: true`; when it does, the state's own
  recommended set applies and `allow` narrows it. `/return` is always available and exempt.

## Experimental development (not runtime-active)

An experimental exploration layer lives in the library. Its modules
(`core/collider.py`, `core/collision.py`, `core/llm.py`,
`core/orchestrator.py`, `core/selection.py`, `core/feedback.py`,
`data/collider/`) exist. Three auxiliary task routes (`antemuse_generate`,
`antemuse_select`, `antemuse_refresh`) are declared — a routing entry, not a call —
and the four session-boundary hooks are registered; on a session boundary they
release any material bound to that session. `/spark` is the first thing that binds material;
it is also the only runtime path that can reach a model, and only when the flag
is on.

- `/spark <goal>` exists and runs one bounded pass. With
  `plugins.entries.antemuse.settings.experimental.enabled: true` and a host that
  exposes `ctx.llm`, it takes the branch path (one auxiliary call per budgeted
  source, then deterministic selection). With the flag off it stays
  deterministic and calls nothing. `/keep love|like|trash <#n|candidate-id>`
  records a verdict by its account handle; `/again` re-runs the last goal with
  the sources that verdict points at (`deepen` from loved, `refresh` from liked).
- The two audiences are separate by contract: the model receives the candidates,
  the person receives a line of counts (`spark · 2 candidate(s) · 1 kept · kept #1`).
  Never read candidate text into a human-facing line.
- Do not claim the library improves responses, diversity, or creativity. No
  protected comparative evaluation has been run, and runtime selection scores
  are not improvement evidence.
- The base state lifecycle stays deterministic: entry, exit, expiry, tool
  restoration, and rendering never require inference, and `/return` remains
  available under every state.
- Any promotion of a method is gated on protected comparative evaluation under
  the governing spec.

## Verifying a release

The thing that ships is the tarball, not the checkout:

```bash
T=$(mktemp -d); tar -C $T -xzf ~/.cache/antemuse/dist/antemuse-<v>.tar.gz
cd $T/antemuse-<v>
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q
npm ci --silent --prefix tools/desktop_harness && node tools/desktop_harness/mount.mjs
```

Two harnesses exist and they are different: `tools/desktop_harness/mount.mjs` (node/jsdom,
mounts the whole pane) and `tools/cockpit_harness.py` (Playwright, drives `createCockpit`).
Citing one while shipping the other is how a broken harness survived four releases — the jsdom
one asserted the registration by the *shape* of the area list, so it died on a clean mount of
every release from 0.11.0 to 0.11.8.

## Verifying in this environment

The shell exports a `PYTHONPATH` pointing at a Python 3.14 site-packages, which
breaks both `pytest` collection and `PIL` inside any other interpreter. Clear it
for every test run:

```bash
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q

# `--with nltk` alone is not enough: the dashboard tests import fastapi/httpx
# and the catalog test imports pyyaml, so collection aborts with three errors on
# a clean machine. requirements-test.txt is the list that actually runs.

# NLTK_DATA is only needed if your corpora live outside the default lookup:
#   NLTK_DATA=~/nltk_data ...
```

The plugin declares `nltk`, but Hermes does not install plugin dependencies into
its own interpreter: if a state enters and every walk records
`failed · No module named 'nltk'`, install it where Hermes runs:

```bash
uv pip install --python "$(hermes --version >/dev/null; python3 -c 'import sys;print(sys.executable)')" \
  "nltk>=3.8,<4"
```

And always point `ANTEMUSE_STATES_HOME` somewhere temporary during verification —
the plugin shares one state file with the live agent, so a test that enters a
state will lock the agent's own tools until it exits.
