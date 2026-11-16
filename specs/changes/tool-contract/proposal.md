# The tool's contract

## Why

Driving the packaged app and calling the `state` tool by hand turned up three cases where the
tool said something untrue to its caller — and one where it did something the caller never
asked for.

- **A walk name that does not exist was accepted.** `state(action='enter', walk='bogus')`
  answered `WALKING · 6 hops …`, recorded `walk: "bogus"` in the active state, and then ran a
  real walk anyway. The cause was one line in `core/walks.py`: `get()` ended with
  `return GraphWalk({"name": "wander", **BUILTIN["wander"]})`, so any unknown name silently
  became `wander`. The hops observed were hyponym steps — the every-edge walk.
- **The rejection message recommended actions that do not exist.** `state(action='card')`
  answered `no such action: 'card'. try: …, watch, card, image.` — `card` and `image` were in
  that sentence and in neither the schema nor the handler, so following the advice looped.
- **`/explore` was enterable by the agent** while its own parameter description says
  "person-driven and is entered with its command".
- **`state(action='list')` omitted `/explore`**, so the palette said two verbs where the
  README, the SKILL and the command surface all say three.

## What changed

| Was | Is |
|---|---|
| `walks.get()` replaced an unknown name with `wander` | `walks.get()` raises `no such walk: 'x' · try: …`; only an empty name means the default |
| `engine.enter()` stored whatever walk string it was given | it refuses a name that is not in `walks.names()`, before anything is written |
| the action list existed twice — once in the schema, once typed into the error | one `ACTIONS` tuple; the schema enum and the rejection message are both built from it |
| the tool entered `explore` on the agent's word | the tool answers `explore is person-driven · the person types /explore`; `engine.enter("explore")` still serves the command |
| the palette listed `/walk` and `/return` | it lists `/walk`, `/explore` under a PERSON-DRIVEN heading, and `/return` |

## Non-goals

- The HUD's `LIT`, `EDGE` and `PICK` cells, and the 10px map labels. Their meaning is now
  written down in the manifest; how they look is a separate design pass and was not approved.
- Anything about the cockpit's rendering, flight model or verdict path.
- Entering `/explore` from the pane or the command. Only the tool lost that ability.

## Must not change

- `state(action='enter', name='walk')` with no walk still enters `outer`.
- A walk name is still lowercase letters, digits, `-` and `_`, and still cannot reach outside
  the walks directory.
- `/explore` still has no dose, no provider and no end but `/return`.
