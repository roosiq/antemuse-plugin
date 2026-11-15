# Design pass — finish the instruments

Change id: `design-pass`
Repo: `antemuse-plugin`
Status: **audit complete, awaiting approval — nothing implemented**

## Goal

Finish what the two panes already are. The audit in `audit.md` covers both panes, chat, the
command surface, settings and the docs, and produces a phased plan: five critical fixes, five
refinements, six polish items, plus the design-system tokens the panes need.

## What this pass is

- Visual and interaction design only: hierarchy, legibility, responsive behaviour, failure
  copy, affordances, motion, empty states, focus.
- It writes the three artifacts the audit protocol requires and the repository lacked:
  `docs/design/DESIGN_SYSTEM.md`, `APP_FLOW.md`, `LESSONS.md`.

## What this pass is not

- No functional change. Seeding an explore, injecting picks, lane handoffs — those live in
  `../machine-and-person/` and are flagged there, not designed here.
- No new pane, no new state, no new route.
- No brand change: the panes wear the host's variables and that rule stands.

## Acceptance

1. Every Phase 1 finding is closed with evidence: a screenshot at 1440×900 and 390×844, and a
   measurement for the HUD's minimum cell width.
2. `whyFailed()` is the only failure vocabulary in the module — no raw `err.message` reaches a
   surface.
3. `reducedMotion(win)` is the only place the media query is read, and drift plus bullet travel
   honour it.
4. The map pane states its own controls on screen once, and the legend states what accent and
   size mean.
5. Suite, harness and the pane guards stay green; every new guard names the behaviour.

## Approval gate

Phase order is advisory, not fixed. Nothing is implemented until the person approves the
phases — the audit skill's own rule, and the same gate this repository uses for every change.
