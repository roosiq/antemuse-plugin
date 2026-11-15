# Release 0.11.0 — tasks

Change id: `release-0.11.0`
Source: `proposal.md`

Ordering matters: `scripts/release.sh` refuses a dirty tree, so C1–C3 must land as commits before S6.

## S0 · freeze

- [ ] Full suite green — `env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q` (last: 934 passed, 1 skipped)
- [ ] Harness green — `python3 tools/cockpit_harness.py` (26 checks)
- [ ] `git diff --stat` reviewed; every changed path explained by C1, C2 or C3, or reverted
- [ ] Scope frozen: nothing new enters the tree except fixes to what is already in it

## S1 · commit C1 — delivery

- [ ] `core/engine.py`, `core/sources.py`, `core/states.py`, `dashboard/plugin_api.py`, `__init__.py`
- [ ] `tests/test_state_delivery.py` + the five tests that encoded serve-only closure
- [ ] Revert `.antemuse/walk_cursor.json`; decide whether to untrack it
- [ ] Accept: `git show --stat` limited to delivery code and its tests; `pytest tests/test_state_delivery.py -q` passes

## S2 · commit C2 — desktop

- [ ] `desktop/plugin.js`, new pane/explore/hook tests, `tools/cockpit_harness.py`, `tools/cockpit_video.py`, `tools/e2e_states.py`
- [ ] Accept: `python3 tools/cockpit_harness.py` 26/26 on that commit

## S3 · commit C3 — docs and specs

- [ ] README, SKILL, TESTING, SECURITY, CONTRIBUTING, CHANGELOG
- [ ] **README factual fix** — delete the "units arrive one a second … a six-hop walk is served in
      about six seconds" and "an expiry says how much of the dose arrived" sentences; delivery is one
      unit per call and `expired` no longer exists
- [ ] `docs/design/` drawings (app-flow, states-context) and `specs/` (product, audit, delivery,
      experience, release)
- [ ] `.specify/` decision: commit or ignore
- [ ] Accept: `pytest tests/test_docs_current.py -q` passes; every drawing is referenced or removed

## S4 · listing copy

- [ ] Description leads with **new ideas for creative work**, mechanics second — copy is canonical in
      `specs/product/positioning.md`, not restated here
- [ ] `cognitive`, `creativity`, `brainstorm` each appear once — each returns 0 live results today
- [ ] `/explore` and the concept map are in the first paragraph
- [ ] `category: desktop` in `tools/catalog_entry.py` (was hardcoded `general`)
- [ ] `known_issues` names the two honest limits: CLI has no picture; cockpit is desktop-only
- [ ] Accept: `python3 tools/catalog_entry.py` then `--check` passes; each of
      `hermes plugins search cognitive|creativity|brainstorm` returns the entry

## S5 · examples

- [ ] `docs/examples/corpus/` checked in (one small text per situation, readable)
- [ ] `tools/examples.py` drives the real engine and writes `docs/EXAMPLES.md`; `--check` supported
- [ ] All eight examples generated, with `specs/product/examples.md` as the contract
- [ ] README carries examples 1, 2, 3, 8 and matches the generated file byte for byte
- [ ] Guards hold: no duplicate arrivals, no `random:*` seed, no empty arrival shown as material, no
      invented reply
- [ ] `Back:` captured from a real governed turn; otherwise the example is arrival-only and stays out
      of the README
- [ ] Blocked on: C1's duplicate-material fix (F10), or daydream examples refuse to generate

## S5b · stills

- [ ] `python3 tools/make_screenshots.py` (banner, return-account, blocked-tool)
- [ ] Capture `pane-walk.png` from the running app (manual; cannot be rendered)
- [ ] Add `cockpit-explore.png` and `states-table.png`
- [ ] Accept: each file < 400 KB and resolves 200 from `raw.githubusercontent.com` at the pinned sha
- [ ] Blocked on: gateway running the committed code

## S6 · cut the release

- [ ] `./scripts/release.sh 0.11.0`
- [ ] Accept: version in `plugin.yaml` and `__version__`; changelog section present; entry pinned to the code commit; three commits created

## S7 · prove the artefact

- [ ] `./scripts/build-release.sh`
- [ ] `hermes plugins validate . --install-deps`
- [ ] Install the tarball into a throwaway home; run `/walk`, `/explore`, `/return`
- [ ] Accept: validate passes; the account prints; `hermes plugins doctor` clean

## S8 · catalog PR

- [ ] Copy `plugin-catalog/antemuse.yaml` into the `hermes-agent` fork; open PR
- [ ] Both CI gates green (structural, pinned-source-validate)
- [ ] Merge, then verify the live page: new description, `desktop` shelf, one agent state in the README, cockpit still
- [ ] Accept: `hermes plugins search cognitive` returns the entry from the live catalog
- [ ] Blocked on: network and a GitHub token (owner or supervised run)

## Post-release

- [ ] Record the pinned sha and the release date in `CHANGELOG.md` (the generator does this)
- [ ] Update `specs/changes/state-experience/proposal.md` F8/F9 with what shipped vs deferred
- [ ] Next cycle starts at state-experience Phase 1 (T1, T2, T3, T8)
