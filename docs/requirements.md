# Antemuse plugin — operating requirements

Status: draft for review. Amended 2026-11-07 to record the approved two-layer
contract. The behavioural contract is in `docs/spec.md` and the operator
instructions are in `README.md`.

Document authority:

- `docs/brd.md` owns business intent and Ryan's quoted requirements. It wins
  where the two business documents disagree about intent.
- This document owns operating detail and BR-to-implementation traceability:
  users, distribution, constraints, risks, release criteria, and open decisions.
- `docs/spec.md` owns shipped behaviour and implementation evidence. A business
  requirement is not a claim that its implementation exists.
- `specs/changes/creative-state-evidence/spec.md` governs the bounded
  exploration work approved on 2026-11-07. It is the authority for the
  two-layer contract and for BR-15.

Derived from existing artifacts — `docs/brd.md`, `docs/brand.md`, `docs/spec.md`,
`README.md`, `../docs/antemuse-family-spec.md`, and recorded marketplace research.
Nothing here invents market data, revenue, or targets; items without a source are
marked **OPEN** and need Ryan's decision.

Version described: `0.9.0`. Owner: Ryan Cook. Scope: the Hermes plugin at
`plugin/` only — not the sites, the lab, or the model work.

---

## 1. Problem and opportunity

An LLM turn is single-path: the model produces one coherent continuation, and the
person receives it. That is an interaction pattern, not an intelligence limit —
there is no built-in move to step away, change frame, or come back different.

Antemuse's bet is that a small, bounded change of *state* is worth more than
another prompt template. The agent keeps working (or doesn't, by design), the
person receives imagery rather than a wall of explanatory text, and the state
ends with an account.

Market opportunity, as recorded on 2026-11-04 (not re-verified here):

- the catalog had 976 entries;
- searches for `ideation`, `brainstorm`, and `divergent` returned 0 results;
- the catalog validator hard-codes nine categories (desktop, memory, platform,
  web, tools, voice, automation, models, general), so cognition plugins land in
  `general` or `memory`.

That is a discoverability gap, not proof of demand. **Demand is unmeasured.**

## 2. Product thesis

Four commitments define the product and constrain every business decision:

1. **A state is a bounded change to behaviour, not a place.** Tools, directive,
   contract, residue.
2. **The base state lifecycle is deterministic.** Entry, tick, expiry, tool
   restoration, and rendering resolve without inference. Optional exploration
   may make bounded model calls with measured cost, but never on the lifecycle
   path.
3. **The agent and the person share the state.** The person gets the experience;
   the model gets the content.
4. **No invented material.** Missing corpora, dead feeds, and absent memories are
   named, never filled.

Business consequence: the base experience has bounded marginal cost and no
model dependency on the lifecycle path, so it can run offline and make no
accuracy claims. Optional exploration is opt-in, disabled by default, and
carries measured cost. Base runtime risk is behavioural; promotion risk is
statistical, and any improvement claim is gated on protected comparative
evaluation (BR-15).

## 3. Users and jobs to be done

| User | Situation | Job | What success feels like |
|---|---|---|---|
| **Agent operator** (primary) | long working sessions, repeated stalls | "give the agent a different frame without stopping the work" | the work continues; the return is a different first step, not a summary |
| **Curious marketplace browser** | browsing plugins, low intent | "show me something I have not seen in a chat window" | installs in under a minute; `/walk` is visibly different from a prompt |
| **Peer / collaborator** | watching someone else's agent | "let me see what the agent is doing without reading its prose" | the takeover is legible as a place, with no tutorial needed |
| **Privacy-sensitive user** | personal memories on disk | "know what this reads and where it goes" | it reads local files, sends nothing, and says so |

The primary user is the operator who already runs Hermes daily. The plugin is
not aimed at people who have never used an agent.

## 4. Value proposition

Brand sentence, used in the README and the catalog listing only:

> Antemuse gives the agent somewhere to think, and you something to watch.

Differentiators, in business terms:

- **Bounded base cost.** The state lifecycle makes no model calls; a state costs
  a short injection (~109 tokens for a walk, recorded measurement) and nothing
  else. Optional exploration is opt-in and its cost is measured per run.
- **Reversible by construction.** States expire on minutes and turns; `/return`
  always works; the escape hatch is exempt from every block.
- **Observable, not introspective.** The person sees imagery and operations, not
  a claimed view of hidden reasoning.
- **Operator-controlled and quiet.** No telemetry, no account, no send API.
  Doomscroll fetches public feeds. Image generation calls the configured
  `SD_SERVER`, which defaults to an operator-controlled tailnet GPU host; the
  state-control and corpus mechanisms themselves make no model calls.
- **Evidence-gated.** No method is default-on or described as an improvement
  before protected comparative evaluation (BR-15).

## 5. Objectives and success measures

Objectives, in priority order:

1. **Adoption:** operators enable it and keep it enabled.
2. **Use:** states are entered without being demo-only, and breaks are accepted
   rather than ignored.
3. **Safety:** no report of an agent stuck in a state it cannot leave.
4. **Legibility:** a newcomer can explain what a state is after one run.
5. **Distribution:** it is findable under an honest category.
6. **Evidence:** any improvement claim is backed by protected comparative
   evaluation, not by runtime scores or test counts.

Measurement approach (no targets set — **OPEN**):

| Measure | How it would be observed | Target |
|---|---|---|
| Enablement | `hermes plugins list` / config presence | OPEN |
| Repeat use | states entered per active week | OPEN |
| Break acceptance | offer line shown by itself vs a state entered on purpose | OPEN |
| Completion | states ended by clock/quit vs abandoned mid-turn | OPEN |
| Incidents | reported lockouts or lost residue | 0 (a defect, not a metric) |
| Discoverability | catalog search position for "cognition", "walk", "creativity" | OPEN |
| Improvement | protected comparative evaluation per the governing spec | OPEN |

Do not substitute test counts or spec coverage for these; they measure the build,
not business adoption or creative-quality evidence.

## 6. Scope

**In scope for 0.9.x**

- five states: walk, daydream, doomscroll, unstuck, dream;
- the recommendation line and mood reporting (both now `state` tool actions);
- walks as user-editable data (WordNet and manual graphs);
- terminal takeover, chat card, text record, PNG card;
- deterministic material from WordNet, FrameNet, local memories, public feeds;
- one `state` tool and eleven commands.

**Implemented at the library level, not runtime-wired** (approved 2026-11-07;
see `specs/changes/creative-state-evidence/spec.md`):

- `evaluation/` — evaluation controls and harness;
- `core/collider.py` — Collider source strategy;
- `core/collision.py` — collision mechanics;
- `core/llm.py` — bounded auxiliary LLM calls;
- `core/orchestrator.py` — run orchestration;
- `core/selection.py` — selection aids (not improvement evidence);
- `core/feedback.py` — human feedback plumbing;
- `core/presenter.py` — prepared-artifact presentation;
- `data/collider/` — real Open Collider generated examples with attribution.

These modules exist and are controller-verified at the library level. They are
**not wired into runtime as a command**: `spark` and `keep` exist as tool actions, and no feedback
command, no auxiliary hook, and no runtime injection exists in the shipped
plugin. No creative-quality improvement is claimed.

**Out of scope, explicitly**

- any creative-quality claim or promotion based on runtime scores or judging.
  Selection-only judging is permitted inside the experimental library, but it is
  not improvement evidence;
- model training or fine-tuning;
- the generative "creative cognition engine" proposal — recorded, not adopted
  (`../docs/research/creative-cognition-proposal.md`). The approved
  creative-state-evidence spec governs this bounded work instead;
- animation or post-and-edit in chat;
- multi-user or shared-session state;
- a browser dashboard (proposed only, in `specs/changes/scenes-per-surface/`);
- per-concept imagery, publishing, accounts, telemetry;
- default-on methods, always-on cognition, or autonomous background delivery.

## 7. Distribution, pricing, licensing

| Item | Position |
|---|---|
| Repo | `github.com/roosiq/antemuse` (verified remote); plugin lives at `plugin/`. Visibility **OPEN** — not verifiable from this session (no GitHub auth) |
| Install | symlink into `~/.hermes/plugins/antemuse`, then `hermes plugins enable antemuse` |
| Catalog category | No cognition slot exists. Verified category set: `desktop`, `memory`, `platform`, `web`, `tools`, `voice`, `automation`, `models`, `general`. `productivity` is **not** a valid category — the earlier brand note was wrong. Filing under `general` is the only honest fallback; a new category is a marketplace conversation. **OPEN** |
| Price | **OPEN** (current build has no gating or account; feed and image-generation networking is described in §8) |
| Licence | **OPEN** — the repo has no licence file; this blocks public distribution and any reuse claim. The Open Collider artifacts under `data/collider/` are CC BY 4.0 with attribution; that does not license the plugin itself |
| Support model | **OPEN** — self-serve docs today; response expectations undefined |

The licence gap is the most concrete blocker to listing publicly. Decide before
any catalog submission.

## 8. Constraints

- Requires Hermes `>=0.21.6` and Python packages `pillow>=10,<14`, `nltk>=3.8,<4`
  installed in the interpreter Hermes runs.
- Corpora (`wordnet`, `framenet_v17`) must exist locally under `~/nltk_data`;
  the plugin never downloads at runtime.
- State is profile-wide, not per-session; this is a product decision, not a
  limitation to fix casually.
- The plugin returns strings only; it may not name a channel or call a send API.
- The terminal's visual contract is text-free; the debug frame and model-facing
  text record are deliberate non-visual surfaces. The current note/join typing
  prompts are an unresolved deviation recorded in `docs/spec.md` §14.
- `tools/gen_frames.py` defaults to `http://100.82.186.41:8089`, an
  operator-controlled tailnet GPU host, not localhost. `SD_SERVER` overrides it.
  Whether this satisfies BR-7's same-machine wording is **OPEN**.
- Matrix and Telegram profiles exist in `core/surfaces.py`, but neither has been
  verified against a real client. Configured support is not validated support.
- Optional exploration is opt-in and disabled by default. It may make bounded
  model calls with measured cost, call, token, and time limits. It never runs on
  the lifecycle path (entry, exit, expiry, tool restoration, rendering).
- Runtime selection scores are not improvement evidence. Promotion requires
  protected comparative evaluation under the governing spec (BR-15).

## 9. Stakeholders and approval

| Role | Who | Authority |
|---|---|---|
| Owner / approver | Ryan Cook | product direction, pricing, licence, release |
| Implementation | Hermes agent sessions | code, tests, docs within an approved spec |
| Users | operators, peers | feedback; no gate |

Approval follows the workspace spec-driven policy: intent approval (gate 1) and
execution-plan approval (gate 2) for substantial changes. Tiny doc or copy edits
may use the fast lane. The creative-state-evidence spec and plan were approved
by Ryan on 2026-11-07.

## 10. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A state blocks tools and the agent cannot leave | low | high | `state` exempt from every block; `/return` tested; `settle()` preserves live state |
| Missing corpora make a state empty | medium | medium | `sources.ready()` refuses entry with the fix command |
| Behavioural surprise — work stops when a user expected it to continue | medium | medium | walk is ambient; directives say work continues; annotation marks every reply |
| Privacy discomfort — daydream reads `MEMORY.md`/`USER.md` | medium | medium/high | local-only, no telemetry, documented; consider a redaction or opt-out control (**OPEN**) |
| Feed breakage makes doomscroll thin | high | low | cached, source-named failure, never invented |
| Maintenance drag — renderer, fonts, three.js, corpora | medium | medium | prebuilt assets, text fallbacks, tests pin invariants not numbers |
| Brand confusion with the Antemuse sites | medium | low | plugin carries the brand undecorated; docs state the relationship |
| Category gap hides it in `general` | high | medium | accept `general` or raise the category gap upstream; **OPEN** — `productivity` is invalid |
| Overclaiming creativity | medium | high | no quality claims; evidence section in the spec records the nulls; BR-15 gates promotion |
| Exploration cost or latency overruns | medium | medium | opt-in, disabled by default, bounded call/token/time limits, measured cost |
| Generated artifacts mistaken for verified facts | medium | high | `verification_status=generated_example`; attribution and caveat in `data/collider/ATTRIBUTION.md` |

## 11. Assumptions

- Users run a modern terminal with truecolor; non-tty surfaces degrade to the
  card or the text record.
- A three-minute state is short enough to be acceptable inside a working turn.
- Operators accept profile-wide state (one state across sessions).
- Local corpora are present or can be installed with one documented command.
- The public feeds used by doomscroll stay reachable unauthenticated; if not,
  the state degrades honestly.
- Operators who enable exploration accept bounded auxiliary model calls with
  measured cost; operators who do not enable it see no change.

## 12. Release criteria

A release is shippable when:

- `hermes plugins doctor` passes with the declared tool and hooks;
- the full test suite passes in a clean environment, or every exception is a
  documented, separately owned defect such as FLAKE-1;
- README, SKILL, and spec describe the shipped behaviour, with no known
  contradiction left unflagged;
- no unresolved critical defect in the drift list (`docs/spec.md` §14);
- the licence and catalog metadata are decided, or the release is explicitly
  private;
- no method is described as an improvement without protected comparative
  evaluation (BR-15).

## 13. Open decisions

1. **Licence** — required before public listing.
2. **Price** — free, paid, or donation; no gating exists today.
3. **Category** — `general` is the only valid fallback today; `productivity` does
   not exist in the catalog. Propose a `cognition` category upstream, or accept
   `general` and say so plainly.
4. **Success targets** — the measures in §5 have no numbers.
5. **Privacy control** — should daydream be able to exclude certain memory
   entries from surfacing?
6. **Imagery locality** — does BR-7 require generation on the same machine, or is
   an operator-controlled tailnet GPU host sufficient? Proposed broader wording:
   “Real imagery, generated on operator-controlled infrastructure, with no
   per-image vendor service.”
7. **Exploration promotion** — which methods, if any, survive protected
   comparative evaluation and become eligible for opt-in promotion. **OPEN**;
   no method is promoted today.

The product boundary is settled for this document set: Antemuse remains the
ambient state plugin. The creative-cognition proposal is recorded, not adopted;
the approved creative-state-evidence spec governs the bounded exploration work.

---

## 14. Business-requirement traceability

Status describes the current `0.9.0` tree, not the aspiration. “Partial” means a
real implementation exists but a stated part of the BR is unmet or unverified.
Paths are relative to `plugin/`; test names point to the executable evidence.
The suite collects 564 tests. Final verification passed 563 tests with FLAKE-1
deselected, and the focused collision/orchestrator/adapter regressions passed 89
tests. The unrestricted run hit the documented stochastic FLAKE-1 case. Test
counts are build evidence, not business adoption or creative-quality evidence;
one green run is not proof of suite stability.

| BR | Status | Spec section | Implementing path | Evidence or gap |
|---|---|---|---|---|
| **BR-1 — cognitive gap / discoverability** | **Partial** | `spec.md` §§2, 17 | `plugin.yaml`; install instructions in `README.md` | `hermes plugins doctor` verifies installation; `tests/test_manifest.py` verifies identity. Public catalog discovery is **not implemented**: no public listing, licence, or decided category. Demand remains unmeasured. |
| **BR-2 — imagery for the person, text for the model** | Implemented | `spec.md` §§6, 10 | `core/engine.py::inject`; `core/tui.py::imagery_frame`; `core/surfaces.py::card`, `record` | `tests/test_tui.py::test_the_stream_is_not_on_screen_but_reaches_the_agent`; `tests/test_surfaces.py::test_card_is_only_a_picture`, `test_record_is_dense_and_plain`. |
| **BR-3 — temporary states, not containers** | Implemented | `spec.md` §§1, 4, 5 | `core/states.py::STATES`; `core/engine.py::enter`, `tick`, `stop` | `tests/test_states.py` covers five states, turn/clock expiry, tool policy, and return. |
| **BR-4 — real corpus material** | Implemented | `spec.md` §§8, 9 | `core/walks.py`; `core/sources.py`; `core/social.py` | `tests/test_walks.py`, `tests/test_sources.py`; historical corpus counts are recorded in `spec.md` §13. The stochastic outer/wander comparison is tracked separately as FLAKE-1. |
| **BR-5 — pictures and nothing else** | **Partial** | `spec.md` §§10.1–10.4, 14 | `core/tui.py`; `core/photographs.py`; `core/surfaces.py` | Wordless visual tests exist in `tests/test_tui.py`, `test_panel.py`, `test_photographs.py`, and `test_surfaces.py`. **Gap:** note/join entry currently displays a temporary text prompt and typed words in the takeover; owner decision recorded in `spec.md` §14. |
| **BR-6 — full-terminal artistic imagery and transitions** | Mechanics implemented; aesthetic success unmeasured | `spec.md` §§10.2–10.6, 13 | `core/tui.py`; `core/photographs.py`; `core/backdrop.py`; `tools/scene.html` | `tests/test_photographs.py::test_frames_are_full_size_and_wordless`, `test_changing_state_starts_a_dissolve`; `tests/test_tui.py::test_frame_fills_the_screen_without_overflowing`; recorded pty evidence in `spec.md` §13. No subjective quality measure is claimed. |
| **BR-7 — real imagery generated on this machine** | **Partial** | `spec.md` §§10.3, 14 | `tools/gen_frames.py`; `core/photographs.py` | Image rendering and terminal playback exist. **Same-machine generation is not the default:** `SD_SERVER` defaults to `http://100.82.186.41:8089`, a tailnet GPU host. Locality wording awaits Ryan. |
| **BR-8 — the person can watch and act** | Implemented | `spec.md` §§3.3, 10.2 | command registration in `__init__.py`; `core/tui.py::run`; `core/engine.py::record` | `tests/test_walk_map.py::test_person_step_joins_the_same_path`; `tests/test_panel.py::test_both_columns_carry_their_own_words_debug`; recorded live-key evidence in `spec.md` §13. |
| **BR-9 — surface-specific output** | **Partial** | `spec.md` §10 | `core/tui.py`; `core/panel.py`; `core/surfaces.py` | `tests/test_surfaces.py`, `test_panel.py`, `test_tui.py` cover terminal, chat, text, and PNG projections. **Gap:** Matrix and Telegram profiles are unverified against real clients. |
| **BR-10 — answer where the action started** | Implemented | `spec.md` §§5, 11, 12 | return-only handlers in `__init__.py`; origin/session handling in `core/engine.py`; `core/storage.py` | `tests/test_manifest.py::test_nothing_in_core_names_a_channel_or_sends_anything`; `tests/test_states.py::test_a_state_records_where_it_was_started`, `test_another_session_cannot_collect_the_account`, `test_only_this_session_can_collect_it`. |
| **BR-11 — return with an account** | Implemented | `spec.md` §§5.3, 6.4 | `core/engine.py::stop`, `_account`, `inject` | `tests/test_report.py` covers stop, expiry, residue, empty states, and the next-turn account. |
| **BR-12 — operator-extensible walks** | Implemented | `spec.md` §8 | `core/walks.py::GraphWalk`, `save`, `remove`; `walk_new` / `walk_del` in `__init__.py` | `tests/test_walks.py` covers built-ins, manual graphs, persistence, cursors, relation policy, and deletion boundaries. |
| **BR-13 — Antemuse, undecorated** | Implemented | `spec.md` §§1, 2 | `plugin.yaml`; `__init__.py`; `SKILL.md`; `docs/brand.md` | `tests/test_manifest.py::test_manifest_name_is_the_brand`, `test_the_registered_skill_is_the_brand`, `test_no_retired_name_appears_anywhere`. |
| **BR-14 — no clichéd explanation of connections** | Implemented | `spec.md` §§6, 10 | wordless visual paths in `core/tui.py`, `core/photographs.py`, `core/surfaces.py`; model-only material in `core/engine.py` | `tests/test_walk_map.py::test_bare_map_has_no_instrumentation`; `tests/test_surfaces.py::test_card_is_only_a_picture`; `tests/test_tui.py::test_active_frame_is_pictures_only`. |
| **BR-15 — evidence-gated improvement** | **Not implemented at runtime; library/evaluation controls implemented** | `specs/changes/creative-state-evidence/spec.md` §§2, 7, 9 | `evaluation/`; `core/collider.py`; `core/collision.py`; `core/llm.py`; `core/orchestrator.py`; `core/selection.py`; `core/feedback.py`; `core/presenter.py`; `data/collider/` | Library and evaluation controls are implemented and controller-verified at the library level; final regression results are recorded in the task register. **Gap:** runtime registration/wiring has not happened; `spark`/`keep` exist only as tool actions with no evaluation behind them; no auxiliary hook or runtime injection exists; no protected comparative evaluation has been run; no creative-quality improvement is claimed. Runtime selection scores are not improvement evidence. |
