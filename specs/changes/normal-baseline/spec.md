# Normal — measuring the state nobody has to ask for

Status: **implemented (partial)** 2026-11-08. Owner: Ryan Cook. Scope: measurement of the
ordinary, no-state condition. No new command, no new state, no model call.

## The problem

Every threshold in the recommender was a constant somebody picked: 90 minutes is a long
stretch, 3 failures in a row is a loop, 60 turns is saturation. They might be roughly
right for one person doing one kind of work; they are not measurements. And they cannot
be checked, because the plugin never recorded what *normal* looks like — it only counts
work while a state is running or since the last one, never the ordinary session as a
distribution.

A state only means something against a baseline. "You are looping" is a claim about
normal, so normal has to be measured with the same instrument.

## What is measured

Two ordinary observations, recorded only when **no state is active** (a state's own
turns would contaminate the baseline it is being compared to):

1. **Turn shape** — tool calls and failures per turn.
2. **Stretch** — minutes from one state's end to the next state's start: how long this
   person actually works before stepping away, which is the number the "long stretch"
   threshold should have been.

Stored in `normal.json` in the plugin data dir: the last 200 turns, the last 50
stretches, and a timestamp. Atomic write, bounded, no content — counts only, never text.

## What is reported

```
normal.stats() →
  measured: bool        # false below 20 turns
  turns: int
  tools_per_turn: float # median
  fail_rate: float      # failures / turns
  stretches: int
  stretch_p75: int      # minutes, median of the top quartile
```

Below 20 turns or 5 stretches the answer is `measured: false`. Nothing is claimed from
four data points.

## How it is used

**One calibration, not a rewrite.** `long stretch` stops using the constant 90 and uses
the measured 75th percentile of this person's stretches, floored at 60 minutes and capped
at 180 — a floor so a burst of short sessions cannot make the plugin nag, and a cap so one
12-hour day cannot silence it for a week. With no measurement, it falls back to 90 and the
line says so.

The line carries the comparison rather than an adjective:

```
this looks like a daydream · 122m since the last state, 2.1× your usual 58m · /daydream
```

Loop, wall and saturation keep their fixed thresholds for now. Calibrating them the same
way is the honest next step, but it needs failure-rate distributions the sample here
cannot support yet, and a threshold derived from 20 turns would be a guess wearing a
measurement's clothes.

## Acceptance criteria

1. Ordinary turns are recorded only while no state is active; a state's turns do not
   enter the baseline.
2. `stats()` returns `measured: false` below 20 turns, and no calibrated threshold is used
   while it is false.
3. With ≥ 20 turns and ≥ 5 stretches, the long-stretch threshold follows the measured p75,
   clamped to 60–180 minutes.
4. Stretches are recorded when a state is entered, not when it ends, so an abandoned state
   cannot inflate the distribution.
5. Nothing here reads message text, and nothing is written outside the plugin data dir.

## Must not change

The recommendation rules and their precedence, `/return`, `CONTROL_TOOLS`, state
durations, budgets, cadences, the wordless card, and the rule that nothing on the state
path needs a model call.
