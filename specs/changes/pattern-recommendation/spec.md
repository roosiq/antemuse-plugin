# Pattern recommendation — name the state that fits the shape of the work

Status: **implemented (PARTIAL)** 2026-11-08. Owner: Ryan Cook. Scope: the recommendation line that
already rides in the injected block. No new command, no new state, no model call.

## Goal

When the shape of the work has a name, say its name: *"this looks like a walk — you are
looping on the same failure"*. This change says **which state to recommend for which
pattern, on what evidence, and in what words** — so the recommendation is a judgement
with a stated basis, not a nudge.

### Revision 2026-11-08: one owner

There were two recommenders. `core/mood.py` summed minutes / 90 + turns / 30 + fails / 6
into a "strain" score and named a state from that arithmetic — `break due` below 2.0,
`break overdue` above it — while `core/recommend.py` named a state from a measured
pattern. Whichever had something to say spoke, so the arithmetic often did: a healthy
session of 122 minutes and 27 turns was told *"a daydream fits"* by a timer, with no
evidence beyond the clock.

**`core/mood.py` now measures and never recommends.** It reports minutes since the last
state, turns, failures, the run of consecutive failures and any reported feeling. It has
no `due`, no `strain`, no `suggest`, no `offer`, no `menu`. Naming a state is
`core/recommend.py` alone, and every line it emits must name the counter that justified
it. When nothing is measured, nothing is said.

## The rule that must not bend

**Recommend, never enter.** Entering a state is the person's decision (`/walk`,
`/daydream`, `/doomscroll`, `/dream`) or the agent's explicit tool call. A recommendation
that takes the action is a hijack, and this plugin has already been on the wrong side of
that once: a state that removes the ability to leave itself.

**Measured, never inferred.** Every trigger below is a counter the plugin already keeps:
turns, journal events, tool successes and failures, minutes inside a state, source
failures. Nothing here reads the person's feelings. `/mood` stays *reported* — if the
person says they are tired, that is data; if the plugin decides they are tired, that is
invention.

## Patterns

| Pattern | Evidence (all already recorded) | Recommend | Why that state |
|---|---|---|---|
| **Loop** | the same tool fails ≥ 3 times in a row, or the same error text recurs ≥ 2 turns | `walk` | the thread matters and the frame does not; walking keeps the work and changes the view |
| **Grind** | ≥ 20 turns with no state and ≥ 1 failed tool call in the last 3 turns | `daydream` | cheapest interruption: three minutes, memories, tools untouched |
| **Churn** | ≥ 4 topic shifts across the last 8 turns with no completed edit or test run | `walk` | motion without arrival usually means the frame is wrong, not the effort |
| **Saturation** | ≥ 60 turns in one thread, or ≥ 3 decisions left open in the journal | `dream` | slow and unstructured; let the open decisions recombine |
| **Data wall** | ≥ 2 source failures (fetch, 401, timeout) in the last 4 turns | `doomscroll` | a feed is raw noise to break attention off a blocked dependency |
| **Rut** | two entries of the same state inside 10 minutes, or the same state re-entered twice in a row | a *different* state, chosen by the rules above | repeating the same move on the same pattern is the definition of stuck |
| **Long stretch** | ≥ 90 minutes since the last state ended, with ≥ 10 turns | `daydream` | the cheapest state, and the clock is a real measurement: an unbroken stretch is the observation, not a score derived from it |
| **Reported** | a mood report inside 4 hours (`state(action="mood", feeling=…)`) | the state mapped to that feeling | the person or agent *said* it. Reported is data; inferred is not |
| **Return hangover** | the state ended < 2 turns ago and the first step repeats the step it ended on | `walk` | the account said what is next; if that step is being retried, the frame is still wrong |

Five states are defined, so the recommendation must always name one of them; "take a
break" without a state is not an output.

**Precedence**, fixed so two patterns cannot argue: `new project` → `reported` → `loop` →
`data wall` → `saturation` → `long stretch` → `grind`. A report outranks the counters
because the person knows something they do not; a loop outranks a wall because a blocked
tool is more actionable than a blocked URL.

## Where it surfaces

One line, in the injected block, in the second person, with its evidence attached:

```
this looks like a walk · same tool failed 3× · /walk 5
```

- One per 45 minutes, cooling already implemented (`OFFER_AFTER_MIN`).
- Never more than one candidate state in a line: a menu is not a recommendation.
- Suppressed while a state is running, except **rut**, which is about the state itself.
- Silent when no pattern matches. Silence is the correct default; a plugin that always
  has an opinion is a nag.
- The line never enters a state, never blocks a tool, and never appears on the human card
  (BR-5): it is text for the model and the person's reply, not the picture.

## What this is not

- Not mood detection. No sentiment analysis, no classifier, no model call.
- Not a quality claim. If someone follows every recommendation, this spec predicts
  nothing about output quality; that would need the evaluation in Path A.
- Not autopilot. There is no "auto-enter after N patterns".

## Acceptance criteria

1. Each pattern above fires on its stated evidence, with a deterministic fixture for each
   (failing tool, turn counters, source failures, re-entry timestamps).
2. No pattern fires without its evidence; the default is silence.
3. A fired recommendation names exactly one state and one piece of evidence.
4. Nothing fires inside a running state except `rut`.
5. 45-minute cooling holds across sessions for the same profile.
6. The line never appears on the human card and adds no tool block.

## Must not change

State definitions, durations, turn budgets, cadences, tool policy, `OFFER_AFTER_MIN`,
`CONTROL_TOOLS`, the injection format, or the rule that rendering never needs a model
call.

## What is built, and what is not

| Pattern | State | Evidence it reads |
|---|---|---|
| loop | **built** | `work.streak` — consecutive tool failures, reset by any success |
| data wall | **built** | `work.source_fail_turns` — the turn number of each provider failure |
| saturation | **built** | `work.turns ≥ 60`, or ≥ 3 open decisions when a caller supplies them |
| grind | **built** | `work.turns ≥ 20` plus a failure inside the last 3 turns |
| rut | **built** | `entries` — which state was entered, and when; fires inside a state too |
| churn | **NOT BUILT** | needs a topic-shift signal the plugin does not keep. Inventing one from word overlap would be a guess dressed as a measurement, so it does not fire. |
| return hangover | **NOT BUILT** | needs "the first step repeats the step it ended on", which requires comparing intent across a state boundary — a model judgement, which this design forbids. |

`core/recommend.py`; 13 tests in `tests/test_recommend.py`, including one that drives the
real engine: three failed tools, no command, and the line appears in the injected block —
then stays quiet for the cooling window.
