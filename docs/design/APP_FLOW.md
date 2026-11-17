# App flow

Every route, surface and state, and which of them a person can reach.

The drawn version of this page is `antemuse-flow.png`, generated from `app-flow.html`. It is drawn
from the code, so where this page and the drawing disagree, the drawing is right and this page is
stale.

## Surfaces

| Surface | Route | Placement | What it is |
| --- | --- | --- | --- |
| Antemuse pane | `/{ID}` | `right`, 320–560px | the map: every concept the ledger knows, the walk's hops, the journal's labels |
| Cockpit pane | `/{ID}/cockpit` | `main` | the same map in first person, flown by the person |
| Settings | Settings ▸ Plugins ▸ Antemuse | host form | seven settings from `config_schema` |
| Chat | any conversation | — | the state's account on entry, a state marker on replies, `/return` |

All three routes exist in the desktop app. Chat never carries a picture.

## Reaching a surface

- **Nav row** — `Antemuse` and `Cockpit` in the plugin's nav.
- **Command palette** — `cockpit`, `cockpitOpen` copy keys; ⌘K then the name.
- **Status chip** — always present; opens settings, or the cockpit while `explore` is active.
- **Pane button** — `open the cockpit`, rendered only while `explore` is active.
- **Nothing navigates by itself.** No state, recommendation or hook moves the person.

## The cockpit, and the only number worth counting

The cockpit flies the same `GET /graph` payload the pane draws. The concept under the
reticle is named — on hover, on click, and on the impact of a bullet — so the `PICK`
count never moves without saying what was picked.

A named concept can be judged: `K` keeps it, `T` drops it, and both are posted through
the host's `ctx.rest` door (the pane runs on a `file://` origin, where a relative
`fetch` cannot reach the gateway). A verdict is a ledger row whose `move` is `keep` or
`trash`, so the pane's tally and `tools/hit_rate.py` count the same rows:

```text
kept 1 · dropped 1
hit rate: 1 kept, 1 trashed · 50.0%
```

That rate — how often the material was worth keeping — is the product metric. Arrival
counts measure the machine; verdicts measure the idea.


## The state machine

```
                            /walk /daydream /doomscroll /dream /unstuck   /explore
                              │                          │
                              ▼                          ▼
                     machine-led state          person-led state
                        dose: hops               no dose, no clock,
                                                 no provider
                              │                          │
      dose served + seen · dry turn · /return      only /return
      · source failed                                    │
                              └──────► account ◄─────────┘
                                          │
                          residue (report) + next turn's opening
```

- The five agent states are machine-led: `walk` delivers six hops; `daydream` two
  memory pairs; `doomscroll` three feed items; `dream` two recombinations; and
  `unstuck` one direction.
- It ends itself four ways — complete, dry, failed, or an explicit `/return` — and reports which
  one it was.
- `explore` is person-led and ends one way, and its account names the person's own picks.
- One state owns the profile at a time.

## What each surface shows while a state runs

| | pane | cockpit | chat |
| --- | --- | --- | --- |
| label | state label + counts | HUD + `PICK`/`LIT` | state label + counts |
| material | hops, journal labels, firing set | concepts as points, picks as gold | none |
| ending | corner note after the poll | pick panel | account line + opening block |

## Failure paths

| Failure | What the person sees |
| --- | --- |
| `/graph` 401/403 | `sign-in required` (pane) — cockpit: raw error, to be fixed |
| `/graph` 404 | `the plugin backend is not mounted` |
| `/graph` 5xx | `the backend did not answer` |
| no response at all | `reconnecting` for a run of failures, then `backend unavailable` |
| missing corpora | `wordnet unavailable`, `framenet unavailable` in the account |
| feed down | `feed unavailable · <source>` in the account |
| a state with no dose | `open · you end it`, never `0 left` |

## Where the two lanes meet (proposed, not built)

See `specs/changes/machine-and-person/proposal.md`: a person can aim an explore, picks can be
injected as material, a machine-led state can be seeded from picks, and a machine-led state
can offer the cockpit at what it found. None of it is built.
