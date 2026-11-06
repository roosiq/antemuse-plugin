# Probe: is the walking agent more creative?

First cheap test of the claim the whole design rests on. One run per condition,
same prompt, same model: *"Give me 8 unusual uses for a brick. One per line,
numbered, no explanation."* — the Alternate Uses shape.

Proxies, computed with WordNet over the nouns each list actually uses:

| | ideas | distinct nouns | WordNet categories | mean pairwise similarity |
|---|---|---|---|---|
| idle | 8 | 27 | 7 | 0.426 |
| walking | 8 | 30 | **12** | **0.269** |

Lower similarity and more categories means the second list drew from farther
apart. The walking list reached `act` (Foley thud), `substance` (thermal mass),
`person` (body-fall), `group` (spawning structure); the idle list stayed in
artifact, food, event, phenomenon.

## The part that argues against reading much into it

The walk's own material was `lights-out → bedtime → hour → canonical hour` — time
of day. **None of that appears in the ideas.** The first idea in both lists is a
bed warmer. So whatever produced the wider spread, it was not the walk's concepts
being used; at most the state changed register.

n = 1 per column. The proxy measures word spread, which reward lists that wander
and punishes lists that cohere — an incoherent list can score as "creative". It
is a cheap instrument, not a creativity test.

## What a real test needs

Paired design (same task, N ≥ 20 state/no-state pairs), blind scoring by more
than one judge or a validated rubric, semantic distance computed from embeddings
rather than WordNet, and a pre-declared effect size — the same discipline the
Toslop measurements use. Until then the honest claim is: the design is based on
published incubation work (`docs/creativity-exercises.md`: a walking break lifted
Alternate Uses scores for 81% of participants vs 23% on a convergent task), and
this implementation has not been shown to reproduce it.
