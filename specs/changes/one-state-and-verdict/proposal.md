SUPERSEDED — 2026-11-16

The 2026-11-09 owner note declined the one-state cut. `restore-four-states` restores
daydream, doomscroll, dream, and unstuck beside walk; it is the active record for this
surface. Historical proposal preserved below unchanged.

# One state, and a way to judge it

## Why

The audit's verdict was that the plugin shipped six flavours of the same idea, and
that none of them could be told apart by their material. The recommendation was to
cut to one state and to instrument whether the material was any good.

This change does both:

- `walk` is the only agent state. `/explore` stays, because it is not a state the
  agent enters — it is the map the person drives, with no dose and no provider.
- A concept the map puts in front of a person can now be kept or dropped, and the
  ledger counts those judgements.

A product with one state can be judged. A product with six and no verdicts can only
be described.

## What changed

| ask | where |
| --- | --- |
| one agent state | `core/states.py` (`STATES = {"walk": …}`), `core/sources.py` (walk provider only) |
| remove the four states from every surface | `__init__.py`, README, TESTING, `specs/product/`, `tools/examples.py` |
| name what the map picked | `desktop/plugin.js` (`nameNode`), HUD readout |
| keep / trash with a keyboard path | `desktop/plugin.js`, `POST /verdict`, `GET /verdicts` |
| a hit rate from the ledger | `core/history.py:verdicts()`, `tools/hit_rate.py` |

## Non-goals

- No new state, no second graph, no scoring model.
- No change to `/explore` behaviour.
- No version bump and no release: this is uncommitted work on `main`.

## Acceptance

See `acceptance.md`. The suite is the gate; the hit-rate tool is run against a
fabricated ledger so its output is a fact rather than a claim.
