# Antemuse Room

Not a game. A room that cycles through phases of **concept discovery** and
**movement**, and shows you what it accumulated.

One tick advances one phase:

- **Move phases** — `discover`, `flip`, `shift`, `connect` — hand out a seed and
  one constraint, and take a spark: `title :: because … :: do this first`.
- **State phases** — `walk`, `daydream`, `dream`, `dissociate`, `doomscroll` —
  change the seed, the distance expectation, or the debt. They resolve without a
  model call, so automation never stalls.
- **Converge** keeps the best spark of the arc and opens the next arc from the
  winner's next action.

Because state phases are self-resolving, the same machine runs from a slash
command, an agent tool call, or a cron tick.

## Two projections, one state

Every room renders twice, from the same `Frame`:

| Projection | For | What it is |
|---|---|---|
| poster | humans, vision models | 1200×1500 PNG: height = score, ring count = distance, every number drawn as text |
| transcript | language models | one line per spark, totals, shape, keepers |

Neither is derived from the other; both are derived from `Frame`, so the numbers
cannot disagree. A test asserts it.

## Surfaces

```
/room step                  advance one phase, get the brief
/room commit T :: because … :: do this first
/room poster                transcript + MEDIA: png path
/room phases                the palette and rotation
/room walk                  jump straight into a phase
/room reset [seed]          new room
```

Agents use the `room` tool with `action=step|commit|status|poster|phases|phase|reset`.

## Install

```bash
ln -s ~/antemuse-room ~/.hermes/plugins/antemuse-room
hermes plugins enable antemuse-room
```

Tools are assembled per session. A running gateway reloads commands on enable
but keeps modules it already imported — iterate with `disable && enable`.

## Layout

```
plugin.yaml            manifest, pillow dependency
__init__.py            room tool, /room command, bundled skill
kitchen/phases.py      phase definitions, rotation, palette
kitchen/room.py        the machine: step, commit, converge, state effects
kitchen/visual.py      two projections of one Frame
kitchen/judge.py       deterministic scoring of a spark
kitchen/deck.py        seed deck
kitchen/store.py       profile data dir
tests/                 21 tests: rotation, state effects, converge, projections
```

## Verify

```bash
hermes plugins doctor ~/antemuse-room
PYTHONPATH= ANTEMUSE_ROOM_HOME=$(mktemp -d) uvx --with pillow pytest tests/ -q
/room step
```

## Notes

- PIL renders the poster; `pillow` is declared in the manifest and the Hermes
  runtime ships a working copy.
- A `PYTHONPATH` inherited from the Hermes install venv breaks a 3.12 pytest run
  (`PIL._imaging` mismatch); clear it when testing.
- Data lives in the profile's plugin data dir, overridable with
  `ANTEMUSE_ROOM_HOME`.
- The old `/cook` command and the five-round game are gone; the judge and the
  seed deck survive underneath.
