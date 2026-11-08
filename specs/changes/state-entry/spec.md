# State entry — where a state starts, which way it goes, and how it stays diverse

Status: **implemented (partial)** 2026-11-08. Owner: Ryan Cook. Scope: what material a
state opens with and the rule that moves it. No change to durations, turn budgets, tool
policy, rendering, or the no-words rule.

## The gap this closes

`docs/spec.md` defined each state's **sources** (WordNet, FrameNet, memories, feeds) and
its **cadence**, but never its **entry point** or **direction** — and nothing grounded the
first step in the work the person is actually doing. A walk started from a fixed seed list
(`SEEDS`) or a saved cursor; a dream started from a random frame. Two consequences:

1. **Every entry looked alike.** Same seed pool, same relation table, so repeated walks
   drift toward the same regions of WordNet.
2. **None of it was about the project.** A walk taken mid-refactor had no reason to touch
   the words that refactor is made of, so its material was decorative rather than oblique.

## What a state's entry must declare

Each state declares three things, and the code may not improvise them:

| State | Entry point | Direction | Grounded or random |
|---|---|---|---|
| `walk` | one seed term, then a real WordNet edge per step | **out** from the seed along the relation the edge names (hypernym up, hyponym down, similar/holds lateral); direction is recorded per hop | **mixed — 5 : 3 : 2** (project : conversation : random) |
| `daydream` | two memories | **across**: moves only when the two share ≥ 2 terms; the shared term is the direction | conversation-first, memory files second (see `hermes-integration`) |
| `dream` | **a memory** — a word the person said or stored, looked up inside FrameNet | **recombine**: frame → frame through a shared lexical unit or role | **memory-first — 6 : 2 : 2** (memory : project : random) |
| `doomscroll` | a live feed page | **none, by design.** Undirected is the point of this state | random external only; never project material |

## The mix, and why it is a ratio rather than a switch

Diversity is not "always random" — a state that never touches the project is noise, and a
state that only touches the project cannot surprise. Each entry draws its source from a
**deterministic hash of (state, entry timestamp, entry counter)** with weights:

- **50 % project** — terms from the working repository: its basename, its branch name,
  README headings, top-level directories, and the `options.goal` when the entry supplied
  one.
- **30 % conversation** — terms from the bounded recent-turn ring (`core/recall.py`).
- **20 % random** — WordNet synsets / FrameNet frames, deliberately unrelated.

**`dream` declares its own mix: 6 memory : 2 project : 2 random.** A dream's premise is
recombining what is already known, so a random frame is the wrong door; it opens on a
word the person said or stored, and only falls back to the repository or to chance when
there is nothing to remember.

Determinism matters: the same entry, replayed, must pick the same source. A live RNG
would make a walk unreproducible and its diversity unmeasurable.

## Diversity contract

1. **No immediate reuse.** A seed term already used by the current state is skipped.
2. **Per-state salt.** Two states entered in the same second must not draw the same term;
   the state name is part of the hash.
3. **Auditable.** Every entry records `seed=<source>:<term>` in the state's journal, so a
   reviewer can see the mix rather than trust it.
4. **Measured, not claimed.** A test draws 200 entries and asserts each source appears
   within ±8 points of its weight. If the mix is wrong, the test says so.

## Failure behaviour

- No project (no `.git` ancestor) → the project share falls to conversation, then random;
  the fallback is recorded, not silent.
- WordNet or FrameNet missing → the state names the failure as it does today and the entry
  does not fabricate material.
- A project term that does not exist in WordNet/FrameNet → skip to the next candidate;
  never invent a synset.

## Acceptance criteria

1. `core/seeding.py` resolves an entry as `{source, term}` for `walk` and `dream`; the
   journal line names both, and `dream`'s first source is memory.
2. Over 200 synthetic entries the source mix is within ±8 points of 5 : 3 : 2.
3. A term is never reused by the same state inside one window; two states in the same
   second differ.
4. `doomscroll` never receives project material.
5. With no `.git` ancestor, entries still resolve (conversation or random) and the fallback
   is visible in the journal.

## Must not change

State definitions, durations, turn budgets, cadences, directives, contracts, tool policy,
`CONTROL_TOOLS`, residue caps, the no-words rule on the human card, and the rule that
entry, exit, expiry and rendering never need a model call.
