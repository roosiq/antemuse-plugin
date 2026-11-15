# Antemuse constitution

**Status: draft, unapproved.** Written by reading what the repository already enforces, so
that the rules have a home before the next feature needs to cite one. Edit the articles you
disagree with rather than approving this as it stands — a constitution nobody wrote is the
same as no constitution.

Each article names where it is enforced. An article with no enforcement is an aspiration and
should say so.

## I. The state path never calls a model

Entry, exit, expiry, delivery and rendering are deterministic. A state has to work when the
model is slow, absent, or being rate-limited; a state that needs inference to exist is not a
state, it is a request.
*Enforced by:* `tests/test_runtime.py`, `tests/test_command_context.py`
(`/return` ends the state of the chat that asked for it).

## II. No claim without protected comparative evaluation

The plugin may describe a mechanism. It may not claim an effect. The one controlled run of
the subtractive walk found no ideation effect after length control, and that result is quoted
in the README rather than buried.
*Enforced by:* `README.md` "Known limitations", `experiments/idea-states/BENCHMARK.md`,
`tests/test_semantic_states.py`.

## III. The command surface is a contract

One command per state, plus `/return`. A plural neighbour of a singular command is a past
defect. Adding a verb is a deliberate contract change with docs, tests and a changelog entry
in the same commit.
*Enforced by:* `tests/test_command_surface.py`, `tests/test_docs_current.py`.

## IV. A state is a dose, not a duration

Minutes are a stall guard, not the thing being spent. A state that has no dose must be
declared open-ended, and every surface that prints "how much is left" must say so instead of
printing zero.
*Enforced by:* `tests/test_semantic_states.py`, `tests/test_explore_state.py`
(`test_no_path_says_zero_picks_left`).

## V. Surfaces wear the host's theme

Panes read the app's CSS variables. The only colour literals permitted are neutral greys and
black, used for the tube itself. A pane with its own palette is a second product.
*Enforced by:* the hue guard in `tests/test_cockpit_pane.py`.

## VI. Fail open at a lockout, fail closed at a write

A policy hook that cannot compute must allow the call and log why: a raising hook closes the
tool channel for every conversation, which is far worse than a missed block. Conversely, a
write that could attach to the wrong state must refuse — `POST /picks` records nothing
outside an explore.
*Enforced by:* `tests/test_hook_resilience.py`, `tests/test_explore_api.py`.

## VII. Specs are as-built

Numbers in a spec come from running the commands, not from the last time someone looked.
Behaviour that ships appears in a task with the evidence that closed it. Docs are checked
against the code by a test, not by memory.
*Enforced by:* `tests/test_docs_current.py`.

## VIII. Nothing that runs names someone's home directory

Shipped code, tests, scripts and instructions use `~` or resolve at runtime. Prose may record
provenance.
*Enforced by:* `tests/test_no_home_paths.py`.

## IX. A green claim needs a command

Tests name the behaviour, not the implementation. "It passes" without the command and its
output is not evidence, and no test count belongs in a README.
*Enforced by:* review practice; `CONTRIBUTING.md`.

## X. A release is a bump and a pin

The catalog entry pins a commit SHA. Pushing is not releasing, and a version bump without a
catalog entry leaves the plugin unreachable to everyone who installs from the catalog.
*Enforced by:* `scripts/release.sh`, `tools/catalog_entry.py`.

## Out of scope

This document does not govern Hermes itself, `nltk`, or the public feeds a doomscroll reads.
