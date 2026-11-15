# Machine-led and person-led idea work

Change id: `machine-and-person`
Repo: `antemuse-plugin`
Status: **proposal — gate 1, nothing built**

## Goal

Two lanes of idea work, both able to put something into the agent's context, and they are
not the same lane wearing different names:

- **Machine-led.** The agent goes somewhere with a dose, comes back with material, and the
  work continues. Nobody is watching while it happens.
- **Person-led.** The person flies the concept map and picks what they want. The agent did
  not choose any of it.

The point of naming them is that the rules differ — who starts, who may end, what enters the
conversation, and what the agent is allowed to say about it.

## What exists today

| State | Lane | Starts | Ends | Enters context |
| --- | --- | --- | --- | --- |
| walk | machine | command, tool, or `suggest_autofollow` | dose (6 hops) or `/return` | **nothing** while running — a measured decision; the report after |
| daydream | machine | same | dose (2 pairs) | two memory excerpts + the report |
| dream | machine | same | dose (2 recombinations) | frames + the report |
| doomscroll | machine | same | dose (3 items) | feed items + the report |
| unstuck | machine | same | dose (1 direction) | the direction + the report |
| explore | person | command only | **only** `/return` | picks as residue; nothing while running |

So the lanes exist. What is missing is that neither lane can hand off to the other, and the
person-led lane cannot be aimed.

## The four mechanics this change adds

### 1. A person can aim an explore

`/explore <concept>` starts the cockpit at that concept instead of at home, and the pick list
begins from the concepts one hop from it. Without this, a person-led lane is a random walk
with a joystick: the only way to explore an idea is to fly until you bump into it.

### 2. The person's picks are context, not just an account

Today `/return` names the picks back and the model is told to work one of them. That is a
suggestion in prose. The picks should also be injectable as material: on the next turn the
block carries the picked concepts, their ledger weights, and one line saying these are the
person's own choices. Anything the person chose outranks anything a state served.

### 3. Machine-led work can be seeded by the person's last picks

`/dream` and `/daydream` currently read their own sources. A person who has just picked six
concepts around a problem should be able to say "dream on these" and have the state's seed be
the picks rather than the last N memories. This is the handoff the lanes are missing in the
person → machine direction.

### 4. A machine-led state can open the cockpit at what it found

The reverse handoff: after a walk or a dream ends, the report's concepts are a natural place
for the person to take over. Offered, never taken over: the pane's "open the cockpit" button
while a machine-led state is running would start the cockpit at the last hop.

## Unsupervised is a budget question, not a scheduling feature

Today nothing starts a machine-led state by itself except `suggest_autofollow`, which is off
by default and only fires on a recommendation inside a live turn. That is the right default.

If this change adds a schedule, it needs a stated budget: at most one unsupervised state
active at a time, a minimum gap between them, no state that blocks tools, and the person can
always end one with `/return`. Without a budget, "unsupervised idea work" is a process that
spends someone else's credits in the background.

**Decision needed:** is unsupervised means (a) what exists now — a state runs when an
unattended session turns over, (b) an opt-in schedule with a daily cap, or (c) nothing
scheduled, ever, and the machine lane only runs when a person or an agent asks?

## Invariants that do not change

- The person-led lane cannot be started by the machine. No recommendation, schedule, or
  hook enters `explore`; only a person types it.
- The machine-led lane cannot end itself in a way the person is not told about: every ending
  posts its account.
- A state still has no model call on its entry, exit, expiry, or rendering path.
- Whatever a lane injects, the person's own material outranks it.

## Non-goals

- No new pane. The cockpit and the map stay the surfaces.
- No quality claim: this is a plumbing change about where material comes from and who chose
  it. Nothing here says the ideas get better.
- No autonomous spend. A schedule, if one exists, is opt-in and capped.

## Acceptance (draft — needs the decision above before it can be fixed)

1. `/explore salt` opens the cockpit at `salt`; `/explore` alone still starts at home.
2. After `/return`, the next turn's block names the picks and says they were chosen by the
   person, with their ledger weights.
3. `/dream seeded` (or equivalent) uses the last explore's picks as its seed and says so in
   its account.
4. A machine-led state that ends offers the cockpit at its last concept; nothing navigates
   without a click.
5. Whatever the scheduling decision is, there is a test that the person-led lane cannot be
   auto-started and one that an unsupervised state cannot block tools.

## Open questions for gate 1

1. **Scheduling** — (a) as-is, (b) opt-in schedule with a daily cap, or (c) never scheduled.
2. **Pick injection** — names only, names plus weights, or names plus the journal excerpts
   that were live while they were picked? The third is the most useful and the most likely to
   leak material the person did not read.
3. **Seeding a dream from picks** — does the pick set become the seed outright, or does the
   state keep its own source and only get the picks as a bias?
4. **Where the boundary is** — should a person-led state be able to run while a machine-led
   state is already active? Today a state owns the profile, so the answer is no; allowing it
   means two directives in one turn and a rule for which wins.
