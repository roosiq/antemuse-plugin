# Antemuse — architecture and functional plan

Status of this document: **current as of 2026-11-08**, generated against the code in
this repo and checked by `tools/spec_audit.py`. Where a status here disagrees with a
change spec, this document is wrong and should be fixed in the same commit.

Status words mean exactly one thing each:

| Status | Meaning |
|---|---|
| **LIVE** | In the repo, exercised by the suite, and observed working in the real surface. |
| **PARTIAL** | Built and running, with named gaps that are not subtle. |
| **PROPOSED** | Design written, no code. Do not describe it as working. |
| **NOT BUILT** | Named because the plan needs it; nothing exists. |

The suite is **686 tests** (`pytest -q`); the authoritative count line lives in
`docs/spec.md` §13.

---

## 1. What the product is

A Hermes plugin that lets the agent itself take a **walk**, **daydream**, **dream**,
or **doomscroll**. A state is a bounded change to behaviour, not a place: it shapes the
next replies, decides what residue the agent carries afterwards, and — only when the
entry asks with `block: true` — restricts which tools may run.

Two audiences, deliberately separated:

- **The model** receives bounded material and a directive in its own turn, as text.
- **The person** receives a picture with no words on it. BR-5 forbids text on the
  card; the frame is the only human surface a state has.

No model calls and no scoring sit on the state or rendering path. Entry, exit, expiry,
tool restoration and rendering are all deterministic and clock-driven.

The public surface is small and counted: **one tool** (`state`, 12 actions: `enter`,
`exit`, `status`, `list`, `watch`, `card`, `image`, `walks`, `walk_new`, `walk_del`,
`break`, `mood`), **8 hooks**, and the slash commands `/walk`, `/daydream`,
`/doomscroll`, `/dream`, `/return`, `/state`, `/states`, `/note`, `/watch`, `/break`,
`/mood`, `/spark`, `/keep`, `/again`.

---

## 2. System shape

```
Hermes runtime
  │  pre_llm_call ────────► engine.tick()  ──► injected [STATE: …] block
  │  pre_tool_call ───────► engine.policy(tool) ──► block | None        (opt-in)
  │  post_tool_call ──────► work signal (calls, failures)
  │  transform_llm_output ► journal the reply, append the state marker
  │  on_session_* ────────► release prepared material, log named failures
  ▼
core/engine.py  ── the one owner of state
  ├── core/states.py        four state definitions: minutes, turns, cadence, tools,
  │                         directive, contract, feeds, restart
  ├── core/options.py       block / allow parsing, refusal of allow without block
  ├── core/walks.py         WordNet steps: wander, outer, named edge
  ├── core/social.py        doomscroll feed, cached, no model calls
  ├── core/photographs.py   stored memories for daydream/dream
  ├── core/mood.py          /mood, reported never inferred
  ├── core/storage.py       one state file per profile, atomic writes
  └── core/runtime.py       /spark candidate binding (session-scoped, counts only)
         │
         ▼
core/surfaces.py  ── the only renderer
  ├── card(state)           chat card, 44×12, no words (BR-5)
  ├── art(cols,rows,…)      frames → cells → ramp, percentiles, dither, floor
  ├── takeover()            tty full-screen
  └── snapshot_path()       PNG for proportional-font clients
         │
         ├── dashboard/plugin_api.py   GET /state?cols=&rows=&fit=  (desktop pane)
         ├── dashboard/projection.py   grid negotiation, tools_of(), FORBIDDEN keys
         └── desktop/plugin.js         five contributions + ResizeObserver

art pipeline (bake time only; three.js never runs in the client)
  data/meshy/pack/**  ──►  tools/scene.html  ──►  headless Chromium  ──►
  three_frames*/<state>/f000..f007.png  ──►  surfaces.art()  ──►  cell grid
```

---

## 3. Components and status

| Component | Role | Status | Evidence |
|---|---|---|---|
| `__init__.py` | manifest surface: the `state` tool (12 actions), 8 hooks, commands | **LIVE** | `plugin.yaml`, `hermes plugins doctor antemuse` |
| `core/engine.py` | state lifecycle, ticks, policy, journal, residue, origin | **LIVE** | `tests/test_states.py`, `test_plugin_api.py`; live in this session |
| `core/states.py` | the four definitions | **LIVE** | durations, turns, cadences pinned by tests |
| `core/options.py` | `block` / `allow`, refusal of `allow` without `block` | **LIVE** | `enter(..., block=True)` verified against the engine |
| `core/walks.py` | WordNet 117,659 synsets; `wander`, `outer`, named edges | **LIVE** | `tests/test_walks.py` (FLAKE-1 narrowed, see §10) |
| `core/social.py` | doomscroll feed | **LIVE** | exercised through `tests/test_sources.py` |
| `core/photographs.py` | stored memories for daydream/dream | **LIVE** | `tests/test_photographs.py` |
| `core/mood.py` | `/mood`, strain arithmetic | **LIVE** | `tests/test_mood.py` |
| `core/storage.py` | atomic state file, caches | **LIVE** | `tests/test_manifest.py` |
| `core/runtime.py` | `/spark` candidate binding; person gets counts, never candidates | **LIVE** | `tests/test_runtime.py` |
| `core/collider.py`, `collision.py` | concept collision + collision boundary | **LIVE** | `tests/test_collider.py`, `test_collision.py` |
| `core/selection.py` | candidate selection scores | **LIVE (records only)** | no quality claim anywhere |
| `core/surfaces.py` | card, art, takeover, PNG | **LIVE** | `tests/test_surfaces.py` |
| `dashboard/plugin_api.py` | `/state` with grid negotiation and frame index | **LIVE** | app returns 116×74 filling 700×746 |
| `dashboard/projection.py` | grid clamps, `tools_of()`, `FORBIDDEN` | **LIVE** | `tests/test_plugin_api.py` |
| `desktop/plugin.js` | pane, chip, page, nav, watch | **LIVE** | harness 9 properties; verified in the app |
| `tools/scene.html` + `render_three.py` | scenes and bakes | **LIVE** | 32 pane + 32 card frames per pass |
| `tools/glb_mesh.js` | hand-written GLB reader | **LIVE** | positions/normals/indices only |
| `tools/gen_pack.py` | Meshy submit/fill/grab/refine | **LIVE** | 50 assets, append-only ledger |
| `tools/pane_proof.py`, `pane_gif.py` | judge the four panes without a live state | **LIVE** | `/tmp/panes/sheet.png` |
| `tools/spec_audit.py` | spec↔repo status and count drift | **LIVE** | 0 drift, wired into tests |
| `evaluation/*` | shards, metrics, statistics, report | **PARTIAL** | records, not results — no judge |
| `core/tui.py`, `panel.py` | terminal takeover and panel | **LIVE** | `tests/test_tui.py`, `test_panel.py` |
| `core/presenter.py` | reply decoration | **LIVE** | `tests/test_presenter.py` |

---

## 4. State lifecycle — LIVE

1. **Enter** — `/walk`, `/daydream`, `/doomscroll`, `/dream`, or the `state` tool.
   `enter(…, block=False, allow=None)` by default: an aside does not cut the tool chain.
2. **Inject** — each turn, `pre_llm_call` returns `[STATE: WALKING · N min left ·
   N turn(s)]`, the directive, and one tool sentence, all read from the *same*
   `_effective_tools()` decision the hook enforces. They cannot drift.
3. **Tick** — minutes and turns decrement; cadence decides when material is due
   (walk 9 s, daydream 10 s, doomscroll 6 s, dream 40 s).
4. **Material** — `feeds: False` for walk (it supplies nothing); daydream/doomscroll/
   dream feed bounded material.
5. **End** — expiry, turn exhaustion, `/return`, or `/break` into another state.
6. **Account** — `state-return-report` builds three lines from the journal window and
   injects `[YOU JUST CAME BACK …]`; residue keeps 3, journal keeps 60.
7. **Restart** — after a walk the next step is forced to differ (`restart: True`).

Tool policy, the one thing that changed today: **default free** for all four states;
`block: true` enforces the state's own list; `allow: [...]` narrows and is refused
without `block` rather than silently ignored.

---

## 5. Surfaces

| Surface | What it shows | Grid | Status |
|---|---|---|---|
| Chat card | one picture, no words | 44 × 12 | **LIVE**; ink 10–19 % |
| Terminal takeover | full-screen frame + state strip | terminal size | **LIVE** |
| Desktop pane | the picture at pane size, moving | negotiated: 116 × 74 in a 700 × 746 pane | **LIVE**, verified in the app |
| PNG snapshot | same card, for proportional fonts | card | **LIVE** |

The pane contract: `GET /state?cols=&rows=&fit=cover` → `art()` with `fit=cover`,
`pane=True`, dither on, floor 0.06; the client derives font size from the grid that
came back and sizes each cell at `0.6 × 1.0`. `frame_index()` picks the baked frame
from the wall clock at a per-state rate; the pane polls at 0.9 s, under the slowest
hold (4 s), so no frame is skipped.

**What the person sees is never candidate text.** `dashboard/projection.py` holds a
`FORBIDDEN` key tuple asserted by a test: the pane payload carries counts, identifiers
and the picture, nothing that was generated for the model.

---

## 6. Art pipeline — LIVE, composition PARTIAL

- **Assets.** 50 Meshy assets / 302 credits in `data/meshy/pack/`, manifested with
  prompt, task id, credits, sha256, triangles (or px). Style contract: geometric,
  futuristic, abstract, cyberpunk, *not analogous to the current world*, from classical
  mathematics. No furniture, devices, people or lettering.
- **Scenes.** `tools/scene.html` builds a scene per state from a seeded PRNG, loads
  GLBs through `glb_mesh.js`, normalises each mesh to a stated longest side and
  recentres it on its own bounding box.
- **Wireframe, not shading.** A shaded low-poly solid collapses into one value band
  after quantisation to eight glyphs; `wire()` draws the same mesh as transparent line
  structures with one bright subject (0.8–0.85) and everything else 0.18–0.42.
- **Bake.** `render_three.py --square` → `three_frames_pane/<state>/f000..f007.png` at
  1100 × 1100; bare state names → `three_frames/` at 1600 × 420 for the card. The bake
  refuses to run against a dead preview server and verifies every screenshot exists —
  a silent no-op bake is a failure, not a fast bake.
- **Quantise.** Percentile stretch per frame, ordered 4 × 4 dither, and a black floor:
  below 0.06 a cell is empty, because a dither of a flat black field is graph paper,
  not texture.

Measured at 116 × 74: **walk 41 %, daydream 28 %, doomscroll 18 %, dream 35 %** ink.
`walk` and `dream` read well; **`doomscroll` is the open composition** — a five-plate
corridor whose subject sits high and small; `daydream` is close to right after
switching its second form to a möbius ribbon.

---

## 7. Data and storage

| Path | Holds | Cap |
|---|---|---|
| `~/.hermes/plugin-data/antemuse/state.json` | active state, journal, residue, mood, counters | journal 60, residue 3 |
| `…/three_frames/<state>/` | card frames, 1600 × 420 | 8 per state |
| `…/three_frames_pane/<state>/` | pane frames, 1100 × 1100 | 8 per state |
| `data/meshy/pack/` | assets + `manifest.json` + append-only `ledger.jsonl` | 50 assets |
| `evaluation/shards/`, `evaluation/results/` | frozen shard manifests, run records | write-once |

Writes are atomic; missing material produces a **named failure event**, never invented
content, and never a procedural fallback diagram.

---

## 8. Evaluation — PARTIAL by design

Path A (does any of this improve anything?) is deliberately unstarted:

- **Shard** `73a00871…` frozen over 2 tasks × 2 models × conditions A–F, write-once,
  drift caught by re-hashing the fixture; run to `complete: true, 24/24 cells,
  0 duplicates`. Conditions A baseline, B creative, C best-of-N + selector, D
  deterministic material, E plain branches, F branches + selection + synthesis. G not
  implemented.
- **No judge.** These are records, not a quality result. Runtime selection scores are
  not evidence, and a pilot is not a result.
- **Missing for a real result:** a judge, a blind comparison, a protected held-out set,
  and ≥2,000 provenance-backed samples. Pseudo-label self-training and unlabeled crawls
  are not improvement evidence.

---

## 9. Desktop integration — LIVE

Five contributions from `desktop/plugin.js`, all asserted by the jsdom harness
(`tools/desktop_harness/mount.mjs`, 9 properties): `state` (pane), `chip` (status),
`page` (`/antemuse` route), `nav` (sidebar entry), `watch` (poller).

A pane needs a **route**, not just a dock: registering only a dock made the host adopt
the pane as an inactive tab in the right rail with a 0 × 0 box. That was a real defect,
fixed and recorded.

---

## 10. Known defects and limits

| Item | Status |
|---|---|
| `doomscroll` composition reads as a small bright cluster | **open** — needs an eye, not another parameter |
| `daydream` two solids | improved (mass + möbius ribbon); still `PARTIAL` |
| One hue per state, HUD fade, colour/crop/scope gate | **NOT BUILT** |
| `scene3d-renderer` (Python z-buffer instead of Chromium) | **PROPOSED and conflicting** — the bake pipeline is what ships; one of the two must yield |
| FLAKE-1 `test_outer_hops_are_farther_than_wander_hops` | narrowed, not eliminated (samples n=64) |
| `/spark` is not gated by state | accepts, unresolved |
| Slash flags such as `/daydream --block` | **NOT BUILT** — no command surface carries them yet |
| Meshy MCP auth | 401: the CLI OAuth token is not a developer key. CLI path works and is what the pack used |

---

## 11. Constraints that must not change

- Four-state lifecycle, durations, turn budgets, cadences, directives, contracts,
  residue labels, journal 60, residue 3, two-turn decay, `/return`, `CONTROL_TOOLS`.
- Entry, exit, expiry, tool restoration and rendering never require a model call.
- No words on the human card (BR-5); no candidate text on any human surface.
- No invented fallback content: missing sources raise named failures.
- No creative-improvement claim, no default-on method, no always-on layer.
- One renderer: Python owns the glyphs, JavaScript displays text, three.js runs at bake
  time only.

---

## 12. Decision queue

1. **`doomscroll` direction** — nearer/fewer plates, or a face-on slab wall filling the
   pane.
2. **`scene3d-renderer`** — retire it in favour of the bake pipeline, or fund the
   Python renderer and retire the bakes.
3. **`state-evidence-task-bank`** — approve the data layer or leave it a draft.

---

## 13. Where the plan goes next

1. Finish `doomscroll` (blocked on decision 1).
2. Colour and HUD work to close `immersive-visuals` (`PARTIAL` → `LIVE`).
3. `scenes-per-surface`: per-surface grading, clock, dual scoring, 4:5 postcards.
4. Path A: judge, blind comparison, protected set — the only route to a claim.
