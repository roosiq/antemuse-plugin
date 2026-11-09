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

**Where the code stands.** Distance works: mean WordNet path similarity **0.05** for a far
jump vs **0.34** for an adjacent hop. **Connection is broken**: the directive still says
"does not supply ideas… it is the time away from the frame", and the delivered lines name the
concept without the path that anchors it to the current task. The stated goal and the built
state currently contradict each other.

**Must change.** Re-anchor the walk to the current task: start from the task's own concepts
and jump out, then report the hop count and the chain back. Rewrite the directive.

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

**Where the code stands.** It joins memories and stops there. Join rate went 6 % → 100 % on a
dense pool, which is a recall metric for a state whose job is ideation. **Nothing in the
built state ideates.**

**Must change.** Add the synthesis step: memory pair → what they suggest → one possibility,
phrased as something the agent could try or consider. Keep the distinctive-term rule for the
join; stop treating "adjacent" as the end of the item.

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

**Where the code stands.** Randomised across 4 Bluesky feeds, 5 Mastodon instances and 10
RSS feeds with a seen-set: distinct lines **48/22/11 % → 90/83/83 %** at dose 1/3/6. But the
feeds are general-purpose, so the state delivers news and commentary as readily as comedy —
right mechanism, wrong pool.

**Must change.** Replace the feed list with comedy/shitpost sources and add a cheap "is this
work?" exclusion, so a business article cannot arrive as distraction.

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

**Where the code stands.** It just became a cross-frame *inventor* (100 % distinct frame
pairs, 0.0000 overlap) — the previous goal, now superseded. And it has no input covering "the
day's happenings": the plugin sees only this conversation's recall ring (24 turns) and its own
journal (60 entries). Cross-project evidence is not reachable from inside the plugin today.

**Must change.** A consolidation interface (connections between tasks, both sides named) and
an input that spans projects. The invention code is not wasted — it becomes the fallback when
the day's material is thin, but it is no longer the act.

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

**Where the code stands.** It names one direction with evidence and a first move and is
dose-responsive (0/1/2) — but the evidence is thin repo facts ("no README / 3 entries") and
the concept graph is never consulted for the recommendation; the graph only supplies walk
material.

**Must change.** Wire the concept graph into the recommendation, and take "what we have done"
from history rather than from the current repo's file list.

**Measure.** One recommendation, with a history citation and a graph path; the count must
be 1.

---

## idle and work — the floor, not states

Neither is in `STATES` and neither is enterable. `work` is the ordinary condition, `idle` is
nothing happening. They exist so a state can be compared against no state at all: a state
that is indistinguishable from `work` on its own measure has done nothing.

---

## Where the code stands, in one table

| state | Ryan's goal | built today | delta |
|---|---|---|---|
| walk | distant **and connected** concepts for the current task | distant, unanchored; directive says "no ideas" | re-anchor + rewrite directive |
| daydream | synthesize and introduce new possibilities | recalls and joins memories, stops | add the synthesis step |
| doomscroll | social-media stupidity and comedy | randomised general feeds | comedy-only pool + work exclusion |
| dream | process the day, connect tasks across projects | invents cross-frame objects | new interface + a cross-project input |
| unstuck | recommend one new thing from history + concept graph | one direction from thin repo facts | graph + history input |

The pattern in the deltas is the one that produced the bad experiment: the states were built
as *material generators* and are defined as *cognitive moves*. Material is necessary and not
sufficient — three of the five stop before the move.
