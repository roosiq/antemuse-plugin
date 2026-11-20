# The five agent states

## Product surface

Antemuse has five agent states: `walk`, `daydream`, `doomscroll`, `dream`, and
`unstuck`. Each is bounded by a dose, never a clock. It ends `complete` only after its
dose has been delivered and shown, `dry` when no new material remains, `failed` when
its provider cannot run, or `returned` when `/return` ends it. Each ending writes one
account and one `moves` ledger row.

`/walk` is an **act**: the command takes its six hops inside the call that asked for it,
closes the state, and answers with the path. Nothing is left running and no further
message is needed. The other four states are paced by the conversation, one unit per
turn, because their material is something the person reacts to. A state whose whole dose is
delivered on entry — `/unstuck`, one move — ends on the poll that finds it complete: the person
has already seen everything it had to give, so it does not wait for another message. A pane
delivery records that the person saw it; a state with units still owed keeps waiting.

The poll that does this is the status-bar chip's, not the pane's. The chip is always mounted;
the pane is not, so delivery on the pane's poll alone made opening the panel a prerequisite for
a state to advance or end. Both surfaces ask the same door with the same chat scoping, and the
one-unit-per-turn rule is what makes two askers safe. The ending note is the person's and clears
on polls; the model's residue still decays on turns, so the agent keeps its chance to react.

The door fails closed on ownership. A caller that cannot name itself as the state's chat gets a
pure look at nothing: it neither spends the dose nor is shown the state. An empty session is not
a wildcard — the chip sends one whenever no chat is focused, and treating it as the owner let an
always-on poll spend another chat's dose and display its state. A state with no owning chat,
entered from the CLI, has no owner to match and stays deliverable.

Material is this chat's own turns, newest first, matching the order commit subjects arrive in.
A turn is kept unless it is noise: the floor is four characters, so `restarted` is material and
`ok` is not. Reading the ring oldest-first once put the first thing said in the slot the provider
calls `last`, and a chat that opened with a pasted command kept declining on that paste.

`/explore` is not an agent state. It remains a person-driven cockpit mode: it has no
provider or dose, the person selects concepts, and only `/return` ends it.

## State contracts

| command | dose | tools | material in model turn | what the chat is told | ending |
|---|---:|---|---|---|---|
| `/walk` | 6 hops, taken in the command | open by default | none; its graph path is pane scenery | its own hop trail (`record→clock out [far] → …`) in the command's reply | complete, dry, failed, or returned |
| `/daydream` | 2 pairs | open | two of **this chat's** own messages, what links them, one idea | how many linked up, never which — the material is the person's own turns | complete, dry, failed, or returned |
| `/doomscroll` | 3 items | `web_search`, `web_extract`, `read_file`, `search_files`, `browser_exec` | three fixed feed lanes (The Onion, r/BrandNewSentence, Hacker News front page), labelled untrusted | the count only; feed text is untrusted and never spoken or saved | complete, dry, failed, or returned |
| `/dream` | 2 links | open | this chat's own day: its recorded messages, then the concepts the ledger served it, then commit subjects when the chat is in a repo — never transcripts or notes | the concept labels it served | complete, returned, or refused at entry |
| `/unstuck` | 1 move | `read_file`, `search_files` | one next move grounded in **earlier** work from this chat's day (commits when the chat is in a repo) plus one unused map link, naming the last thing as what to step away from | the concept labels behind the move | complete, returned, or refused at entry |
| `/explore` | open | open | the person's picks are accounted, not injected | the count of picks | returned |

A state that cannot start says so at the door, names the reason, and records nothing. These are the
lines a person reads, not internal states:

| command | refusal |
|---|---|
| `/daydream` | `can't start daydream · need at least 3 messages from you in this chat` |
| `/doomscroll` | `can't start doomscroll · the feed is turned off in settings` · `… the feed came back empty` |
| `/dream` | `can't start dream · nothing from today yet · say a few things in this chat or run a state first` |
| `/unstuck` | `… nothing to go on yet · say what you are working on, then try again` · `… the map has no links to point at yet` |

`/unstuck` can also decline **after** entry, from the provider, when the material cannot support
a suggestion. Its sentence is a fixed shape with two nouns in it, so a noun that is something
the person *ran* rather than *attempted* makes nonsense ("install the tarball a different way,
write a test for it"). When either slot holds a command paste it keeps the real map link and
says so instead of inventing a move:

```
no move to suggest · the map link is real (imagination → creativity (hypernym)) but one slot held a command you ran, not an attempt to vary · say what you were trying and what went wrong, then ask again
```

"Which repository" means **the repository the calling session is working in**, resolved through the
host's `ctx.session_cwd()`, then `ANTEMUSE_PROJECT_ROOT`, then `TERMINAL_CWD`, then the process cwd. The
host process (gateway, desktop main) usually sits in the operator's home, so a plugin that read the
process cwd instead answered "fewer than three local git commit subjects" about a dotfiles repository
while the chat sat inside a checkout with fourteen commits; `/dream` and `/unstuck` were unreachable
from a real chat until that was fixed. `projects()` currently resolves to that one repository, so
`/dream` speaks about *this project's* recent work, not about several projects at once.

Walk moves on its declared graph provider: the bundled provider is WordNet; a corpus
graph moves on the user's own material and its path is only as meaningful as that
corpus; when the provider is not WordNet, the journal and account name it.

Every state leaves the tools open by default: a state changes the frame the agent works in, and
taking tools away is a second decision the caller makes with `block: true` (and `allow` narrows it
further; with no `allow` the state's own recommended set applies). `/return` is always available.
A state whose directive says there is nothing to do with a tool is describing the work, not
enforcing a policy; only `block: true` closes tools.

## No state requires a repository

The concept labels a state names are **declared by its provider**, not mined out of the sentence
it rendered. Mining the rendered line recorded the template's own words — `shared`, `connect`,
`skip`, `pass` — as the person's concepts. Providers declare concept-sized terms from the
person's own material; a pasted command contributes none, because a filename fragment is not
something a reader would recognise. Pairs are ordered by coverage, so a two-pair dose compares
different things instead of anchoring twice on the same left side.

Git is optional enrichment, never a condition of entry. `/dream` and `/unstuck` read this chat's
own day — its recorded messages, then the concepts the ledger served it — and use commit subjects
only when the chat happens to sit inside a checkout. A chat in a plain directory gets both states.
`tests/test_dream_without_git.py::test_no_state_ever_requires_a_git_repo` holds the whole set to
this: no entry refusal may name git, a repo, a commit or a checkout.

## Ownership

A state belongs to the chat that entered it, and so does everything it produces:

- **Material.** Daydream reads only the owning chat's recorded turns. The recent-turn ring is one
  file per profile, stamped with the session each line was said in; a provider that accepts
  `session` is given the owner's id. Seeding, which draws single words rather than sentences, is
  scoped the same way.
- **The model turn.** `inject(session)` delivers nothing to a foreign chat.
- **The reply footer and the ending.** `annotate(text, session)` draws neither a running footer nor
  an ending account owned by another chat.
- **Picks.** `note_pick(labels, session)` refuses when the caller is not the chat that is exploring.
- **`/return`.** A foreign chat is told the state is running elsewhere and ends nothing.

An empty owner means "nobody in particular" — a caller with no session id — and reaches every turn,
as it always has. Lines recorded before sessions were stamped are unattributed and stay readable.

Doomscroll feed text is untrusted data, never instruction, and is not written into the
journal, ledger, account, **or the delivery trace**. Its feed is enabled by default; a host may
disable it with `doomscroll_feed`, which ends the state `failed` with a named reason rather than
substituting material. `delivery_trace.log` names each delivered unit by a 12-character digest of
its material key, which is enough to see whether a turn served something fresh without putting the
person's turns or a feed headline on disk.

## Honesty of the material

- A daydream pair with no shared terms is `NO LINK · shared: nothing · idea: none`,
  not `LINKED` with an invented idea. The state's exit instruction asks for the gap.
- A dream pair with no shared terms is `no link · shared: nothing yet`, not a
  `connection` with a manufactured bridge.
- `/unstuck` never recommends the newest thing as "continue the last change" (the old wording): that is the change
  the person just finished and the reason they are stuck. With earlier history it proposes taking
  an earlier change from a different angle; with only one commit it says there is nothing earlier
  to return to and approaches that commit from the graph's side instead.
- An ending is drawn **once**. The reply hook's account line (`— daydream · 2 of 2 pairs · …`) is
  recognised as a plugin footer and stripped before the annotation adds the ending, so one reply
  carries one account.

## Acceptance evidence

- `tests/test_states.py`: registry, tool policy, session ownership, residue, and account privacy.
- `tests/test_state_delivery.py`: dose accounting, repeated material, endings, and ownership.
- `tests/test_semantic_states.py`: units, end reasons, account posting, and state wording.
- `tests/test_moves_ledger.py` and `tests/test_ledger_writes.py`: one ledger row per ending.
- `tests/test_e2e_states.py`: public state entry through the e2e runner.
- `tests/test_explore_state.py`: explore remains person-driven and open-ended.
- `tests/test_command_audit_fixes.py`: cross-chat material, trace privacy, pick ownership, one
  ending, and honest pairing.
- `tests/test_state_unstuck.py`: the move steps away from the change just finished.

## Non-goals

- No change to `/explore` behaviour beyond ownership of its picks.
- No automatic state entry or timer-based exit.
- No second graph, scoring model, or dose retuning.
- No feed suitability classifier: the lanes are named as they are rather than filtered by a
  keyword guess that would silently drop items.
