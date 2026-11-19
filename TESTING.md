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
- `/daydream` delivers two pairs of this chat's own messages; `/dream` two links between your
  recent commit subjects in this repo. Both deliver one unit per message.
- `/doomscroll` delivers three public-feed posts; `/unstuck` one next move from your commits and
  an unused map link.
- `/explore` is yours to drive and open-ended: `EXPLORING · 0 picks · you pick · it runs until you stop it`.
- `/return` ends the active state or explore and keeps its account. With nothing running it says
  `nothing running.`

Each state belongs to the chat that started it: another chat gets no material, no footer and no
ending, and its picks are refused. `/daydream` needs three of your own messages in that chat;
`/dream` and `/unstuck` need a git repo with commits.

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
git-dependent tests are the ones that break there first. Expect roughly 650 passed and
20 skipped in the package against roughly 920 passed and 6 skipped in the checkout; the
difference is the tests that need repository state or a browser.

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
