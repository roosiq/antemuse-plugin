# Antemuse Concept Kitchen

A CLI minigame about creative moves, played identically by humans and agents.

A round deals a **seed** and one **move**. You answer with a spark:

```
title :: because … :: do this first
```

A deterministic judge scores four 25-point axes — move discipline, mechanism
legibility, actionability, novelty against the whole table — so nobody wins by
verbosity, confidence, or vocabulary. Five rounds make a service, and round *n+1*
is seeded by your own round-*n* spark, so a spark that generates beats a spark
that merely sounds good.

Humans and agents write to the same leaderboard. The judge does not know who is
typing.

## Install

```bash
ln -s ~/antemuse-kitchen ~/.hermes/plugins/antemuse-kitchen
hermes plugins enable antemuse-kitchen
```

Tools are assembled per session, so start a new session (or restart the gateway)
after enabling. A running gateway reloads commands immediately, but it keeps the
module it already imported — reload with `hermes plugins disable && enable` while
developing.

## Play

Human (CLI or any Hermes chat surface):

```
/cook play
/cook submit Title: … :: Why: … :: Try next: …
/cook hint        (costs 8)
/cook pass
/cook board
/cook rules
```

Agent:

```python
cook(action="start")
cook(action="submit", text="Title :: why :: try next", player="terra", model="gpt-5.6-terra")
cook(action="hint")
cook(action="board")
cook(action="rules")
```

Both surfaces call the same functions with the same schema. `player` defaults to
the OS user on the command side.

## Scoring

| Axis | 25 points for |
| --- | --- |
| Move discipline | naming exactly one changed dimension, and for flip/shift, the default you moved away from |
| Mechanism | `because` / `which lets` / `by turning`, with a reason that says more than the title |
| Actionability | try-next opens with a verb and carries a bound (`one`, `by Friday`, `under $50`) |
| Novelty | 0.08–0.40 token Jaccard against the table; derivative sparks score zero |

Penalties: slop words −10 each (max −20) · three dimensions at once −15 ·
restating the seed −10 · over the word budget −10 · two hedges −8 · hint −8.
A far-distance spark with no mechanism loses 15%.

## The engine is optional

By default a round asks `https://concept.cooking/mcp` for reference cards — the
par you are playing against. If the engine is unreachable, the round is dealt
from the bundled deck and the brief says so, including the error. Starter
directions are never presented as engine output: that is how the live site
currently degrades (its Worker `SERVER_API_KEY` returns 401 while the gateway's
own key works), and importing that failure into the game would corrupt both the
novelty axis and the player's trust.

Turn it off with `use_engine: false` in the plugin config for a fully offline game.

## Layout

```
plugin.yaml            manifest, config schema
__init__.py            register(): cook tool, /cook command, bundled skill
kitchen/judge.py       deterministic scoring + the printed rules
kitchen/deck.py        seed deck, five-round ladder, chaining
kitchen/engine.py      optional Concept Cooking MCP deal (fails closed to the deck)
kitchen/game.py        round loop shared by tool and command
kitchen/store.py       active round (JSON) + board (SQLite via plugin_data_dir)
kitchen/render.py      ASCII briefs, score cards, leaderboard
tests/                 12 tests: judge fairness, chaining, parity, engine failure
```

## Verify

```bash
hermes plugins doctor ~/antemuse-kitchen
CONCEPT_KITCHEN_HOME=$(mktemp -d) uvx pytest tests/ -q
hermes chat -q '/cook play'
```

State lives in the profile's plugin data dir (`plugins.plugin_storage.plugin_data_dir("antemuse-kitchen")`),
overridable with `CONCEPT_KITCHEN_HOME` for tests.
