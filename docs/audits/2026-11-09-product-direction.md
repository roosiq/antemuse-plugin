# Product and direction audit — 2026-11-09

Two independent models read the same 159 KB record (README, `docs/spec.md`,
`docs/architecture.md`, `docs/brand.md`, `TESTING.md`, the submission spec and
demo plan, plus a one-line inventory of 33 change specs) and answered the same
eleven questions. Neither saw the other's answer, and neither had tools, so
neither could change the repo.

- `anthropic/claude-opus-5.5` via OpenRouter, 1 m 15 s
- `openai/gpt-5.6-terra-pro` via OpenRouter, 1 m 19 s
- `gpt-5.6-sol` was attempted first and refused: the ChatGPT-account Codex
  entitlement does not include it (`HTTP 400`), so Terra Pro stands in as the
  second large model.

Both are kept verbatim below. The synthesis and the defect check are mine.

## Synthesis

**They agree on the centre of gravity.** Both call this a craft object with one
real product inside it, and both name the same product: a stuck loop, a walk, a
different first step, enforced by the host. Opus: *"a measured 'you're looping,
step out, come back with a different first step' intervention."* Terra: *"the
reliable way an agent acknowledges 'this approach is not working; I am changing
how I proceed.'"*

**They agree the public primitive is wrong.** State is a good internal mechanism
and a bad menu. The metaphors (dream, doomscroll) are what generated the sprawl:
each demanded its own material source, art pack and goal. Opus would keep walk,
daydream and unstuck; Terra would expose only walk for this submission and hold
dream back for a craft-object direction.

**They agree the evidence is thin, and both say so without hedging.** Walk's
benefit is p = 0.17 at n = 8 with negligible uptake of delivered material. The
honest product claim is behavioural — the next step differs — not outcome.
Neither treats the hackathon as a place to claim creativity gains.

**They agree on the failure mode.** It wins as terminal cinema and becomes a
screensaver with cognitive labels; the parent-brand motive (human cognition,
drift toward a mean) is not measured by anything in the plugin. Terra adds the
retention version: ceremony that does not change the next useful action gets
punished.

**Where they diverge.** Opus is more surgical: keep three states, ship them, and
fix the disclosures it says understate what is read (`state.db`, `session-scan`,
`<repo>/.antemuse/`, and doomscroll feed text entering the agent's context).
Terra is more reductive: one state, one loop, and treat "agent observability"
as the credible second product rather than a directing metaphor.

**The finding that outranks all of it.** Both independently said the shipped
acceptance path is broken: `TESTING.md` and `demo.md` teach commands that no
longer exist. That is true, and it is my defect, not the plugin's — details
below. A judge or a test user hits it in the first minute.

## Defect check (verified in the tree, not taken on trust)

| claim | verdict | evidence |
|---|---|---|
| `/break` and `/states` are taught but missing | **true** | `__init__.py:567-576` registers one command per state plus `return`; the states are `walk, daydream, doomscroll, unstuck, dream`. `/break`, `/mood`, `/states`, `/spark`, `/keep` are **tool actions** (`STATE_SCHEMA` enum), not slash commands. |
| demo beat shows `677 tests` | **true** | `tools/demo/beats.json:9`; the suite is 906 passed, 1 skipped. |
| README says nothing else is read outside the data dir | **true and wrong** | `README.md:218-221`; `core/history.py:573` reads `~/.hermes/state.db` and `session-scan` is LIVE (spec §15). |
| five states vs "four" | **true** | `core/states.py` has five; the README and demo say four and never mention `unstuck`. |
| TUI names a state that does not exist | **new, mine** | `core/tui.py` key `d` calls `engine.enter("dissociate")`; `dissociate` is not in `STATES`. |

Not verified, and therefore not repeated as fact: Terra's claim that the visual
contract forbids the clock and key legend the demo shows; Opus's token-cost
figure (it is a citation from spec §15, not a measurement I made); both models'
read that `doomscroll` is a poor remedy — that is a judgement, not a defect.

## Owner decisions and corrections (2026-11-09)

- **No states dropped.** Ryan declined both cut lists; walk, daydream, doomscroll,
  unstuck and dream all stay for the submission. The audits' recommendation to
  reduce the menu is a direction question for after the five-user test, not a
  change to the build.
- **The evidence claim was weaker than the record said.** Both audits quoted
  p = 0.17 at n = 8 from spec §16 as "the one positive-direction result". The
  better-powered run was already on disk and says otherwise: 32 pairs per
  condition, raw +1.44 categories (p = 0.027), but the walk arm wrote 162 words
  against 119; length-adjusted +0.15 categories, 95% CI [−0.70, +1.00],
  p = 0.365 (`specs/changes/break-and-mood/incubation-test.md`). Spec §16 now
  records the null and marks the n = 8 figure superseded. The surviving effect is
  ~36% more words, not broader thinking — which is what the submission may claim.

## What I would do with it

1. **Demo the recovery loop, not the menu.** Loop → the counter that fired →
   walk → return account → a visibly different first step. Use the blocked-tool
   beat as the proof that the host is the authority.
2. **Fix the acceptance path before anything else** (done in this commit): real
   verbs only, correct counts, and no promise of a takeover command that does
   not exist.
3. **Tell the truth in the disclosures.** Add the `state.db` read and the
   `<repo>/.antemuse/` write; say that doomscroll feed text enters the agent's
   context.
4. **Answer the direction question after the five-user test, not before.**
   Opus's kill condition and Terra's are compatible: users keep it enabled,
   unprompted, and can name the next moment they would use it.

---

## Audit 1 — `anthropic/claude-opus-5.5`

MODEL: anthropic/claude-opus-5.5

1. Verdict

It's a craft object with one product inside it. That product is a measured "you're looping, step out, come back with a different first step" intervention. Right now it's buried under four visual pipelines, a concept ledger and an evaluation library. The record contradicts itself on its own basics: four states or five (spec §1 says both), 12 actions or 14 (architecture §1), and five commands or six.

2. Steelman

Most agent plugins add capability. Antemuse adds rhythm, and it is enforced. The host refuses tools (spec §6.2), states end without inference (spec §1), and the return account is built from the journal, not from a template (spec §6.4). The recommender says nothing unless a counter justifies speaking, and it names that counter (spec §7). The walk design follows the research instead of decoration: it removes the problem rather than feeding the agent concepts. The author reversed course when measured uptake came in at 1 of 36 (spec §4.1). The honesty discipline is rare too: named failures, "no creative-quality improvement is claimed" (README), p = 0.17 stated plainly (spec §16). "Capability beyond a prompt" is real here and takes seconds to show.

3. Who it's for

Named person: a solo developer running long Hermes sessions, about two hours in, watching the agent retry the same failing tool call. They don't reach for the tool themselves. The recommender reaches for them: "same tool failed ≥ 3× in a row → walk" (spec §7). That person is real.

Everyone else is thin:
- Doomscroll's goal is "distraction via social-media stupidity" with comedic share "not measured" (spec §8.2a). No user is named who wants that for their agent.
- Dream runs for 30 minutes with tools blocked (spec §4.4). I can't name the moment anyone wants that.
- The "person takes the same state beside it" (README) has no evidence that any human has done it.

The real user today is Ryan.

4. Three biggest product risks

R1. The demo and the test guide drive commands that no longer exist.
- demo.md §3 and §4 depend on /mood stuck → /break → "strain ≥ 1".
- The spec says "no /break … no /mood" (spec §3.3) and that strain "is gone" (spec §7).
- TESTING.md's "First run" uses /break and /states, and says /spark, /keep, /again are "present". They were consolidated away (spec §15, command-surface).
- The demo's count beat says "677 tests". The spec says 905/906 (spec §13).

Your first five users and your judges hit dead ends in the first minute. Polish and reliability scores die here.

R2. Profile-wide state breaks real work, and it already broke the author's. demo.md §6 records both: "a state entered in the live profile stops real work. It happened to this session mid-planning", and the live gateway ran stale blocking code (Trap 1). State is profile-wide on purpose (spec §11), and states run "under cron and the messaging gateway" (README, Unattended runs). One chat's dream can stall a cron job.

R3. The disclosures understate what the plugin reads and ingests.
- The README says "Nothing else outside the plugin data dir is read at runtime."
- concept-history reads Hermes' state.db (spec §15).
- session-scan reads up to 300 past messages in a background thread.
- Dream reads commit subjects across repos (spec §8.2a).
- The plugin writes <repo>/.antemuse/ into user repos.
- Doomscroll pipes Bluesky "what's hot" into the model's context with "react to this" (spec §6.1). That is untrusted public text handed to an agent that may have tools open, and states are open by default.

A catalog reviewer who finds this will treat the whole honesty posture as suspect.

5. Is "state" the right primitive?

No. It's the right mechanism and the wrong product. What has evidence or a clear user is a tool-policy window, a forced reframe on return, and a counter-based trigger. That is an agent work-rhythm / anti-fixation product, and "state" is its implementation. The anthropomorphic frame (dream, doomscroll) is what generates the sprawl: each metaphor demanded its own material source, art pack and goal. The mismatch shows in the doses: a "walk" is "6 turns worked" with tools open (spec §4), which is a reframe instruction, not a walk. The spec admits "the frame is gone" is "an instruction, not a fact" (spec §4.1).

What would change my mind: in the five-user test (section 8), users start doomscroll or dream on their own, without a recommendation, more than once, and say the takeover is why. Then it's a companion/creativity object, state is the primitive, and the brand motive (human cognition) fits.

6. Three directions

A. Unstick: recommender + walk + forced different first step, with unstuck for empty repos.
- Tradeoff: it's the most useful direction, but ideation evidence is null or directional (spec §16), so you can show the behaviour change but not a better outcome.
- 84-second demo: a real loop, the recommender line with its counter, a walk, the return account, then the agent naming a different approach. End on the different step, not on a claimed fix.

B. Host-enforced behaviour contracts: states as policy windows ("not a prompt").
- Tradeoff: strongest on the "beyond a prompt" criterion and the easiest to prove. But it's infrastructure: it loses the Antemuse voice and is dull to non-builders.
- Demo: the block beat, a refused call, the escape hatch, restoration. That's 40 seconds of truth and 40 seconds of padding.

C. Companion art object: the wordless takeover that the human watches and rests beside.
- Tradeoff: best for creativity and for the brand motive, weakest on usefulness. The visuals are PARTIAL: doomscroll's composition is "open" (architecture §10), unstuck has no art, and the desktop pane is unverified in the app (TESTING.md; spec §15 claims "Verified in the app" — another contradiction).
- Demo: mostly takeover footage, which on a phone at 390 px is dark blocks.

Pick A, and use B's block beat as its proof shot.

7. What to cut now

- States: cut dream (30-minute ceiling; when it invents, it's a template at 5–8% novel, spec §15) and doomscroll (injection risk, unmeasured goal). Keep walk, daydream, unstuck. That reconciles the "four vs five" mess by making it three.
- Surfaces: the desktop pane and activation stills (PARTIAL, unverified), the concept graph and projection tools, SD photographs on the tailnet host (BR-7 conflict, spec §14.12), scene3d-renderer, the Matrix/Telegram profiles (unverified), and the legacy watch/card/image actions.
- From the submission tree, or at least from the README: the whole experimental library (collider, collision, llm, orchestrator, selection, feedback, presenter, evaluation/, data/collider). "Library only; not runtime-wired" appears seven times in the layout. Judges read that as unfinished.
- Settings: six is too many for the hackathon. Keep recommend_enabled and recommend_cooling_minutes.

8. Five users, one week

Give each user the build with the recommender on and session-scoped state, if you can make that change; otherwise warn them. They do their own normal work for a week. Then collect:
- each recommendation that fired, with the counter that triggered it, and whether they or the agent took the state;
- after each return, whether the agent's first step differed from its pre-walk approach, judged by them, not by you;
- whether they opened the takeover more than once;
- whether they disabled the plugin, and when.

Kill conditions:
- Fewer than two of five keep it enabled at the end of the week.
- Or the recommender fires mostly on non-loops, so users mute it.
- Or any user's real work is blocked by a state they didn't start.

If returns don't change the first step for anyone, direction A is dead and only C remains.

9. The one change this week

Make the demo and TESTING.md run only on shipped verbs, then shoot the A-path demo (section 6) on the frozen commit. The current script will fail on camera at 0:06 (R1). Everything else is secondary to judges and testers seeing a working path.

10. Six months after a win

- The documentation rots. The test count has already appeared as 107, 591, 627, 660, 669, 677, 684, 686, 905 and 906 across the record. With 30+ change specs, nobody but the author can tell what ships, contributors can't enter, and the drift becomes the product's reputation.
- Profile-wide state meets real usage (gateways, cron, multiple chats). The first viral complaint will be "a plugin froze my agent", which the demo itself shows as possible.
- Token cost. One 6-turn model-lane entry measured ~4.0M input tokens (spec §15, state-settings-experiment). It's unproven whether runtime costs that much, but someone will measure it publicly.
- It wins as a cute anthropomorphic toy that says nothing about human cognition or ideological drift. That's the opposite of the parent brand (stated motive, 2026-10-10). Nothing in the plugin measures the human, so success here builds a brand Antemuse didn't intend.

---

## Audit 2 — `openai/gpt-5.6-terra-pro`

MODEL: openai/gpt-5.6-terra-pro

Verdict: This is a craft object with a real plugin mechanism, not yet a product. It can make a strong hackathon demo because host-enforced behavior, deterministic exit, and recovery are genuine capabilities—but the current menu of states has not earned a recurring user need.

Steelman: Antemuse has a defensible core insight: agents should not only generate more text when work stalls; they should be able to enter explicitly bounded operating conditions that alter permissions, context, and return behavior. The host—not the model—is the authority, so a blocked state actually blocks tools, state exit restores normal work, and the agent returns with an account rather than silently resetting (spec §§5–6, §12). Separating a wordless human-facing ritual from a structured model-facing ledger is unusually thoughtful. If Antemuse becomes the reliable way an agent acknowledges “this approach is not working; I am changing how I proceed,” it is more than prompt theater.

Who it is for: Maya, a solo staff engineer using Hermes on a difficult task who has just repeated the same failed tool/test/search loop and no longer trusts another immediate attempt. She reaches for “help me break this loop and resume differently,” not “put my agent into daydream.” That person is still thin: the record contains careful internal evidence and a test-user build, but no evidence that users recognize, request, repeat, or value these named states.

Three biggest risks:

1. No demonstrated outcome. The record is commendably explicit: the walk’s benefit is unestablished, with p = 0.17 at n = 8; uptake of delivered material was negligible; several configurations were null or slightly negative (spec §16, §19.1). The product’s central promise is therefore experience and scheduling, not better work. That may be enough for art; it is not enough for a durable work tool.

2. The recommendations can feel arbitrary or actively perverse. A “data wall” caused by two source failures recommends doomscroll, whose stated purpose is “distraction via social-media stupidity and comedy” (spec §7; §8.2a). That is clever as a concept, but it does not obviously help someone whose research sources are failing. The state names describe the author’s theory of cognition, not a user’s job to be done.

3. The product is too fragmented to trust under deadline. The written record conflicts on the public interaction: TESTING still teaches /break and /states, while the command contract says six commands and nothing else (TESTING, “First run”; spec §3.3). The demo plan uses /mood and claims a live clock/key legend while the visual contract forbids titles, counters, labels, and explanations (demo §3; spec §10.1). Desktop/activation surfaces are simultaneously described as wired and explicitly not seen in the running app (spec §§10.6, 17.2). This reads as a system still arguing with itself.

Is “state” the right primitive? Internally, yes: a state is a clean runtime primitive for policy, bounded context, timing, and return residue. Publicly, no: users do not wake up wanting a state; they want recovery from a loop, a deliberate pause, a fresh approach, or visibility into what their agent is doing. Antemuse should be a work-rhythm product whose internal implementation happens to use states. I would change my mind if five users independently chose and reused “daydream,” “dream,” or “doomscroll” by name without prompting, and could explain why each changed their work.

Three directions:

1. Work-rhythm recovery — recommended. Make “stuck loop → walk → different next step” the product. Tradeoff: less mystical, fewer states, less visual variety; gain: a concrete moment of need. In 84 seconds, show a real loop, the measured trigger, an ambient walk, return, then a visibly different next action.

2. Agent observability and control. Position it as an inspectable execution mode: what the agent may do, what it received, what changed, and how it returned. Tradeoff: competes with agent dashboards and loses some romance. In 84 seconds, show explicit tool closure, an attempted blocked call, scoped material, then deterministic restoration.

3. Creativity ritual / craft object. Own the art: the agent and person take a deliberately strange, bounded imaginative interval together. Tradeoff: niche and hard to price; do not pretend it improves creativity. In 84 seconds, minimize terminal proof and make the visual experience plus a surprising return account the whole point.

What to cut now:

- Cut doomscroll from the public story and demo. “Random feed · consume, do not synthesize” is not a credible remedy for work failure (spec §4.3).
- Do not expose experimental spark/keep, Collider, selection, shards, or activation maps. They dilute the thesis and the record explicitly says they are not quality evidence (README, “Experimental exploration library”; spec §8).
- Do not demo desktop, Matrix, Telegram, or activation stills. Real-client and packaged-app verification remain incomplete (spec §§10.4, 10.6, 17.2).
- For this submission, expose one state: walk. Keep dream only if you choose the craft-object direction. Daydream, doomscroll, and unstuck are a menu before there is a habit.

Test with five users in one week:

Give each person a real stuck Hermes task, not a staged creativity prompt. Ask them to work until they feel stuck; show them Antemuse once; then leave them free to invoke it or ignore it on a second task. Watch for: whether they understand the moment it is for, whether the recommendation feels justified, whether the return changes the next action, and whether the visuals clarify or merely decorate.

Kill it as a work-rhythm product if four of five use it only when coached, cannot name a future moment they would invoke it, or describe the state names/visuals as irrelevant to getting unstuck. Keep it only as a craft object if they enjoy it but do not alter their behavior.

The one change this week:

Replace the four-state proposition with one complete recovery loop: “You are repeating a failed approach. Take a walk. When you return, name the stuck approach and make a different first move.” This is the only part that joins a real observed signal, a defensible research-adjacent mechanism, host-level capability, and a visible outcome (spec §§4.1, 6.1, 7, 16).

What makes it fail six months after launch, if it succeeds now:

It wins attention as terminal cinema and then becomes a screensaver attached to arbitrary cognitive labels. Users will not tolerate a profile-wide agent state crossing chats (README, “Notes”; spec §11) unless it reliably helps the active project; feeds, corpora, visual asset pipelines, and experimental branches will keep adding maintenance while the core question—whether anyone resumes work better—remains unanswered. A hackathon can reward novelty. Retention will punish ceremony that does not change the next useful action.
