# Hackathon submission — task register

Statuses: `[ ]` pending · `[~]` active · `[x]` verified · `[!]` blocked.
Owner: **A** = agent, **R** = Ryan (human gate). Est in minutes.

Deadline 2026-11-11 17:00 EST. Target submit Tue 11-10 18:00.

## Gate 0 — decisions and access

| id | task | owner | est | depends | verification |
|---|---|---|---|---|---|
| H00 | Keep repo private for now; do not create a public remote | R | — | — | decision recorded 2026-11-08 |
| H01 | Re-authenticate `gh` for `roosiq` (`gh auth login -h github.com`) | R | 5 | — | `gh auth status` shows a valid token |
| H02 | Decide public repo name and visibility when unblocking | R | 5 | H01 | `gh repo view --json visibility` |
| H03 | Decide X account for the demo post | R | 2 | — | handle named in `submission/notes.md` |

## Wave 1 — repository is reviewable (independent of H01/H02)

| id | task | owner | est | depends | verification |
|---|---|---|---|---|---|
| H10 | MIT `LICENSE` at repo root | A | 5 | — | `[x]` committed `00438b6` |
| H11 | `README` Disclosures section (network, memory reads, child process, dev tools, no credentials/telemetry/self-updater) | A | 30 | — | `[x]` committed `00438b6` |
| H12 | Fix README drift: "1 tool, 4 hooks" → 8; add clone install | A | 10 | — | `[x]` committed `00438b6` |
| H13 | `.gitignore`: allow `docs/screenshots/*.png`, exclude `data/meshy/` | A | 5 | — | `[x]` proven with `git add -n` |
| H14 | Capture 4 screenshots: takeover mid-walk, chat postcard, `/break` recommendation, blocked-tool refusal | A | 45 | freeze | PNGs under `docs/screenshots/`, committed at the pin |
| H15 | First-screen summary + screenshot in README | A | 20 | H14 | README renders the image at the pinned SHA |
| H16 | Confirm states-open-by-default text in README (`block: true`, `allow:`) matches the pin | A | 10 | — | `[x]` fixed in the freeze commit; `/daydream` no longer implies closed tools |

## Wave 2 — freeze and validate

| id | task | owner | est | depends | verification |
|---|---|---|---|---|---|
| H20 | Quiesce the concurrent art lane (uncommitted `core/surfaces.py`, `desktop/plugin.js`, `tools/*`, `dashboard/*`) — commit or stash, then stop | A+R | 15 | — | `git status --short` empty except declared exclusions |
| H21 | `npm ci` so renderer tests run instead of skip | A | 10 | H20 | 0 skipped |
| H22 | Full suite at the freeze commit | A | 10 | H21 | 677 passed, recorded in `docs/spec.md` §13 |
| H23 | `hermes plugins validate . --install-deps --json` at the freeze commit | A | 10 | H20 | 16/16 checks ok, `warnings: []` |
| H24 | `hermes plugins doctor .` | A | 5 | H20 | 1 tool, 8 hooks |
| H25 | Cut the freeze commit; record the 40-char SHA | A | 5 | H22–H24 | `git rev-parse HEAD` stored in `submission/pin.txt` |
| H26 | `docs/spec.md` §15 row for `hackathon-submission` | A | 10 | H25 | row names pin, PR, X URL, submit time |

## Wave 3 — catalog entry (blocked on H02)

| id | task | owner | est | depends | verification |
|---|---|---|---|---|---|
| H30 | Fill `antemuse.catalog.yaml`: real SHA, screenshots at pin, quoted version, category `general` | A | 15 | H14, H25 | YAML parses; SHA is 40 hex |
| H31 | Clone `NousResearch/hermes-agent`, add `plugin-catalog/antemuse.yaml`, push branch | A | 20 | H02, H30 | branch exists on the fork |
| H32 | Open the PR with description, surfaces used, rule-13 disclosures, screenshots | A | 20 | H31 | PR URL captured in `submission/` |
| H33 | Wait for catalog CI; fix what it reports | A | 60 | H32 | CI status + reviewer comments noted |

## Wave 4 — the demo

| id | task | owner | est | depends | verification |
|---|---|---|---|---|---|
| H40 | Rehearse the 8-shot run end to end, confirm every screen produces the intended line | A | 30 | H20 | rehearsal notes; no invented output |
| H46 | Caption/card generator (`tools/demo/overlays.py` + `beats.json`) | A | 40 | — | `[x]` rendered 9 cards; one composited and frame-checked |
| H47 | Human-pace typing driver (`tools/demo/human_type.py`) | A | 25 | — | `[x]` seeded typo corrected in a real tmux pane |
| H41 | Capture at 1280×720 via `tmux` + `xvfb-run` + `ffmpeg x11grab` | A | 60 | H40 | raw take ≥ 3 min, readable at phone size |
| H42 | Edit to ≤ 84 s with burned-in captions; hard cap 90 s | A | 60 | H41 | `ffprobe` duration < 90.0 |
| H43 | Phone-size legibility pass (watch at 390 px wide) | R | 10 | H42 | R signs off |
| H44 | Post on X, tag `@NousResearch`, link repo + catalog PR | R | 10 | H43, H32 | post URL captured with timestamp |
| H45 | Download/verify the video is public and playable logged out | A | 5 | H44 | public fetch of the post succeeds |

## Wave 5 — submit

| id | task | owner | est | depends | verification |
|---|---|---|---|---|---|
| H50 | Submit Typeform with catalog PR URL + X URL | R | 10 | H44 | confirmation captured |
| H51 | Record submission time UTC + EST and store confirmation outside the repo | A | 5 | H50 | `submission/confirmation.txt` |
| H52 | Post-submission: comment the X link on the catalog PR | A | 5 | H50 | comment visible on PR |

## Wave 6 — buffer (Wed 11-11, hard stop 15:00)

| id | task | owner | est | depends | verification |
|---|---|---|---|---|---|
| H60 | Repost/repair a failed X upload, or amend the PR if a maintainer asks | A+R | 30 | H50 | links resolve |

## Critical path

`H01 → H02 → H31 → H32 → H50`, and `H20 → H25 → H41 → H42 → H44 → H50`.
Everything else is parallel and can be done while the repo is still private.

## Not in this submission

`immersive-visuals`, `scene3d-renderer`, `surface-repair`, the desktop pane,
`cognition` category upstream, and any `1.0.0` version claim.
