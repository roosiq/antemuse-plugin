# What each state is for

A state is a bounded change to what the agent attends to. These goals are **Ryan's own
definitions** (2026-11-08) and they are authoritative: where the code disagrees with this
file, the code is wrong.

Each state below states the goal, what it implies for the material and the interface, where
the code stands today, and the measure that fits *that* goal. The measures are not shared
between states: the first experiment measured all five with novelty of concepts and that was
wrong for four of them.

---

## walk

> "Find distant but still connected concepts that may improve an LLM's output on their
> current task."

**Implies.** Two requirements at once, and they pull against each other: the concepts must
be **distant** (not the task's own vocabulary) and **still connected** (reached by a path
from the task, so the walk is relevant rather than random). It is not a holiday from the
work — it is a stride out and back that brings something the work did not have.

**Interface.** A concept arrives with the link that makes it connected: "this is six hops
from the thing you are working on, via …". Without the link, distant is just random, and the
agent cannot judge whether it touches the task.

**Where the code stands (built 2026-11-08).** Every step starts from a concept seeded by the
current project or conversation, and every line ends with the return path: `↩ 6 hops from
agent: agent → … → <concept>`, or `↩ jumped from <anchor>: …` when it left the path entirely.
The directive now says the concepts are distant *and* on a path from the task, and that using
one that bears on the work is the point. Mean path similarity stays 0.05 for a far jump vs
0.34 for an adjacent hop — distance was never the broken half.

**Measure.** Distance **and** connection: mean hop distance from the current task's concepts
(far), plus a resolvable chain back to it. Then, separately, whether the material was used —
that is the "may improve output" clause, and it is only answerable with real shipping work,
not in a scratch repo.

---

## daydream

> "Same as when a person daydreams — process thoughts, synthesize, introduce new thoughts,
> ideate and introduce new possibilities."

**Implies.** Daydream is **generative**, not a memory viewer. Recalling two memories is the
input; the act is to synthesize from them and put forward possibilities that were in neither.
The output is a new thought, not a report that two notes share a word.

**Interface.** Each item: what came back, what it suggests, and one possibility that follows
from the two. A pair that does not join can still produce a possibility — the join was the
entry, never the point.

**Where the code stands (built 2026-11-08).** Every item now ends with a possibility —
`possibility · if <shared> behaves the same way in both, … could be tried against …` — built
from the pair's own distinctive terms and phrased as a hypothesis, never as an instruction.
The join still has to hold on distinctive terms to be called `JOINED`; when it does not, the
item is `adjacent` and still yields a possibility.

**Measure.** Possibilities per dose (each item yields one), and whether they are new relative
to both memories — not new relative to the corpus, which was the old, wrong number.

---

## doomscroll

> "Complete distraction from the current work using social media stupidity and comedy."

**Implies.** The target is specifically **stupid and funny** — shitposts, jokes, absurd
threads — and specifically **not** work. A feed of industry news is the opposite of this
state, and so is anything the agent might mistake for research.

**Interface.** Sources are comedy and shitpost lanes (joke and meme accounts, absurdity
feeds), and material that reads as professional content is refused as distraction.

**Where the code stands (built 2026-11-08).** The pool is seven satire/comedy lanes verified
to serve text (The Onion, Babylon Bee, Reductress, Point & Clickbait, Daily Mash, xkcd, SMBC);
the general timelines and HN are gone, because they delivered the work back. A deterministic
`is_work()` exclusion drops professional items and says so (`[3 skipped as work]`), and
image-only posts are not items. Measured on the comedy pool: novel 64–70 %, fresh 100 %,
distinct lines **80 / 72 / 70 %** at dose 1/3/6.

**Measure.** Distinct lines across sessions (already measured), plus the share of items that
are comedic rather than professional — a number that has to be looked at, not inferred.

---

## dream

> "Process the day's happenings, find connections between tasks (cross project, etc)."

**Implies.** Dream is **consolidation over what actually happened**, not invention. The
material is the day's recorded activity across projects; the act is to find the connections
between tasks that nobody wrote down — the same problem solved twice, a lane blocked in one
project that another already unblocked, two repos drifting into the same design.

**Interface.** Each connection names both sides, the shared thing, and what it means for one
of them.

**Where the code stands (built 2026-11-08).** The act is consolidation: it reads the day's
commit subjects from each configured project (local git only — no transcripts), pairs subjects
from *different* projects, and reports the shared distinctive words. On a day with no
cross-project overlap it says `no connection today · … and saying so is the finding`; on a
thin day it says the day is thin and invents instead, labelled as a fallback. Cross-frame
invention is retained only as that fallback.

WordNet bridging between subjects was tried and removed: it fired on unrelated tasks
("through: artifact") which is worse than reporting nothing.

**Measure.** Connections per dream, and how many name a task on each side with shared
evidence; the share a person judges worth acting on is the only number that matters and
cannot be computed.

**Blocker.** The cross-project input is a decision, not a build: session history and
hindsight memory both exist on this machine, but reading other projects' transcripts from a
plugin is a privacy and scope change that needs an explicit yes.

---

## unstuck

> "Recommend a new thing to do, in the context of what we have done in the past and with
> recommendations from our concept graph."

**Implies.** Not a greenfield pitch and not a menu: **one recommended next thing**, justified
by (a) what has been done before and (b) what the concept graph suggests is adjacent but
untried. A recommendation needs a reason a person can check and an action that can start now.

**Interface.** The recommendation, the history it rests on, the graph path that produced it,
and the first move. One thing. More than one is a menu, and a menu moves the decision back to
the person, which is what this state exists to avoid.

**Where the code stands (built 2026-11-08).** Three inputs feed it: history (the last commit's
own subject), the concept graph (one edge out of a word this repo already uses, to a neighbour
the repo does not), and memory. Every candidate still carries its evidence and a first move,
and dose 1 still returns exactly one.

**Measure.** One recommendation, with a history citation and a graph path; the count must
be 1.

---

## The concept ledger — how a move knows it has been here before

States were re-deriving their world every time: the journal decays, `residue` is a two-turn
note, the recall ring is this conversation, a walk's `seen` set is twelve terms. `core/history.py`
adds the missing layer — identity only (term, kind, stable key, which move served it, which
session, when), never message text, never the agent's memory.

What it answers: **where was this met before**, **which concepts keep circling across sessions**,
**which were served and never used**. Past-session concepts are read from Hermes' own `state.db`,
read-only and incrementally, from user and assistant text only — no tool output, no reasoning.
The store is derived and fail-open: delete it and every state still runs.

## idle and work — the floor, not states

Neither is in `STATES` and neither is enterable. `work` is the ordinary condition, `idle` is
nothing happening. They exist so a state can be compared against no state at all: a state
that is indistinguishable from `work` on its own measure has done nothing.

---

## Where the code stands, in one table

| state | Ryan's goal | what it does now | open |
|---|---|---|---|
| walk | distant **and connected** concepts for the current task | anchored + return path on every step | "may improve output" is still a hypothesis |
| daydream | synthesize and introduce new possibilities | every item yields a possibility | 100 % join rate on a dense pool |
| doomscroll | social-media stupidity and comedy | satire pool, work exclusion | comedic share needs a human eye |
| dream | process the day, connect tasks across projects | cross-project connections from the day's commits | terse subjects give few signals |
| unstuck | recommend one new thing from history + concept graph | history + one-edge graph path + memory | graph neighbours can be thin |

The pattern in the deltas was the one that produced the bad experiment: the states were
built as *material generators* and are defined as *cognitive moves*. Material is necessary
and not sufficient. As of `state-goals`, all five make the move; what remains open is
evidence about the effect, not the shape of the act.
