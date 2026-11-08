# Unstuck — the state for a project that does not exist yet

Status: **implemented** 2026-11-08. Owner: Ryan Cook. This adds a fifth state, which
revises the four-state lifecycle protected in `docs/spec.md` §18. The revision is the
point of the change; everything else in that set stays fixed.

## Why a fifth state

The four existing states all assume a project exists: something to walk away from,
memories to join, a feed to consume, stored concepts to recombine. At the start of a new
project there is nothing to recombine — and the failure mode is not "no ideas", it is
**a menu**. Five plausible directions, none chosen, no spec written.

A unstuck is the one place where the right output is a single direction and the
artifact it belongs in.

## Definition

| Field | Value |
|---|---|
| name | `unstuck` (aliases `greenfield`, `trailhead`, `start`, `new_project`, `zero`, `day-one`) |
| duration | 5 minutes |
| turns | 3 |
| cadence | 20 s |
| tools | `read_file`, `search_files` — read the project, change nothing |
| feeds | yes: what the project actually contains |
| contract | one direction · named with the spec file it becomes |
| residue | `unstuck: a direction named, and where it goes` |

## Material

Deterministic, read-only, no model call on the state path:

- the repository's name and top-level entries;
- its commit count and first commit subject (`git -C <root> log --max-count`);
- whether a README exists, and its opening line;
- **what is already decided**: `specs/`, `.specify/specs/*/spec.md`, `docs/spec.md`,
  `AGENTS.md`;
- the entry seed from `core/seeding.py` (project-first), so two unstucks in the same
  repository start from different words.

Missing evidence is named, not guessed: `no project root · no .git ancestor`,
`git unavailable · <reason>`, `no README`, `no spec files yet`. A unstuck on a project
that already has a real spec says so — that is a finding, not a failure.

## Directive (what the agent is told)

Name **one** direction. Say which spec file it would become the first paragraph of, or
which file it would create. Do not offer a menu, do not rank options, do not summarise
the repository back to the person. If the direction is wrong the person will say so; a
list of five is unusable.

The state recommends a direction; it never writes the spec. Writing project files is the
agent's normal work, done on the person's instruction, outside the state.

## When it is recommended

`core/recommend.py` fires `unstuck` when the project is **new**: fewer than three
commits *and* no spec artifacts. It is the only recommendation that outranks a loop,
because on an empty repository there is no loop worth interrupting — there is nothing to
be stuck in.

Once the project has three commits or a spec file, the pattern stops firing. A
recommendation that keeps pointing at the unstuck after the trail has started is a
malfunction, not an encouragement.

## Acceptance criteria

1. `states.STATES["unstuck"]` exists with the budget above, and `/unstuck` is
   registered; `/return` remains the only way out.
2. `sources.unstuck_text()` returns what the repository contains, and **names** each
   missing piece instead of inventing it.
3. `recommend.suggest()` returns `unstuck` for a fresh repository and nothing for a
   repository with a spec.
4. Tool policy is the read-only pair; nothing in this state can modify the project.
5. The picture contract is unchanged: wordless card (BR-5), no candidate text on any
   human surface.

## Not built

- **Its own art.** The state renders with the `walk` scene until a unstuck pack is
  generated; this is named in `docs/architecture.md` rather than hidden.
- **Writing the spec.** Deliberately out of scope: the state recommends, the agent acts
  on instruction.

## Must not change

Durations and budgets of the other four states, cadences, directives of the others,
`CONTROL_TOOLS`, `/return`, residue caps, journal cap, the two-turn report decay, the
wordless card, and the rule that entry, exit, expiry, tool restoration and rendering
never require a model call.
