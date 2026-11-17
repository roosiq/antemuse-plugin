# State × canvas: what the picture is allowed to be

Status: **proposed — 2026-11-16**. One decision is open (see §5); everything before it is
either shipped in this change or recorded evidence.

## 1. The owner rule this change is written under

On 2026-11-09 the owner set one constraint: **the concept-activation graph is the only
visualization** — "there should be no other states". The code already carries that sentence at
`desktop/plugin.js:1533`: *"The activation of the concept graph is the only visualization: what a
state looks like IS which concepts are firing while it runs. A state with nothing firing has no
picture, and the surface stays bare rather than showing stand-in art for a moment that did not
happen."*

Any proposal that adds per-state pictures is therefore out of bounds. An earlier draft of this
change did exactly that — a hand-authored composition per state, plus dose cells drawn on the
canvas. That draft is withdrawn and the reason is recorded here rather than quietly dropped: it
would have put five stand-in pictures back on a surface whose whole point is that pictures are
earned by firing material.

## 2. What the pane actually does today

Two different code paths, and only one of them is what the sentence above describes.

- **The strand field** (`SCENES`, `COMPOSITIONS`, `art.render`) is live. It is chosen from a
  hand-written table keyed by state name (`idle`, `work`, `walk`, `daydream`, `dream`,
  `doomscroll`) and it draws procedural strands, not concepts. This is stand-in art.
- **The activation layer** (the `LAYER`/`paint` path) is the one that draws what fired, from
  `/state?graph=1` (`lit`, `path`). It is **not wired to the pane's poll**, which asks `/state`
  without `graph=1`. So the rule in the comment is not yet the behaviour.

Measured consequence of the table alone: `unstuck` existed in the registry from 0.11.21 and had no
table entry, so `/unstuck` drew the `idle` field — a person in a state saw the picture of no state.
That is the same class of defect as the one-state cut: a literal list maintained beside a registry
that outgrew it.

## 3. What this change ships (done, with proofs)

1. `sceneFor(active, busy)` — one exported rule, four answers: `idle` (nothing running), `work`
   (a turn with no state), `bare` (a state that has fired nothing), or the state's own field.
   The poll calls it; the poll no longer holds its own copy of the table.
2. `bare` is a real picture: zero strands, empty composition (`??`, not `||`, so an empty list is
   an answer rather than a missing value).
3. `unstuck` has a field, so no registry state falls back to `idle`.
4. Doomscroll is `NO_FIELD`: its feed text is untrusted and never persisted, so it must not
   become lit cells. It drew a scene that rendered zero lit pixels — the worst of both, a picture
   claimed and nothing on it. It is now `bare` with the strip carrying the count.
5. Parity is pinned from both sides: `tests/test_pane_scenes.py` reads the real file and compares
   it to `core.states.STATES`; `tools/desktop_harness/mount.mjs` asserts the four answers on the
   real export.
5. A dead branch was removed: the 3D kit hung off `Promise.reject(...).then(...)` and could never
   run, so it looked live and was not. `probe.mode` is `strands`, which is the truth.

Proofs: removing `unstuck` from the table fails `test_every_agent_state_has_a_picture_or_a_reason_not_to`
(`states with no picture in the pane (they draw idle): ['unstuck']`); removing the `served <= 0`
branch fails the harness (`a state that has fired nothing must not be drawn as idle`). Both
restored, suite green (893 passed, 3 skipped), harness 12 properties PASS.

## 4. What it proposes next

**P1 — retire the stand-in field.** The strand compositions are the last of the mood pictures. Per
§1 they should go: a state's picture is its firing concepts, and `bare` covers the moment before
anything fires. This is a behavioural change to what the pane shows and needs the owner's word.

**P2 — wire the activation picture to the poll.** The poll asks `/state?graph=1` and passes `lit`
and `path` into the layer that already knows how to draw them, so what a person sees is the same
payload the cockpit draws. Bounded by the existing caps (the endpoint already caps nodes and
edges); no new endpoint.

**P3 — dose and ending stay in the strip, not on the canvas.** The canvas is a picture of *material*.
`3 of 5 hops` and `ended · dry` are facts about the state, and the strip already carries both. If a
person wants the count while looking at the picture, the strip is at the top of the same pane. This
replaces the draft's "dose cells" idea, which drew a budget on a surface that is supposed to show
what actually happened.

**P4 — precedence.** Running state > last flight note > idle, mirroring the precedence already
pinned for the flight receipt. `/explore`'s own pane owns the canvas only while explore is active.

## 5. Open decision

**Retire the strand field entirely (P1), or keep it as the fallback for a host that cannot draw the
activation layer?** Retiring is faithful to §1 and removes ~400 lines of kit; keeping it means the
pane has two answers to "what does a state look like", which is how the original drift happened.
Recommendation: retire, and make a missing activation layer visible as `bare` rather than as stand-in
art.

## 6. Must not change

- No state semantics, dose, turns, endings, tool policy, or registry contents.
- The canvas never renders material as text: no headlines, memory prose, commit subjects, seed
  markers, graph ids, or the model block. Counts and firing labels only, and firing labels are
  concept labels the ledger already shows in the cockpit.
- No new runtime dependency; no network from the pane; nothing persisted by the canvas.
- `/explore` and the cockpit keep their own surfaces.
- The pane stays one file under its 200 KB budget.

## 7. Acceptance

- Every state in `core.states.STATES` has a picture, or is explicitly `bare`; an unknown state
  cannot silently draw `idle`. (Pinned: `tests/test_pane_scenes.py`.)
- The four answers are asserted on the real export, not on source text. (Pinned: `mount.mjs`.)
- P2, when built: the lit set on the canvas equals `lit` from `/state?graph=1` for the same poll,
  proven by the cockpit harness's fixture, not by eye.
- P1, if taken: `SCENES`/`COMPOSITIONS` are gone, `bare` remains, and the harness property list is
  unchanged.
