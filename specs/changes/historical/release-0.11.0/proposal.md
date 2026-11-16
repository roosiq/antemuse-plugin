SUPERSEDED 2026-11-16 — this release plan shipped; see one-state-and-verdict.

# Release 0.11.0 — the listing catches up with the product

Change id: `release-0.11.0`
Status: **gate 1 — proposed, nothing released or committed**

## Why this release exists

Two things are true at once: the engine is materially better than the version the marketplace
serves, and the marketplace page describes a product that no longer exists.

- The tree carries the state-delivery fixes (final unit reaches the turn that spends it, failing
  sources end `failed` instead of claiming a dose, pane polls cannot complete a state, unstuck
  serves its direction) — none of it is committed.
- The live page renders the README **at the pinned sha `b19cca8`**, which still says five states,
  one-second pacing, and an `expired` ending. `/explore` and the cockpit are absent from the page
  entirely.
- The entry sits on `general` (119 entries, mixed with themes and telemetry) rather than `desktop`
  (409), and its card copy contains none of the words people search — `cognitive` and `creativity`
  return zero results marketplace-wide.

So this release is as much a *listing* release as a code release. The engine work is already done;
what remains is committing it honestly, refreshing the artefacts the page is generated from, and
moving the pin.

## Positioning — the product is an idea machine, and the copy says "state machine"

The listing currently opens with mechanics: "the agent takes a walk… a bounded change to how it
works, with a dose rather than a duration." That is what the thing *is made of*. What it is *for* is
new ideas, and every artefact a stranger sees has to say that first.

The position, the words, the card copy, the README opening and the voice rules now live in
**`specs/product/positioning.md`** — one copy, so the release cannot drift from the product record.
Release-specific acceptance is only this: `cognitive`, `creativity` and `brainstorm` each return the
entry in the live catalog, and each of those words appears exactly once in the description.

## Version

**0.11.0.** Not a patch: the dose accounting changed meaning (a unit is spent when shown, not when
fetched), a state can now end `failed`, and a pane poll can no longer end a state. Anyone who wrote
against `served >= dose` semantics is affected.

## What ships

Four commits, in this order. `scripts/release.sh` requires a clean tree, so this grouping is also
the sequence.

**C1 — the delivery fix and its tests.**
`core/engine.py`, `core/sources.py`, `core/states.py`, `dashboard/plugin_api.py`, `__init__.py`,
`tests/test_state_delivery.py` (new), and the five tests that encoded serve-only closure
(`test_semantic_states.py`, `test_moves_ledger.py`, `test_states.py`, `test_runtime.py`,
`test_session.py`, `test_command_surface.py`).

**C2 — the desktop half and its guards.**
`desktop/plugin.js`, `tests/test_cockpit_pane.py`, `tests/test_explore_state.py`,
`tests/test_explore_api.py`, `tests/test_hook_resilience.py` (all new), `tools/cockpit_harness.py`,
`tools/cockpit_video.py`, `tools/e2e_states.py`.

**C3 — docs, specs and the design drawings.**

C1 additionally carries the **duplicate-material fix** (F10 in `state-experience/proposal.md`): a
line already served by this state does not spend a unit, and a state that cannot produce distinct
material ends `dry` rather than claiming a full dose. Without it the examples guard refuses to
generate daydream.

C3 also carries two **stale-text fixes found while planning**: `tools/e2e_states.py` still explains
its `TURN_GAP = 1.1` as "delivery is paced by the clock (one unit a second)", which stopped being
true when delivery became one unit per call; and the README paragraph below.: the README still says "the units arrive one
a second from the moment the state exists, so a six-hop walk is served in about six seconds" and "an
expiry says how much of the dose arrived." Delivery is one unit per call and `expired` no longer
exists — the endings list was corrected earlier, this paragraph was not. A release would otherwise
re-publish the same false sentence under a new pin.
`README.md`, `SKILL.md`, `TESTING.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`,
`docs/design/` (app-flow, states-context, findings), `specs/` (state-audit, state-delivery,
state-experience, release-0.11.0), `.specify/`.

**C4 — the listing.**
`plugin.yaml`, `tools/catalog_entry.py` (category + description), `docs/screenshots/*`,
`plugin-catalog/antemuse.yaml` (generated at release time, never hand-edited).

Explicitly **not** in this release: state-experience Phase 1+ (T1–T3, T8–T11), the outcomes journal,
the tool-schema slimming, `transform_tool_result`, any new state, any pane redesign, the design-pass
changes, and the `machine-and-person` proposals.

## Preflight evidence (already run)

| Check | Result |
| --- | --- |
| `pytest tests/ -q` | 934 passed, 1 skipped (last full run after the schema fix) |
| `tools/changelog.py --check` | ok: section 0.10.44 |
| `tools/catalog_entry.py --check` | **FAILS** — manifest-derived fields do not match HEAD |
| `tools/make_screenshots.py --check` | **stale** — regenerated `return-account.png`, `blocked-tool.png` |
| `git status --porcelain` | **36 paths**, so `release.sh` will refuse until C1–C3 are committed |

Two oddities to resolve before committing, not after:

- `.antemuse/walk_cursor.json` is **tracked and modified**. It is runtime data from a machine, not
  source. Revert it in C1 and consider removing it from tracking.
- `.specify/` is untracked scaffolding from Spec Kit. Decide once: commit it as project framework,
  or add it to `.gitignore`. Silence is the only wrong option.

## Examples

Eight scenarios, a four-line format, and the guards that keep them from lying are specified in
**`specs/product/examples.md`**; `specs/product/states.md` says which state belongs to which
situation. The release's obligation is narrow:

- `tools/examples.py` generates `docs/EXAMPLES.md`; `--check` passes.
- `README.md` carries four of the eight (1, 2, 3, 8) and they match the generated file byte for byte.
- All four generator guards hold: no duplicate arrivals, no `random:*` seed, no empty arrival block
  presented as material, no invented reply.

Two things found while prototyping, both of which now block or shape the work:

- **`walk` serves no material by design** — its example shows the six-hop path and the reply, never
  "what arrived".
- **A repeated line spends a unit** (`state-experience` F10). Reproduced: `daydream` served the same
  pair in both slots and closed `complete`. Fixed in C1, or the generator refuses to emit it.

## Steps

**S0 · freeze and verify.** No code changes from here except fixes to what is in the tree.
```
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q
python3 tools/cockpit_harness.py
```
Accept: suite green, harness 26/26, `git diff --stat` reviewed and explained by C1–C3.

**S1 · commit C1.** `git add` the delivery files; revert `.antemuse/walk_cursor.json`; commit.
Accept: `git show --stat` touches only delivery code and its tests; `pytest tests/test_state_delivery.py -q` passes on the commit.

**S2 · commit C2.** Desktop half + harnesses. Accept: harness 26/26 on that commit.

**S3 · commit C3.** Docs, specs, drawings, `.specify` decision.
Accept: `pytest tests/test_docs_current.py -q` passes; every drawing in `docs/design/` is either
referenced by a doc or removed.

**S4 · the listing copy.** One pass over `plugin.yaml` + `tools/catalog_entry.py` so the generated
entry says what the product does:

- `plugin.yaml` description becomes the positioning paragraph above: **new ideas first**, mechanics
  second, `/explore` in the first paragraph, and `cognitive` / `creativity` / `brainstorm` each used
  once.
- `category: desktop` (valid shelf; 409 entries) instead of `general` — the shelf is where a UI
  plugin lives; the words are how it is found.
- `known_issues` gains the two things a stranger should know: the CLI has no picture, and the
  cockpit is desktop-only.
Accept: `python3 tools/catalog_entry.py --check` after regeneration; and each of
`hermes plugins search cognitive`, `creativity`, `brainstorm` returns the entry — all three return
nothing today.

**S5 · examples.** `python3 tools/examples.py` then `--check`; `docs/EXAMPLES.md` exists, every one of
the eight examples has a situation, a command, a verbatim arrival block and a reply, and the
generator's guards (duplicate material, `random:*` seed, empty arrivals) passed for all of them.
*Blocked on:* the duplicate-pair defect below — fix it in C1 or the daydream examples will refuse to
generate, which is the guard working as intended.

**S5b · stills.** `banner.png` and the account/blocked-tool stills are rendered by
`tools/make_screenshots.py`; `pane-walk.png` is captured from the running app. Add
`cockpit-explore.png` and `states-table.png` (the states-context drawing already exists).
Accept: every image is < 400 KB, referenced by the entry, and resolves 200 from `raw.githubusercontent.com`
at the pinned sha.
*Blocked on:* the gateway running the committed code — the pane still has to be captured from the app,
not mocked.

**S6 · cut it.**
```
./scripts/release.sh 0.11.0
```
Accept: three commits (`0.11.0: release`, `catalog entry for <sha>`, plus C1–C3), `plugin.yaml` and
`__version__` both `0.11.0`, changelog section present, entry pinned to the code commit.

**S7 · prove the artefact.**
```
./scripts/build-release.sh
hermes plugins validate . --install-deps
```
then install the tarball into a throwaway home and run a state:
```
ANTEMUSE_STATES_HOME=$(mktemp -d) hermes --ignore-user-config ... /walk
```
Accept: validate passes; an isolated install runs `/walk` and `/return` and prints the account;
`hermes plugins doctor` clean.

**S8 · the catalog PR.** Copy `plugin-catalog/antemuse.yaml` into the `hermes-agent` fork, open the
PR, wait for both CI gates (structural, pinned-source-validate), merge, then verify the live page:
new description, `desktop` shelf, cockpit still, README renders one agent state and four endings.
Accept: `https://hermes-agent.nousresearch.com/docs/plugins/antemuse` shows the new text, and
`hermes plugins search cognitive` returns the entry.
*Blocked on:* network + a GitHub token — I cannot open a PR from here, so this step is yours or a
supervised run.

## Risks

- **The capture step is the only real gate.** Pane and cockpit stills come from the running app; a
  release without them ships the same stale imagery. If the app cannot be run, ship the code and
  defer the stills — but say so in the entry rather than shipping a stale image silently.
- **`release.sh` will not tolerate a dirty tree**, and it regenerates the changelog from commit
  subjects. Commit subjects in C1–C3 therefore *are* the changelog; they must read as user-facing
  sentences, not as `fix`.
- **Category change is a one-line edit in a generator** that a reviewer may question. Supporting
  evidence: the product is two desktop panes; `general` is where themes and telemetry land.
- **The pin freezes the README.** Any README fix after S6 is invisible until the next release.

## Rollback

- Code: `git revert` the release commit; installed users keep 0.11.0 until they update, so the
  catalog pin is the real rollback surface.
- Catalog: a follow-up PR re-pinning `sha` to the previous release commit restores the old page
  within one merge; the entry is generated, so re-run `tools/catalog_entry.py` at the old commit
  rather than editing the YAML.

## Gate 1 — what I need from you

1. **Version**: 0.11.0 as proposed, or 0.10.45 to keep the minor line?
2. **`.specify/`**: commit as project framework, or ignore?
3. **S8**: do it yourself, or should I prepare the PR branch and hand you the exact command?
