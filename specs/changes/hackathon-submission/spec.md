# Hackathon submission — Antemuse

Status: **planning** 2026-11-08. Nothing submitted, nothing pushed.
Owner: Ryan Cook. Scope: submission artifacts for the Nous Research Hermes plugin
hackathon. Does not change runtime behaviour.

## 1. What is being submitted

One plugin, one entry, four artifacts:

1. A **public** repository at a full 40-character commit SHA that anyone can clone.
2. A **catalog PR** to `NousResearch/hermes-agent` adding
   `plugin-catalog/antemuse.yaml` (owner submission, rule 5).
3. A **public demo on X**, strictly under 90 seconds, showing the plugin working,
   tagging `@NousResearch`.
4. The **official form** (`https://form.typeform.com/to/FwJLvOln`) carrying the
   catalog PR link and the X demo link.

Deadline: **2026-11-11 17:00 EST (UTC-05:00)**. At planning time that is
T−3 d 1 h 32 m. EST is UTC−05:00; the announcement body omits the year and the
oEmbed date (2026-11-04) is the evidence for it.

## 2. Why this plugin is a credible entry

The judging text names five qualitative criteria and no weights: usefulness,
reliability, polish, creativity, and capability beyond a prompt or skill.
Antemuse's strongest ground is the last one, and it is demonstrable in seconds:

- The state is **enforced by the host**, not suggested to the model.
  `pre_tool_call` refuses tools the state does not allow, before they run.
- Entry, exit, expiry, restoration and rendering are **deterministic** — no model
  call, no scoring. The clock and turn budget end a state without inference.
- The **audiences are separated by construction**: the model receives material
  and a directive; the person receives pictures and counts. No candidate text
  reaches a human surface.
- It spans **five Hermes surfaces** that a prompt cannot reach: hooks, a tool,
  slash commands, a bundled skill, a terminal takeover, a desktop surface and a
  dashboard route.

What it must not claim: that a state makes the agent more creative. `docs/spec.md`
§16 and §18 forbid it and the evidence is directional, not established (p = 0.17,
n = 8). The demo shows the mechanism and the experience, never a benefit claim.

## 3. Non-goals

- No new states, no change to the `state` tool schema, no change to §18's
  must-not-change list.
- **No `immersive-visuals` or `scene3d-renderer` work in this submission.** Both
  are `proposed`, neither is implemented, and §19 reserves `1.0.0` for
  `scenes-per-surface`. Shipping a renderer rewrite under hackathon time pressure
  would put an unverified surface on the one commit reviewers read.
- No desktop pane in the demo: `desktop-surfaces` §7b records that the dock pane
  did not render inside the app. The terminal takeover is the verified full-pane
  surface and is what the video shows.
- No self-updater, no telemetry, no new network endpoint, no credential handling.
- No `cognition` marketplace category PR in this window. The honest existing
  shelf is `general`; asking for a category is a separate upstream conversation.

## 4. Acceptance criteria

Submission is complete only when every line below is true and evidenced.

**Eligibility (HACK)**

- A1. `github.com/roosiq/antemuse-plugin` is public and `git clone` succeeds
  without credentials.
- A2. The pinned commit contains no untracked build output, no `.pyc`, no
  `data/meshy/`, no `node_modules/`, and matches the tree that was validated.
- A3. `hermes plugins validate <pin> --install-deps --json` reports every check
  `ok: true` and an empty `warnings` list **at the pinned SHA**.
- A4. `hermes plugins doctor <pin>` reports the plugin loading with 1 tool and 8
  hooks.
- A5. The test suite passes at the pin, with the count and command recorded in
  `docs/spec.md` §13.
- A6. `plugin-catalog/antemuse.yaml` exists in a PR against
  `NousResearch/hermes-agent`, pins the full SHA, quotes `version`, declares
  `category: general`, `tier: community`, `requires_hermes: ">=0.21.6"`, and
  carries the rule-13 disclosure lines.
- A7. The X post exists, is public, embeds a video **strictly under 90 s**, shows
  the plugin actually running, and tags `@NousResearch`.
- A8. The form is submitted with both links, before 2026-11-11 17:00 EST, with a
  confirmation captured outside the repository.

**Catalog admission (CAT)**

- A9. `LICENSE` present and compatible with the bundled MIT three.js and the
  CC BY 4.0 `data/collider` attribution already in the tree.
- A10. README has an explicit **Disclosures** section covering: network reads
  (doomscroll feeds, optional image generation endpoint), shell/subprocess use in
  `core/tui.py` and dev tools, the external `SD_SERVER` default, the data
  directory, and that no credentials are read or stored.
- A11. Declared capabilities match registrations (already validated; re-run at pin).
- A12. No committed screenshot PNG is required for admission, but the entry's
  `screenshots:` must point at images hosted under the repository at the pinned
  SHA — which needs `.gitignore`'s blanket `*.png` exception.

**Polish (QUALITY-03)**

- A13. `README.md` describes what the plugin does in the first screen, has a
  working install command, and contains no drifted counts (today: "1 tool,
  4 hooks" against 8 registered).
- A14. Every failure path shown in the demo is a named failure, not a blank
  screen: unavailable feed, missing `nltk`, expired state, blocked tool.

## 5. Must not change

- `state` tool schema and action set; the four state definitions and their
  durations, turn budgets, cadences, tool policy, directives, contracts, residue.
- Hook set and contracts; `CONTROL_TOOLS`; `/return`; journal cap 60; residue cap
  3; two-turn report decay.
- The no-model-call rule on entry/exit/expiry/rendering; provider failure strings;
  the no-words rule on terminal and caption-free chat.
- Origin binding: no delivery helper, no channel ids in `core/`.

## 6. Human gates (cannot be done by an agent)

1. `gh auth login -h github.com` — the stored token for `roosiq` is invalid.
2. Creating the public repository and pushing it, if the owner prefers to do that
   personally.
3. Posting the demo on X and submitting the Typeform: both require Ryan's account
   and identity.

Everything else — repo hygiene, README, licence, validation, catalog entry, video
capture and edit — is machine work.
