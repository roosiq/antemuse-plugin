# Changelog

All notable changes to Antemuse. The manifest version and this file move
together; the catalog entry is generated from the manifest at release time.

## 0.9.0 — 2026-11-09

First packaged build.

- Five states: `walk`, `daydream`, `doomscroll`, `unstuck`, `dream`, each with a
  duration, turn budget, reply contract, residue, and wordless imagery.
- States end on their dose, not the clock; minutes are a ceiling and an expiry
  says how much of the dose arrived.
- Host-enforced tool policy: `block: true` closes tools and a blocked call never
  runs; `allow:` narrows a block and is refused without it.
- `/return` produces an account from the journal without a model call, and keeps
  the residue.
- One recommendation line, emitted only when a counter justifies it (minutes,
  turns, repeated failed calls), always naming the counter.
- Terminal takeover (`python3 -m core.tui`), chat card, text record, and PNG card.
- Six settings rendered as a form by the desktop app; a setting may change how
  loud or long a state is, never what a state is.
- Exploration library (spark/keep, collider, selection) present but runtime-gated
  behind `experimental.enabled`; it makes no quality claim.

Known limits are recorded in `README.md` and in the catalog entry's
`known_issues`.

## Unreleased

- Nothing. Open work lives in `specs/changes/` with an explicit status per item.
