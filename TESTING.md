# Testing

## Requirements

- Hermes Agent 0.21.6 or newer.
- Python 3.11+.
- `nltk` with the WordNet corpus for live walk coverage.
- Optional: `node` and `npm` for the desktop-pane harness.

## First run

```bash
hermes chat -q '/walk'       # six hops, tools open, work continues
hermes chat -q '/return'     # end it and keep the account
```

The seven slash commands are `/walk`, `/daydream`, `/doomscroll`, `/dream`,
`/unstuck`, `/explore`, and `/return`.

- `/walk` is an act: it takes all six hops inside the command and answers with the path —
  `WALKING ended · walk · 6 of 6 hops · …`. Nothing is left running and no further message is needed.
- `/daydream` delivers two pairs of this chat's own messages; `/dream` two links between things from your day. Both deliver at most one unit per message; the
  delivery poll may serve the first earned unit without one.
- `/doomscroll` delivers three public-feed posts; `/unstuck` one next move from your day and
  an unused map link.
- `/explore` is yours to drive and open-ended: `EXPLORING · 0 picks · you pick · it runs until you stop it`.
- `/return` ends the active state or explore and keeps its account. With nothing running it says
  `nothing running.`

Each state belongs to the chat that started it: another chat gets no material, no footer and no
ending, and its picks are refused. `/daydream` needs three of your own messages in that chat;
No state needs a git repo. Commits are optional extra material for `/dream` and `/unstuck`
when the chat happens to be inside a checkout; without one they read this chat's own day.

There is no `/break`, `/mood`, `/note`, `/watch`, or `/states` command. Those are
actions on the `state` tool.

## Suite

Run this exact command from the repository root:

```bash
env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q
```

The suite uses a temporary state home. It verifies state doses, delivery ownership,
tool policy, ending accounts, residue, ledger rows, command surface, person-driven
explore, and docs consistency.

**Drive an act the way the engine drives it.** `/walk` is instant: `engine.perform()`
calls the provider once per unit until the dose is met, so a six-hop walk is six
separate `walk_text(1)` calls, not one `step(6)`. Any memory a walk keeps inside a
single call is invisible to the next one. A stress test built on `step(6)` reported
200 clean walks while the shipped act ping-ponged (`campaign → youth movement →
campaign`) and journalled seven lines for a dose of six. Test the act through
`engine.perform()` and read the journal, and count hop lines against the dose — the
account line caps its own list, so it hides an over-run rather than reporting it.

Two isolation rules matter when you add a test:

- **A test's "project" is the one it makes.** The host exports its own working
  directory, and `dream` and `unstuck` read a repository, so an autouse fixture
  (`_no_inherited_working_directory`) closes both doors: the session-cwd provider and
  `ANTEMUSE_PROJECT_ROOT` / `TERMINAL_CWD`. Inheriting them makes a test read this
  machine's private history instead of its own tmp repo — six tests were failing that
  way before the fixture existed.
- **A test that wants git asks for the `git_repo` fixture.** It builds three recent
  commits and hands the repository over as the session's cwd. Without it a state test
  passes in a checkout (which is a repository) and fails in the extracted package
  (which is not) — that is exactly how the 0.11.22 gate first went red.

## Additional checks

```bash
python3 tools/examples.py --check
hermes plugins validate . --install-deps
hermes plugins doctor antemuse
```

`tools/examples.py` generates `docs/EXAMPLES.md` from the real engine. It includes
one worked example for each agent state, and it gives `dream` and `unstuck` a
throwaway repository with fixed subjects so the examples show those states working
rather than refusing. `--check` reads the file and verifies each example's contract —
the account reads as its own state, `dream` and `unstuck` name the concepts they
served, and no worked example is a failure line. It used to look only for the five
headings, which let the file describe endings the code had stopped producing.

### The shipped package, not just the checkout

The release gate runs the suite from the extracted tarball as well, because the two
differ in exactly the ways above:

```bash
tar -xzf ~/.cache/antemuse/dist/antemuse-<version>.tar.gz -C /tmp/pkgcheck
cd /tmp/pkgcheck/antemuse-<version> && \
  env -u PYTHONPATH ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q
```

The extracted package has no `.git` and no `docs/EXAMPLES.md` regeneration context, so
git-dependent tests are the ones that break there first. Measured at 0.12.14: **739 passed,
12 skipped** in the package against **1007 passed, 1 skipped** in the checkout; the difference
is the tests that need repository state or a browser.

A test that reads this checkout's real commit subjects is not testing the plugin, it is testing
whatever was committed last. Supply the material and patch the git seam (`sources.projects`,
`sources._recent_work`) instead. Two defects of exactly that kind were found at 0.12.8.

## Where it writes

- State, journal, residue, cursors: `~/.hermes/plugin-data/antemuse/` (or
  `ANTEMUSE_STATES_HOME` during tests).
- Per-project walk data: `<your repo>/.antemuse/`.
- `/explore` writes the concepts a person picks to the concept ledger.

No credentials or API keys are required for a state.

## Known limits

- State is profile-wide, while delivery and accounts are owned by the session that entered it.
- The desktop app is required to see the map or cockpit; chat and terminal show text only.
- `spark`, `keep`, and the exploration library are experimental and gated behind
  `experimental.enabled`.
- A state entered with `block: true` can restrict tools for the profile until it ends.
