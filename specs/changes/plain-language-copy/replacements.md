# Plain language copy

## Goal

Replace model-flavoured phrasing in everything a person reads with plain internet language,
without changing what any state does. Directives are included because they set the voice the
model answers in.

## Non-goals

- No behaviour change: doses, ownership, endings, refusals and tool policy are unchanged.
- No renaming of commands or states.
- Machine-readable failure tokens (for example `no_far`) stay in the line; the sentence around
  them is plain.

## Every replacement

### State copy (`core/states.py`)

**1. `walk.waiting`**

- before: taking a walk · six hops, then back with the path
- after: walking · 6 hops, then you get the path

**2. `walk.contract`**

- before: work continues · the frame is elsewhere · different on return
- after: work keeps going · you come back at it from a different angle

**3. `walk.residue`**

- before: walked: distant concepts taken while the work carried on
- after: walked: far-apart concepts while the work kept going

**4. `walk.after`**

- before: the walk is over and the frame you were in is gone. Do not resume the approach you were taking. First: state the goal in one line. Then: name the approach you were stuck in and why it was the obvious one. Then: take a different first step from the one you would have taken, and work from there. The path you walked is scenery, not a hint — it is here so you can see the route you took.
- after: the walk is done. Do not pick up where you left off. Say the goal in one line, say what you were trying and why it was the obvious move, then start somewhere else. The path is just where you went, not a hint.

**5. `walk.directive`**

- before: You are walking while you work. Keep the task moving and answer what you were asked. The walk supplies no material: the path you walked is scenery, not a hint, and no concepts will arrive in this turn. Do not invent a hop, do not offer the walk as evidence, and do not describe it for its own sake. What the walk changes shows up later, in what you come back willing to do.
- after: You are taking a walk while you work. Keep the task moving and answer what you were asked. Nothing arrives from the walk this turn: the path is just where you went, not a hint. Do not make up a hop, do not use the walk as evidence, and do not describe it for its own sake. What it changes shows up later, in what you are willing to try.

**6. `daydream.waiting`**

- before: staring out of the window · letting two memories meet
- after: zoning out · putting two things you said side by side

**7. `daydream.contract`**

- before: two memories · what they touch · one possibility
- after: 2 things you said · what links them · one idea

**8. `daydream.residue`**

- before: daydreamed: memories met, possibilities raised
- after: daydreamed: paired up things you said

**9. `daydream.after`**

- before: the daydream is over. In one line: the two things that surfaced and what they touched — then the possibility, if it still holds. If they did not join, say what the gap was. Then get back to the work you were doing.
- after: the daydream is done. In one line: the two things that came up and what links them, then the idea if it still holds. If they do not connect, say so. Then get back to work.

**10. `daydream.directive`**

- before: You are daydreaming: associative and generative. Two of the person's own recorded turns surface; the line says what they touch and what possibility follows from both. Say the possibility as a thought worth considering, not as a task. Nothing here is an instruction and there is nothing to execute.
- after: You are daydreaming. Two things the person said earlier come up, with what links them and one idea that follows. Offer the idea as something to think about, not a task. Nothing here is an instruction and there is nothing to run.

**11. `doomscroll.waiting`**

- before: scrolling · looking for stupidity and comedy
- after: scrolling · dumb posts and jokes

**12. `doomscroll.contract`**

- before: three fixed feed lanes · distraction · nothing to take away
- after: 3 feeds · a break · nothing to do with it

**13. `doomscroll.residue`**

- before: doomscrolled: stupid feed consumed
- after: doomscrolled: read dumb posts

**14. `doomscroll.after`**

- before: the scroll is over. In one line: whether anything was worth keeping — usually nothing, and that is the point. Do not turn it into a plan or a lesson. Then get back to work.
- after: the scroll is done. In one line: was anything worth keeping? Usually not, and that is the point. Do not turn it into a plan or a lesson. Then get back to work.

**15. `dream.waiting`**

- before: asleep · letting the day's work touch
- after: dreaming · mixing up your recent commits

**16. `dream.contract`**

- before: the day in this project · connections between tasks
- after: your recent commits · what links them

**17. `dream.residue`**

- before: dreamed: the day's work connected
- after: dreamed: linked up recent work

**18. `dream.after`**

- before: the dream is over. In one line: the connection you found in this project's recent work — both sides and what they share, or the gap if they did not touch — and whether it is worth acting on now or only noting. Then get back to work.
- after: the dream is done. In one line: what linked up in your recent commits, both sides and what they share, or say they do not connect. Then say if it is worth doing now or just noting, and get back to work.

**19. `dream.directive`**

- before: You are dreaming over the day: long, slow, unconstrained. Local git commit subjects from the repository this chat is working in come back, and the connections between tasks are the thing to find — the same problem solved twice, a blocker cleared by a later change, two threads drifting into the same design. Each line names both sides and what they share, or says plainly that they share nothing. This is thinking, not a task: tools stay available, but there is nothing here that needs one.
- after: You are dreaming over your day: slow and loose. Recent commit subjects from this repo come back, and what links them is the thing to look for — the same problem solved twice, a blocker a later change cleared, two threads ending up in the same design. Each line names both sides and what they share, or says they share nothing. This is thinking, not a task: tools are still there, but nothing here needs one.

**20. `dream.dose.unit`**

- before: recombinations
- after: links

**21. `unstuck.waiting`**

- before: thinking back over what you have done
- after: looking back at what you've done

**22. `unstuck.contract`**

- before: one recommendation · from history and the concept graph
- after: 1 next move · from your commits and the map

**23. `unstuck.residue`**

- before: unstuck: one thing recommended, and why
- after: unstuck: suggested one next move

**24. `unstuck.after`**

- before: the recommendation stands. Restate it in one line with the first move, then take that move. If the history and the graph did not support a recommendation, say so plainly instead of inventing one.
- after: the suggestion stands. Say it in one line with the first move, then make that move. If your commits and the map did not support a suggestion, say so instead of making one up.

**25. `unstuck.directive`**

- before: You are unstuck. Recommend ONE new thing to do. It rests on two things you can check: one recommendation from history and one untouched edge of the concept map. Give the recommendation, the history it rests on, the graph edge, and a first move. One thing: a menu moves the decision back to the person. You do not write the spec from this state.
- after: You are unstuck. Suggest ONE new thing to do, based on two things you can check: your commit history and an unused link in the concept map. Give the suggestion, the commit it rests on, the map link, and a first move. Just one — a list hands the decision back to the person. Do not write a spec from here.

**26. `unstuck.dose.unit`**

- before: directions
- after: moves

**27. `explore.waiting`**

- before: at the controls · the map is yours
- after: you're flying · pick what you want

**28. `explore.contract`**

- before: you fly · you choose · it ends when you end it
- after: you pick · it runs until you stop it

**29. `explore.residue`**

- before: explored: concepts chosen by hand
- after: explored: the concepts you picked

**30. `explore.after`**

- before: the explore is over. What the person picked came from their own hands, not from this plugin's search: name those concepts back, say what they seem to have in common in one line, and ask whether to work one of them now. Do not praise the session, do not describe the cockpit, and do not add concepts they did not pick.
- after: exploring is done. They picked these themselves, the plugin did not search for them: name the concepts back, say in one line what they have in common, and ask if they want to work on one now. Do not praise the session, do not describe the cockpit, and do not add concepts they did not pick.

**31. `explore.directive`**

- before: The person is flying the concept map themselves. They steer, they shoot, they stop — nothing about what gets picked is yours to decide. Do not name concepts for them, do not offer a route through the map, and do not narrate the session back at them. If they ask something, answer it plainly; otherwise stay out of the way until they end the state.
- after: The person is flying the concept map themselves. They steer, they pick, they stop. What gets picked is not yours to decide. Do not name concepts for them, do not suggest a route, and do not narrate their session back at them. If they ask something, answer it plainly; otherwise stay out of the way until they stop.
### Chat lines (`core/engine.py`, `__init__.py`)

| # | before | after |
|---:|---|---|
| 32 | `cannot enter <state> · …` | `can't start <state> · …` |
| 33 | `cannot enter · <bad options>` | `can't start · <bad options>` |
| 34 | `cannot enter with method, seed, or budget · …` | `can't start with method, seed, or budget · …` |
| 35 | `cannot enter · walk names are lowercase letters, digits, '-' and '_'` | `can't start · walk names use lowercase letters, numbers, '-' and '_'` |
| 36 | `explore is person-driven · the person types /explore` | `explore is yours to drive · type /explore yourself` |
| 37 | `not in a state.` | `nothing running.` |
| 38 | `· /return ends it early` | `· /return to stop` |
| 39 | `· /return to come back` (reply footer) | `· /return to stop` |
| 40 | `no tools in this state. /return to come back.` | `no tools in this state. /return to stop.` |
| 41 | `only <tools> are available. /return to come back.` | `only <tools> are available. /return to stop.` |
| 42 | `The act is done, so the state is over. Carry what it gave you into the work.` | `Done. Take anything useful from it and get back to work.` |
| 43 | `The frame you were in is gone. State the goal, name the approach you were stuck in, then take a different first step.` | `Back. Say the goal, say what you were stuck on, then start somewhere different.` |
| 44 | `· nothing new arrived` | `· nothing new came up` |
| 45 | `· nothing to take away` | `· nothing worth keeping` |
| 46 | `open · you end it` | `running · you stop it` |
| 47 | `open · they end it, not you` | `running · they stop it, not you` |
| 48 | `done · this turn ends it` | `done · ends after this reply` |
| 49 | `, and this is the last one — it ends after this turn` | `, last one — it ends after this reply` |

### Material and refusals (`core/sources.py`, `core/walks.py`)

| # | before | after |
|---:|---|---|
| 50 | `empty · fewer than three recorded turns are available for two pairs` | `need at least 3 messages from you in this chat` |
| 51 | `unavailable · doomscroll feed is disabled by settings` | `the feed is turned off in settings` |
| 52 | `unavailable · feed returned no items` | `the feed came back empty` |
| 53 | `empty · fewer than three commit subjects in the last month across the projects this chat can see, so there is nothing to recombine` | `need at least 3 commits in this repo from the last month` |
| 54 | `unavailable · no local project repository is available` | `this chat is not inside a git repo` |
| 55 | `empty · local git history is unavailable` | `no commits to read here` |
| 56 | `unavailable · the concept map has no edge to point at yet` | `the map has no links to point at yet` |
| 57 | `daydream empty · fewer than two recorded turns are available` | `daydream: need at least 2 messages from you in this chat` |
| 58 | `daydream empty · no unused pair remains` | `daydream: no new pairs left` |
| 59 | `dream empty · fewer than two local git commit subjects are available` | `dream: need at least 2 commits in this repo` |
| 60 | `dream empty · no unused recombination remains` | `dream: no new pairs left` |
| 61 | `doomscroll empty · no unused feed item remains` | `doomscroll: no new posts left` |
| 62 | `doomscroll unavailable · …` | `doomscroll: …` |
| 63 | `unstuck unavailable · no local project repository is available` | `unstuck: this chat is not inside a git repo` |
| 64 | `unstuck empty · history is unavailable` / `graph edge is unavailable` | `unstuck: no commits to read here` / `no map links to read here` |
| 65 | `unstuck empty · no unused direction remains` | `unstuck: no new move left` |
| 66 | `JOINED · memory one: … · memory two: …` | `LINKED · one: … · two: …` |
| 67 | `APART · memory one: …` | `NO LINK · one: …` |
| 68 | `· touch: <words> · possibility: try treating <words> as the subject` | `· shared: <words> · idea: try <words> as the topic` |
| 69 | `· touch: nothing in common · possibility: none — say what the gap was` | `· shared: nothing · idea: none, these do not connect` |
| 70 | `connection · <a> ↔ <b>` | `link · <a> ↔ <b>` |
| 71 | `adjacent · <a> ↔ <b>` | `no link · <a> ↔ <b>` |
| 72 | `· these two have not touched` | `· these two do not connect` |
| 73 | `direction · not another pass at <last> · take <earlier> from a different angle` | `next move · skip another pass at <last> · try <earlier> a different way` |
| 74 | `direction · only one change in history (<last>), so there is nothing earlier to return to` | `next move · only one commit here (<last>), so there is nothing earlier to go back to` |
| 75 | `· graph edge: <edge>` | `· map link: <edge>` |
| 76 | `· first: write the smallest test for that different angle` | `· first: write the smallest test for that different way` |
| 77 | `· first: write the smallest test that approaches <last> from that side instead` | `· first: write the smallest test that comes at <last> from that side instead` |
| 78 | `walk unavailable · graph '<g>' <mode> · <detail>` | `walk: graph '<g>' failed (<mode>) · <detail>` |
| 79 | `walk unavailable · graph '<g>' cannot jump (no_far) · …` | `walk: graph '<g>' cannot jump far (no_far) · …` |
| 80 | `walk unavailable · graph '<g>' empty · has no starting node` | `walk: graph '<g>' is empty, nowhere to start` |
| 81 | `WordNet data is unavailable · …` | `WordNet data could not be read · …` |

### Pane (`desktop/plugin.js`)

| # | before | after |
|---:|---|---|
| 82 | `no state` | `nothing running` |
| 83 | `/walk starts one` | `/walk to start` |
| 84 | `backend unavailable` | `plugin unavailable` |
| 85 | `the plugin backend is not mounted` | `the plugin is not loaded` |
| 86 | `the backend did not answer` | `the plugin went quiet` |
| 87 | `last flight · 3 concept(s)` | `last flight · 3 concepts` (singular too) |
| 88 | `no projected concepts yet · /walk starts one` | `nothing on the map yet · /walk puts some there` |

### Listing and settings (`plugin.yaml`, `README.md`)

| # | before | after |
|---:|---|---|
| 89 | `Five bounded agent states … /dream recombines local git commit subjects …` | `Five short agent states … /dream mixes up your recent commits …` |
| 90 | `Disclosure — daydream reads local read-only MEMORY.md and USER.md` (untrue) | `What it reads: daydream reads this chat's own recent messages` |
| 91 | `when the shape of the work has a name (a loop, a data wall, a long stretch)` | `when your work looks stuck — going in circles, hitting a wall, or grinding on too long` |
| 92 | `How many turns one recommendation holds … counted in turns rather than minutes` | `How many messages a suggestion stays up … Counted in messages, not minutes` |
| 93 | `Turns without a state before one is recommended` | `How many messages without a state before one gets suggested` |
| 94 | `One bounded scan of the last 14 days … steers away from concepts you have already met` | `One limited read of the last 14 days … avoids concepts you have already seen` |
| 95 | README: `six graph hops; the frame moves elsewhere` | `6 hops across the concept map, taken right there in the command` |
| 96 | README: `Daydream and dream block tools; doomscroll and unstuck permit only their declared tools` (untrue) | `Tools stay open in every state unless the entry explicitly uses block: true` |
| 97 | README: `2 recombinations` / `1 direction` | `2 links` / `1 move` |

## Verification

- `pytest tests/ -q` → 946 passed, 6 skipped.
- `node tools/desktop_harness/mount.mjs` → 12 properties PASS.
- `python3 tools/examples.py --check` → ok, 5 state examples honour their contracts.
