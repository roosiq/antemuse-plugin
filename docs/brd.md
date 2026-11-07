# Antemuse — business requirements, from the operator's own words

Status: draft, consolidated 2026-11-06.
Owner: Ryan Cook.
Source: every message Ryan sent in the chain that produced this plugin
(`@session:default/20261104_181830_944602c9`), deduplicated, listed in full in
the appendix. Nothing here is inferred from market data, the code, or another
agent's summary. Where a line says what Ryan wants, it quotes him.

`docs/requirements.md` is the companion artifact derived from the code and the
brand work. This document is the authority where the two disagree, because it
records what was actually asked for.

---

## 1. The ask, as it actually arrived

Ryan did not open with a product brief. He opened with a market question and
corrected the product into existence over one long session. The corrections are
the requirements; each removed something the agent had assumed.

**It began as a gap hunt.** "Go on the Hermes plugin marketplace and find gaps
with cognitive plugins. Creativity, chaos, randomness, semantics, etc." A second
pass through `concept.cooking` asked what could be built there.

**Then it was a game.** "Lets make it a minigame that both humans and agents can
play" — which he retired two turns later.

**Then it was a visual experience, not a game.** "Nah. Let's make this less of a
game and more of a visual experience for humans and vision models but text
experience for language models." That sentence is the product. Everything since
elaborates it.

**Then it stopped being a place.** "No. This should be the equivalent of an agent
taking a walk, daydreaming, dissociating, etc. not rooms." The vocabulary of
containers — kitchen, station, room — was retired with it.

**Then the screen was emptied.** "The user should not see text, jargon,
explainers or anything. This should be more about ingecting content into the
context with your agent."

**Then it had to belong to the interface it was invoked from.** "Everything from
these actions should be built into the current frame / project / chat the user
initiates them from."

**Then it was named.** "it's just antemuse."

## 2. What the business requires (BR)

Each requirement traces to a sentence Ryan wrote. These are business statements;
the behavioural contract lives in `docs/spec.md`.

**BR-1 — A cognitive gap in the marketplace is worth filling.**
The catalog held 976 entries with zero results for ideation, brainstorming, or
divergence. The reason to build is that the category is missing, not that demand
is proven. *"Go on the Hermes plugin marketplace and find gaps with cognitive
plugins."* Success measure: the plugin exists, installs, and is discoverable in
the closest available category. Demand stays unmeasured and must not be claimed.

**BR-2 — The product is a difference in experience between two audiences.**
The model receives text; the person receives imagery. This asymmetry is the
product, not a rendering choice. *"a visual experience for humans and vision
models but text experience for language models."* Consequence: any feature that
shows the person an explanation of the mechanism violates the requirement.

**BR-3 — A state is a temporary change of behaviour, not a container.**
*"This should be the equivalent of an agent taking a walk, daydreaming,
dissociating, etc. not rooms."* The four states are walk, daydream, doomscroll,
and dream. Vocabulary that reintroduces a place — room, kitchen, station, level —
is out of scope by instruction.

**BR-4 — Each state draws on a real corpus, not generated filler.**
Walking moves through a concept graph; daydreaming returns to stored memories and
looks for connections; doomscrolling consumes random social content; dreaming
recombines stored concepts into new material. *"Walk = visualize taking a walk
with periodic events... Doom scroll ... complete randomness of social media
content fed to visualizer and agent. Dream = long length, revisit memories and
find connections."* And: *"Let's use wordnet and framenet for the datasets here."*

**BR-5 — The person sees pictures and nothing else.**
No titles, counters, captions, or explanation on screen. *"The user should not
see text, jargon, explainers or anything."* This holds on every surface, and it is
testable: no words may reach a terminal frame or a chat image.

**BR-6 — The visual experience must be worthy of a terminal.**
*"I want it to be a proper artistic cli visual like we see in Claude code or other
terminal cli takeover tools"*, then *"We need better scenes / images"*, then *"We
want a full image rendered in the cli then transitioned."* A full-bleed image with
a transition between states — not a status panel, not a wall of ASCII characters.

**BR-7 — Real imagery, generated on this machine.**
*"Let's use real images. Can you stand up a small local image generating model for
this."* Local generation is a requirement, not an implementation detail: no
per-image vendor cost, no external dependency in the core experience.

**BR-8 — The human can watch, and can act.**
*"The visuals should allow the person to watch and do the same."* The display is
not a spectator screen: the person can enter a state, write into it, and end it.

**BR-9 — Every surface gets what that surface can carry.**
*"Our plugin needs to be cognizant of the channel its writing to. Discord has a
much narrower field of view than others"* and *"Is there a way to bring this to all
the different types of clients in streaming ascii or snapshot ascii"*. Terminal:
continuous. Chat: a still. Text-only client: a record.

**BR-10 — Actions answer where they were started.**
*"Everything from these actions should be built into the current frame / project /
chat the user initiates them from."* No separate channel, no home-channel routing,
no side delivery.

**BR-11 — The agent returns with an account of the state.**
The person saw the pictures; only the agent can say what was behind them. The
plugin supplies the facts of the state so the return does not depend on the
model's memory.

**BR-12 — Walks are extensible by the operator.**
*"Let's create a class to handle new graph walks algorithmically, so users can
create their own concept walks within the plugin."* Built-in walks are defaults,
not the product boundary.

**BR-13 — The brand is Antemuse, undecorated.**
*"This is Hermes plugin so antemuse is a fine brand"*, and finally *"it's just
antemuse."*

**BR-14 — Cliches are disqualifying.**
*"Don't show things like why they connect. That's cliche."* The product never
explains its own connective tissue to the person.

## 3. Explicitly rejected

Built, then removed by instruction. These are requirements in the negative — do
not reintroduce them.

- A minigame with scores or play. *"Nah. Let's make this less of a game..."*
- A cooking station, a kitchen, a room, a level. *"Back off the original cooking
  station idea"*, *"not rooms."*
- Text, labels, explainers, or any prose shown to the person.
- The "dissociate" state — folded into doomscroll.
- The name `antemuse-states`, or any sub-brand of Antemuse.
- Explaining *why* two concepts connect.

## 4. Constraints the business has to respect

- **No model calls on the state path.** Entering, ticking, and ending a state must
  resolve without inference, so marginal cost is effectively zero and the feature
  works offline.
- **No invented material.** A missing corpus, a dead feed, or an empty memory is
  named, never filled in.
- **No deployment, publication, or purchase without explicit approval.**
- **Local-first.** Imagery is generated on the operator's machine; social content
  is the only network dependency, and its absence degrades to a named failure.
- **One operator, one machine.** There is no multi-tenant story and none is
  claimed.

## 5. Open business decisions

1. **Marketplace category.** The catalog's nine categories have no cognition slot.
   Filing under `general` hides the plugin; proposing a new category is a
   marketplace conversation, not a code change. Undecided.
2. **Demand.** No usage data exists. Any public claim about adoption would be
   invented, so none is made until the plugin is listed.
3. **Pricing.** Assumed free. Not stated by Ryan, and not contradicted either.
4. **Which surfaces ship in v1.** Terminal and chat are specified; Matrix and
   Telegram are configured in code but unverified against real clients.

## 6. Success, in business terms

- A person can start a state from the interface they are already in, watch it
  without reading anything, and end it without losing their work.
- The agent's first move after a state differs from the move it would have made.
  That is the entire purpose, and the only measure that matters.
- Installing takes under a minute, with no key, no account, and no network
  requirement in the core loop.

---

## Appendix — every message, in order

Extracted verbatim from the session database, deduplicated, compaction artifacts
removed.

39 messages.

1. [shake] Go on the Hermes plugin marketplace and find gaps with cognitive plugins. Creativity, chaos, randomness, semantics, etc
2. [shake] Let’s look at concept.cooking and see what we can build a plugin as
3. [shake] Remember this is a cli based tool. Lets make it a minigame that both humans and agents can play
4. [shake] Don’t show things like why they connect. That’s cliche
5. This is Hermes plugin so antemuse is a fine brand
6. [shake] Do research on quick exercises that improve creativity
7. [shake] Look at unique use cases for terminal applications including visualization
8. [shake] Let’s think about these actions as slash commands: dream, daydream, doom scroll, dissociate, take a walk, what else?
9. [shake] Nah. Let’s make this less of a game and more of a visual experience for humans and vision models but text experience for language models
10. [shake] Back off the original cooking station idea. This should be automated to cycle through various phases of concept discovery and movement based on the commands
11. [shake] No. This should be the equivalent of an agent taking a walk, daydreaming, dissociating, etc. not rooms
12. [shake] The visuals should allow the person to watch and do the same
13. [shake] What
14. [shake] Snap
15. Build this as a plugin to display into Hermes cli
16. [shake] I want it to be a proper artistic cli visual like we see in Claude code or other terminal cli takeover tools
17. [shake] Can you use threejs animations for the visualizations in terminal
18. [shake] Is there a way to bring this to all the different types of clients in streaming ascii or snapshot ascii
19. [shake] We need better scenes / images
20. Our plugin needs to be cognizant of the channel its writing to. Discord has a much narrower field of view than others
21. [shake] Walk = visualize taking a walk with periodic events. Periodic events come from the concept graph and are walked from concept to concept in text. Daydream = short length, visualization you mention is good. Bring back memories and try to find connections between them. Join connections when you think it’s good. Doom scroll (replaces Dissociate) = complete randomness of social media content fed to visualizer and agent Dream = long length, revisit memories and find connections. Invent new stories, objects, ideas, based on disparate connections between differing stored concepts
22. [shake] Do we need images for all of the frames or concepts in the concept graph
23. [shake] Wrong concept graph.
24. [shake] Great. Now how are we visualizing this concept walk for the person using the agent? It should be like an immersive video game in the cli
25. [shake] Let’s create a class to handle new graph walks algorithmically, so users can create their own concept walks within the plugin. Ps do we also have access to the Hermes memory module? How are we going to doomscroll?
26. [shake] The user should not see text, jargon, explainers or anything. This should be more about ingecting content into the context with your agent. The user should see imagery and feel like they’re taking a walk or dreaming or doomscrolling.
27. [shake] We want a full image rendered in the cli then transitioned
28. Use threejs-term
29. [shake] Show me a picture
30. [shake] Let’s use real images. Can you stand up a small local image generating model for this
31. [shake] Think about what these scenes should be for the user in the various hermes interfaces.
32. [shake] Okay let’s plan for this. You should also have another item sitting for you in your specs
33. [shake] Everything from these actions should be built into the current frame / project / chat the user initiates them from.
34. [shake] Walk me through the full design. What are we building
35. [shake] simplify that
36. [shake] okay what's the project called
37. [shake] it's just antemuse. let's do a design pass here so we know what branding we're going with.
38. [shake] We made some updates in hermes desktop yesterday. Can you take a look
39. [shake] consolidate my messages here throughout the whole chain into a brd
