# Submission packaging — what is still missing

Status: **proposed**. Owner: Ryan Cook. Scope: the external submission artifacts
and the in-repo assets they need. No runtime behaviour changes.

## Why

The packaging audit (`docs/audits/2026-11-09-packaging.md`) compared this tree
with 763 admitted catalog entries and eight approved plugins. Everything that can
be fixed from inside the repository is fixed. What remains is a short list of
artifacts that either need a human credential or need to be produced, and the
in-repo assets they depend on.

## Missing items

### M1 — Public repository at the pin

- **Blocked by:** `gh auth login -h github.com` (the stored `roosiq` token is
  invalid). Only Ryan can authenticate.
- **Do:** create `roosiq/antemuse-plugin` as public, push `main`, confirm the pin
  commit is present and cloneable without credentials.
- **Acceptance:** `git clone https://github.com/roosiq/antemuse-plugin` succeeds
  in a clean container; `git cat-file -e <pin>^{commit}` succeeds in that clone;
  `hermes plugins install roosiq/antemuse-plugin` resolves the pin.

### M2 — Catalog pull request

- **Blocked by:** M1.
- **Do:** branch on a fork of `NousResearch/hermes-agent`, add exactly one file
  `plugin-catalog/antemuse.yaml` (copy of `plugin-catalog/antemuse.yaml` at the
  pin), open the PR with `specs/changes/hackathon-submission/catalog-pr-body.md`.
- **Acceptance:** PR contains one added file; CI's catalog check passes; the
  entry's `version`, `requires_hermes` and `capabilities` match the manifest at
  the pin; the body carries the rule-13 disclosures and the screenshots.

### M3 — Catalog `image:` (banner)

- **Do:** 2:1 PNG, 1200×600, brand palette, wordmark and one line. Served from
  `raw.githubusercontent.com` at the pin.
- **Acceptance:** URL returns `image/png` with 200; image reads at 300 px wide.

### M4 — Catalog `screenshots:`

- **Do:** four PNGs under `docs/screenshots/`, committed at the pin: the terminal
  takeover, the chat card, the `/return` account, and a refused tool call.
- **Acceptance:** each URL returns 200 at the pin; each shows the real surface,
  not a mock; no private paths, tokens, or memory text in frame.

### M5 — Demo video and post

- **Do:** one take, < 90 s, 1280×720, H.264; posted publicly on X tagging
  `@NousResearch`. Script and beats live in `demo.md` and `tools/demo/`.
- **Acceptance:** duration 80–89 s, measured with `ffprobe`; the plugin is doing
  real work on camera; the post is public and tags the account.

### M6 — Submission form

- **Blocked by:** M2 and M5.
- **Do:** submit both links through the official form.
- **Acceptance:** confirmation captured; links resolve.

### M7 — Disclosure review before the PR

- **Do:** read `README.md` Disclosures and `SECURITY.md` against the code one last
  time; every network read, file read outside the data dir, write, child process
  and untrusted-text path must appear in both.
- **Acceptance:** a checklist in the PR body maps each row to a file and line.

## In-repo work this spec authorises

1. `tools/make_screenshots.py` — produce M3 and M4 from the real renderers, so the
   assets are reproducible rather than hand-captured.
2. `docs/screenshots/*.png` — the four stills plus `banner.png`.
3. Catalog entry gains `image:` and `screenshots:` URLs at the pin.
4. PR body gains the screenshot links and the disclosure-to-code table.

## Non-goals

- No change to states, the `state` tool schema, hooks, commands, or the §18
  must-not-change list.
- No new network endpoint, telemetry, credential handling, or self-updater.
- No re-shoot of the takeover; the renderer is the source of truth.
