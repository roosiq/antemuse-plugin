# What each state is for

A state is a bounded change to what the agent attends to. This file says what each one is
*for* — the goal, what success looks like when it happens, what failure looks like, the
measure that actually fits that goal, and what the state must not do.

Written because the first experiment measured all five states with one number (novelty of
concepts) and that was wrong for four of them. A state can hit 98 % on someone else's metric
and still not do its job.

The goals below are transcribed from each state's own directive in `core/states.py`; where a
goal needed judgement, the judgement is marked **open** and listed at the end.

---

## walk

**Goal.** Work continues while the frame is elsewhere. The walk is the time away from the
frame, not new material for it.

**Success.** The task still moves at its normal quality. The concepts served are far from
the project's own vocabulary — the walk is genuinely somewhere else. Nothing about the walk
appears in the agent's reply as content.

**Failure.** The agent narrates the walk, uses it as a source of ideas, or lets it become
the topic. Also failure: a walk that stays in the neighbourhood, so "away" is a fiction.

**Measure.** Frame distance, not novelty: mean WordNet path similarity **0.05 for a far
jump vs 0.34 for an adjacent hop** (`outer`/`vault` vs `wander`). Interference — whether the
frame leaks into replies — is **measured nowhere yet**.

**Non-goals.** Supplying ideas. Being entertaining text for the human. Any claim that a walk
makes the work better.

---

## daydream

**Goal.** Associative recall with restraint: two memories surface at a time, the state says
what they touch, and joins them only when the join actually holds.

**Success.** A join rests on words distinctive to those two memories, not on the project's
own boilerplate. When nothing holds, the state says `adjacent` and moves on — that is a
correct outcome, not a miss. No recommendations, no tools.

**Failure.** Forced joins (any two notes that both say "plugin"), a stream of
recommendations, or tool use inside an undemanding state.

**Measure.** Join rate **on distinctive terms** (terms that appear in at most a quarter of
the pool), plus the honesty of the adjacent branch. Before the fix: **6 %** join rate,
because each item drew one random pair from a 25-memory pool. After: **100 %** on that dense
pool with a median of 3.5 distinctive shared terms — and the question of whether 100 % means
the pool is dense or the bar is low is **open**.

**Non-goals.** Brainstorming. Producing actions the agent should take. Ranking memories.

---

## doomscroll

**Goal.** Consume unfiltered external material, without synthesizing. The randomness is the
point; the agent reads and does not tidy.

**Success.** Material is random across sources, does not repeat itself across sessions, and
is read rather than turned into output. At the end of a turn the agent can name what it
consumed.

**Failure.** The same six items every session because one feed was first to answer; filtering
for relevance; summarizing the feed back as if that were the act.

**Measure.** Distinct lines across sessions — **48 / 22 / 11 %** at dose 1/3/6 on the frozen
feed, **90 / 83 / 83 %** after drawing from a wider pool and refusing repeats.

**Non-goals.** Curation. Relevance. Coverage of "what matters today".

---

## dream

**Goal.** Recombine stored concepts into things that do not exist — objects, stories,
mechanisms — and keep the ones that land.

**Success.** The recombination crosses two worlds that share no vocabulary, uses real words
from those worlds, and the agent keeps at least one and says what it is for. Pairs differ
from run to run.

**Failure.** A template sentence inside one frame with its roles shuffled — structurally
distinct, lexically boilerplate. Role-name soup. A long dream where nothing is kept.

**Measure.** Frame-pair distance and pair distinctness, because novelty of words is not the
goal here — the invention *is* the pair. Measured: **100 % distinct pairs, mean frame
overlap 0.0000, 100 % disjoint pairs** over 40 recombinations. Keep rate is **unmeasured**.

**Non-goals.** Usefulness on demand. Ranking candidates. Tool use. Any promise that a
recombination is good rather than new.

---

## unstuck

**Goal.** On a greenfield, name ONE direction: what the product is, and which spec file that
sentence becomes. The promise, not the roadmap.

**Success.** Exactly one direction, in the present tense, bound to the evidence that
produced it and carrying a first move that can be started in one turn. The human can accept
it or reject it; three more would be unusable.

**Failure.** A menu, a ranked list, a summary of the repo handed back, or a spec written from
inside this state. Also failure: a direction with no evidence behind it.

**Measure.** Count (must be 1 at dose 1), groundedness (every direction names its evidence
and its first move), and dose responsiveness — 0 directions at 0, 1 at 1, 2 at 2. Before the
rewrite the state served five identical lines at every dose and **1 %** distinct lines across
trials; now **29 %**.

**Non-goals.** Writing the spec. Estimating effort. Offering options.

---

## idle and work — the baseline, not states

They are not in `STATES` and never enter. `work` is the ordinary condition and `idle` is
nothing happening; both exist so a comparison has a floor. A state that cannot be told apart
from `work` on its own measure has not done anything.

---

## Open questions

1. **walk** — may the agent ever mention the walk? The directive says no; the return report
   is written by the runtime, not the agent, which is the only reason the two do not
   contradict each other.
2. **daydream** — is a 100 % join rate the goal, or evidence the bar is too low for a dense
   pool? A pool-aware threshold (3 distinctive terms when the pool is large) would keep the
   restraint honest.
3. **dream** — is nonsense acceptable as invention, or must every recombination be usable —
   a name, a purpose, a first test? Today the only gate is "keep it and say what it is for".
4. **doomscroll** — should source rotation happen per session or per item?
