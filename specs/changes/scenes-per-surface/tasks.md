# Tasks: scenes-per-surface

Dependency ordered. Each task is independently verifiable and names its check.
`T7` is the carried-over item from `state-return-report`.

## T0 — origin binding  **done (2026-11-06)**
`core/engine.py::enter` records `{session_id, platform, project}`; artifacts
resolve to `<project>/.antemuse/` when `ANTEMUSE_STATES_HOME` is unset; no module
under `core/` may reference a channel or a send call.
**Check:** entry from session A then `stop()` in session B produces nothing in B;
a grep test asserts `core/` contains no `chat_id`, `thread_id`, or send API;
artifact path follows the project root.

Implemented: `enter()` records `origin: {session_id, platform, project}`;
`stop(session_id)` withholds the account from any other session (it stays in the
residue for the one that started it); `storage.project_root()` finds the nearest
`.git` ancestor and `project_dir()` gives `<root>/.antemuse`, which now receives
the walk cursor and the card. Three tests plus the grep test.

Two known gaps, recorded rather than hidden: a state entered by a bare slash
command *before any turn* has no `session_id` yet (so nothing is withheld), and
`project` follows the process cwd at entry, not a per-session directory.

## T1 — motion profiles
`core/realimagery.py`: replace `HOLD_S`/`FADE_S` with
`MOTION = {state: {hold, fade, kind}}`; `frame()` takes the profile from the
state key; implement `kind` in `cut`, `drift`, `push` terms.
**Check:** `frame("doomscroll", …)` at consecutive seconds changes frame index
without any blended output; `frame("dream", …)` crosses exactly one dissolve in
20 s. New `tests/test_realimagery.py::test_motion_profiles`.

## T2 — progress grade
`core/realimagery.py`: `grade(cells, state, g)` applying exposure, warmth, and
veil per D2, applied to 8-bit cell values before `to_rows`.
**Check:** walk at `g=0` vs `g=0.9` differs in mean luminance ≥ 12; doomscroll
grade is flat within 2. Test asserts the numbers, not the vibes.

## T3 — dual scoring
`tools/gen_frames.py --score` and `core/realimagery.py::score(path, target)`;
sidecar `<data>/real/scores.json`.
**Check:** the known-bad doomscroll frame (`f002`, phone on a pale wall) is
ranked below a face-lit frame for the terminal target while possibly ranking
above it for chat — the test asserts the two rankings *disagree*, which is the
point of having both.

## T4 — postcard
`core/surfaces.py::postcard(state, index=None)` → 4:5 720×900 PNG under
`<data>/postcards/`; `state` tool `action="image"` returns the postcard for
image-capable platforms and the wide frame for others.
**Check:** aspect within 1 px of 4:5; no alphanumeric text in the file's caption
path; `tests/test_surfaces.py::test_postcard_geometry`.

## T5 — chat emission
Entry response and `stop()` result append `MEDIA:<postcard>` for image-capable
profiles; ticker sets `pending_postcard` for states > 15 min at the halfway
point; `engine.inject()` surfaces it once and clears it.
**Check:** `/daydream` produces exactly one image *in the session that started
it*; a 30-minute dream produces entry + midpoint + resolution = 3 there and zero
elsewhere; a midpoint recorded for session A is dropped, not delivered, when
session B asks next (R10).

## T6 — retire ASCII art for image profiles
`surfaces.card()` untouched for `text`/terminal; chat profiles stop emitting the
`three_frames` ASCII block.
**Check:** existing `test_surfaces.py` pictures-only assertions still pass;
`card()` output for `discord` contains no art rows.

## T7 — walk accounts name the relation
`core/engine.py::_account`: trail entries carry `[relation]` for walk steps,
capped at five heads.
**Check:** the `state-return-report` acceptance case 1 gains `[hyponym]`-style
brackets; all six original criteria still pass. Update
`specs/changes/state-return-report/spec.md` open question to "resolved in
scenes-per-surface T7".

## T8 — docs, version, commit
README: per-surface table (terminal continuous / chat postcard / text record),
motion table, scoring note. `plugin.yaml` → 1.0.0. `.gitignore`: `node_modules/`,
`real/`, `postcards/`.
**Check:** fresh clone renders nothing without data and does not crash.

## Sequencing notes

- T1–T3 are pure and can be done in any order after T1.
- T4 depends on T3 only for choosing which frame becomes the postcard.
- T5 depends on T4.
- T6 depends on T5 being wired, so a chat surface always has something to show.
- T0 comes first: every later task inherits its origin rules.
- T7 is independent of all of it and can ship first if T0 is not yet in place.
