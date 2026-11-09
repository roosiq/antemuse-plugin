# Tasks — submission packaging

Order matters: assets must be committed before the pin, and the pin before the
catalog PR.

| # | task | owner | blocked by | verification |
|---|---|---|---|---|
| P1 | `tools/make_screenshots.py` renders takeover, chat card, return account, refusal, banner | agent | — | script runs twice with identical bytes for the same inputs |
| P2 | Commit `docs/screenshots/*.png` (5 files) | agent | P1 | `git ls-files docs/screenshots` lists them; each opens at its stated size |
| P3 | Freeze commit, run the full gate there | agent | P2 | 906 passed/1 skipped · validate 16/16 · doctor 1 tool, 8 hooks |
| P4 | Regenerate the catalog entry at the frozen pin with `image:` and `screenshots:` URLs | agent | P3 | `tools/catalog_entry.py --check` passes; URLs contain the pin |
| P5 | Public repo and push | Ryan | `gh auth login` | clone in a clean dir; pin present |
| P6 | Open the catalog PR | agent | P5, P4 | one added file; CI catalog check green |
| P7 | Demo take, post on X | Ryan + agent | — | `ffprobe` duration; post is public and tags `@NousResearch` |
| P8 | Submit the form | Ryan | P6, P7 | confirmation captured |

## Must not change

- `plugin.yaml` identity fields other than the ones already added in the packaging pass.
- Any file under `core/` that the states depend on.
- The demo's claims: no creativity claim, no measured-outcome claim.
