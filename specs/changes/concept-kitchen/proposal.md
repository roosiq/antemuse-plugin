# concept-kitchen — proposal

Change id: `concept-kitchen`
Repo: `/home/ryan/concept-kitchen` (standalone Hermes plugin)
Derived from: `/home/ryan/concept.cooking` (moves, SparkCard contract, quality rules)

## Goal

Ship a CLI minigame that makes creative moves playable and scoreable by both
humans and agents, filling the marketplace's empty ideation/creativity lane
(`brainstorm`, `ideation`, `divergent` → 0 catalog hits across 976 entries).

## Non-goals

- No web UI, no dashboard pane, no desktop page. Terminal text only.
- No new creative engine. Moves and the SparkCard rubric come from concept.cooking.
- No ranking by model, no per-model difficulty, no tournaments, no cron.
- Not an MCP shim: the engine deal is optional and a round plays without it.

## Rules of the game (the contract)

- Five rounds per service; moves fixed as unpack → flip → shift → connect → flip;
  distance ladder near → lateral → lateral → far → far.
- Round *n+1* seed is the player's round-*n* spark (`title — try_next`).
- Submission is exactly three parts: `title :: why it connects :: try next`.
- Judge is deterministic: move discipline / mechanism / actionability / novelty,
  25 each, plus the published penalty list. No model call, no randomness.
- One open service per profile at a time; both surfaces share it.
- Humans and agents write to one board; `kind` and `model` are labels, not weights.

## Acceptance criteria

1. `hermes plugins doctor ~/concept-kitchen` passes: discovery, manifest, import, registration.
2. `uvx pytest tests/ -q` passes, covering: strong spark ≥ 72, generic advice < 40,
   one dimension beating three, derivative spark scoring 0 novelty, connect
   requiring source + mechanism, hint −8, label-prefixed fields parsed, five-round
   chain completing, human+agent sharing a board, engine failure labelled `deck`.
3. `/cook play` in a real CLI session deals a seed, a move, and the expected distance.
4. `/cook submit` returns a scored card and either the next round or the service summary.
5. Agent play through `cook(action=...)` produces the same scoring path and a board row
   carrying `kind=agent` plus the model label.
6. Engine failure (today: HTTP 401) never yields starter-direction cards presented as
   engine output; the brief states `PAR deck` and prints the engine error.
7. State survives process boundaries: `/cook play` in one invocation, `/cook submit`
   in the next.

## Verification commands

```bash
hermes plugins doctor /home/ryan/concept-kitchen
CONCEPT_KITCHEN_HOME=$(mktemp -d) uvx pytest tests/ -q
hermes plugins enable concept-kitchen
hermes chat -q '/cook play'
hermes chat -q '/cook submit "T :: W :: N"'
hermes chat -q '/cook board'
```

## Must not change

- Nothing in `/home/ryan/concept.cooking` (read-only source of moves and rules).
- No production deploy, no secret change, no catalog publication in this change.
- The Concept Cooking Worker's `SERVER_API_KEY` is out of scope; the 401 is
  reported, not fixed here.

## Known limitation

One open service per profile (an `active.json` file), so two concurrent sessions
cannot each hold a service. Acceptable for a solo CLI game; a per-session key is
the follow-up if the leaderboard gets real use.
