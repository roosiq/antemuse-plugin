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
turn, because their material is something the person reacts to.

`/explore` is not an agent state. It remains a person-driven cockpit mode: it has no
provider or dose, the person selects concepts, and only `/return` ends it.

## State contracts

| command | dose | tools | material in model turn | what the chat is told | ending |
|---|---:|---|---|---|---|
| `/walk` | 6 hops, taken in the command | open by default | none; its graph path is pane scenery | its own hop trail (`record→clock out [far] → …`) in the command's reply | complete, dry, failed, or returned |
| `/daydream` | 2 pairs | open | two of **this chat's** own messages, what links them, one idea | how many linked up, never which — the material is the person's own turns | complete, dry, failed, or returned |
| `/doomscroll` | 3 items | `web_search`, `web_extract`, `read_file`, `search_files`, `browser_exec` | three fixed feed lanes (The Onion, r/BrandNewSentence, Hacker News front page), labelled untrusted | the count only; feed text is untrusted and never spoken or saved | complete, dry, failed, or returned |
| `/dream` | 2 links | open | local git commit subjects only, from the repository this chat is working in, never transcripts or notes | the concept labels it served | complete, returned, or refused at entry |
| `/unstuck` | 1 move | `read_file`, `search_files` | one next move grounded in **earlier** commits plus one unused map link, naming the last change as the thing to step away from | the concept labels behind the move | complete, returned, or refused at entry |
| `/explore` | open | open | the person's picks are accounted, not injected | the count of picks | returned |

A state that cannot start says so at the door, names the reason, and records nothing. These are the
lines a person reads, not internal states:

| command | refusal |
|---|---|
| `/daydream` | `can't start daydream · need at least 3 messages from you in this chat` |
| `/doomscroll` | `can't start doomscroll · the feed is turned off in settings` · `… the feed came back empty` |
| `/dream` | `can't start dream · need at least 3 commits in this repo from the last month` |
| `/unstuck` | `… this chat is not inside a git repo` · `… no commits to read here` · `… the map has no links to point at yet` |

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
- `/unstuck` never recommends the newest commit as "continue the last change" (the old wording): that is the change
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
