# Hackathon submission — readiness checklist

Evidence cut: 2026-11-08 15:27 EST, HEAD `c3f8ce3`, tree at `specs/changes/hackathon-submission/`.
Checked with the source-grounded preflight `hackathon_judge` (v0.2.1, 33 rules)
plus the official validator. The preflight is not official Nous judging.

## Hard blockers (red)

| # | rule | evidence | fix |
|---|---|---|---|
| 1 | PRE-01 public repo | `git remote -v` is **empty**; `gh auth status` → "The token in default is invalid" for `roosiq` | W0: re-auth, create public repo, push |
| 2 | CAT-13 disclosures | no Disclosures section in `README.md`; judge: "README lacks an obvious disclosure section" | W2 |
| 3 | License | no `LICENSE` file in the tree or in the sibling repos | W1 |
| 4 | HACK-01 catalog PR | no entry, no PR | W3 |
| 5 | HACK-02/03 demo | no video, no X post | W4/W5 |
| 6 | HACK-04 form | not submitted | W5 |

## Green (verified today)

| rule | evidence |
|---|---|
| PRE-02 loadable layout | `plugin.yaml` + `__init__.py` + `desktop/plugin.js` + `dashboard/manifest.json` |
| PRE-03 local validation | `hermes plugins validate . --install-deps --json` on a clean clone of `c3f8ce3`: manifest, requires_hermes, load, **capabilities match registrations**, config_schema, requires_env, dependency constraints, security scan (`safe`), **no core override**, **desktop surface** — all `ok: true`, `warnings: []` |
| CAT-06 capabilities match | same run: `"matches registrations"` |
| CAT-07 security scan | same run: `"safe"` |
| CAT-08 desktop SDK | same run: `"stays inside the plugin SDK surface"`; the judge's `tools/*.js` findings are the bundled three.js and the dev harness, neither loaded by `desktop/plugin.js` |
| CAT-09 no core override | same run: `"no runtime rebinds of Hermes core"`; judge flagged `dashboard/plugin_api.py:53` (`sys.modules[name] = module`), which is the plugin loading its **own** sibling modules under private names, and the validator accepts it |
| CAT-14 compatibility | `requires_hermes: ">=0.21.6"`, installed Hermes is `0.22.5`; floor is a SemVer floor, not a date |
| CAT-17 reviewable payloads | `git ls-files` has zero `.pyc`/`.pyo`/binaries/archives; `__pycache__/` is ignored; the judge's bytecode list is all untracked working-tree output |
| CAT-10 dependency bounds | `pillow>=10,<14`, `nltk>=3.8,<4` — bounded both ends, no newest-release floor |
| Reliability | 677 collected at `c3f8ce3`: **670 passed, 7 skipped in 8.5 s** on a clean clone (the 7 are the renderer tests, which skip without `npm ci`); `hermes plugins doctor` → 1 tool, 8 hooks. Run `npm ci` and repeat so no test is skipped at the pin |

## Amber (fix or accept with a decision)

| # | item | evidence | position |
|---|---|---|---|
| 7 | README drift | `README.md:75` "1 tool, 4 hooks"; 8 hooks register (`__init__.py:367–378`) | fix in W2; it is the polish criterion |
| 8 | Dirty tree | `tools/scene.html` modified, `data/meshy/` 2.1 MB untracked | keep out of the pin (W1) |
| 9 | Art scope | `immersive-visuals`, `scene3d-renderer`, `surface-repair` header all `proposed` | out of scope until 11-11 17:00 |
| 10 | Desktop pane | `desktop-surfaces` §7b: dock pane did not render in-app | not shown in the demo; takeover is the verified full-pane surface |
| 11 | Category | no `cognition` shelf; `productivity` invalid | `general`, decided |
| 12 | Version label | §19 reserves `1.0.0` for `scenes-per-surface` | `0.10.0` |
| 13 | Screenshot hosting | `.gitignore` has blanket `*.png` | add `!docs/screenshots/*.png`, verify with `git check-ignore -v` |
| 14 | Source-finding triage | judge heuristics: env reads (`core/panel.py:26`, `sources.py:30`, `storage.py:34/46`, `walks.py:46`), network (`social.py:42–43`, `sources.py:264–265`), subprocess (`tui.py:234`) | each is disclosed in W2; the validator scans them as safe, and none reads a credential store |

## Manual-only rules (no automated check exists)

CAT-01, CAT-04, CAT-05 (owner submission), CAT-15, CAT-16, CAT-18 (no
`browser_vault` backend), PRE-05 (maintainer review), QUALITY-01…05.

QUALITY-02 is the one a judge cannot take from source: the demo must exercise a
failure path, not only the happy path. W4's blocked-tool shot and an unavailable
feed during doomscroll cover it.
