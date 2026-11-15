# Historical state audit — superseded by the one-state cut

Change id: `state-audit`
Status: **v3 — three rounds; one new P0 from the failure paths; nothing fixed yet**

Round two (two hostile reviewers on the nous provider, plus my own re-verification) found one
root cause I had wrong, three claims that are not true of the current code, and one production
delivery path I had missed entirely. What changed is recorded at the end under *Review round two*.

## How this was done

Every state was driven end to end against a copy of the live data directory (real ledger, real
corpora, real feeds), calling the plugin exactly as its `pre_llm_call` hook does — one
`engine.inject()` per turn, no extra delivery. Entry line, `status`, each turn's injected block,
the reply annotation and the closing account were captured. Each state was then re-run with the
world sabotaged (no corpora, no feeds, not in a repository) to see what a person gets when it
fails.

> **Correction to the first pass of this audit.** It called `deliver_if_due()` before `inject()`
> in the probe, which double-delivered and made every state look as though it never showed its
> material. That was a measurement error, not a defect: `/daydream` and `/dream` deliver content
> on their first turn. Everything below is the production path.

## The defect: every state loses its **last** unit, and one state loses all of it

`inject()` calls `deliver_if_due()`; that can serve the final unit of the dose; `_expire()`
(line ~300) then closes any state with `served >= dose`; `inject()` reads `data["active"]` after
that and finds nothing, so the `[WHAT ARRIVED …]` block is never built. The turn receives the
closing instruction and a counts-only report instead.

Measured, production path:

| State | Dose | What the agent actually receives |
| --- | --- | --- |
| daydream | 2 pairs | pair 1 in full (both sides, shared terms, a possibility); pair 2 never shown |
| dream | 2 recombinations | connection 1 in full (both sides, shared terms, a caveat); 2 never shown |
| doomscroll | 3 items | items 1 and 2 in full; item 3 never shown |
| walk | 6 hops | nothing, by design — and that is correct |
| **unstuck** | **1 direction** | **nothing at all** — the only unit is also the last one |
| explore | none | the person's picks, via the account — correct |

So the mechanism mostly works, and fails in two places:

- **Every state loses its final unit**, so every closing instruction asks the model to report a
  thing it was never handed. Daydream's close says "the two things that surfaced" after one was
  shown; dream's says "the connection you found" after the second vanished; doomscroll's asks
  "whether anything was worth keeping" after one item disappeared.
- **`/unstuck` never delivers its recommendation at all — and the cause is not the close.**
  `sources.unstuck_text()` builds a real `direction 1 · … because … · first: …` and then
  `out.insert(0, "starts from " + seeding.marker(seed))`, while `deliver_if_due()` serves exactly
  one line (`got[:1]`). The line it serves is the seed marker, so the direction is discarded
  before the ordering bug can matter. Fixing the close alone would still deliver only
  `starts from seed=project:antemuse`.

**Fix direction (corrected in round two).** My first fix — "let `complete_if_dosed()` own the
close" — was vacuous: `deliver_if_due()` already calls it, which is precisely how the state closes
before the block is built. The real fix needs a notion of presentation: a served unit is not spent
until it has been shown to a turn. Concretely — serve the final unit without completing, mark it
presented when `inject()` has put it in the block, and complete on the turn after that, so the
state closes with its last material in hand and exactly one account. `GET /state` must keep
serving without completing, or the pane will end states the agent never saw.

**Why the suite missed it:** the tests assert that doses are delivered and accounts produced
(`served`, `dose`, `report`). Nothing asserted that the final turn's *block* contains the final
item.

## What each state is actually like

### walk

- Entry line and directive are honest, and withholding material is the documented mechanism.
- The closing account is a chain of unrelated concepts:
  `giant petrel→hepatolenticular degeneration [far] → … → sargassum fish→T…`. The `outer` policy
  maximises distance, so the pairs are semantic noise. A person reading it learns the plugin
  walked somewhere absurd.
- Contradiction in one paragraph: "The path you walked is scenery, not a hint" followed by the
  entire path.
- Adversarial read: *"so it interrupts me for six messages and then shows me two random nouns."*

### daydream

- Turn 1 arrives with real material: `JOINED · …the live app is closed and the gateway… ↔ Neither
  is your app… · shared: canvas, closed, cockpit, gateway · possibility · …`
- The account the person sees is `2 of 2 pairs · JOINED · joined ×2` — the count of a thing, not
  the thing. The person never sees the two memories; the model saw one of them.
- Adversarial read: *"it told me my two thoughts joined. Which two?"*

### doomscroll

- Material is visible and genuinely funny — `babylonbee.com · @feed · 2-Year-Old Under Fire After
  Showing Mommy What Sound The Monkey Makes` — delivered with hostname and handle attached.
- Every item carries `[14 skipped as work]`, including the second and third, so the marker reads
  as boilerplate rather than a decision about that item.
- The block says "the person only sees pictures". There are no pictures: chat is text and the
  pane shows the map, not the feed. The instruction describes a surface that does not exist.
- With feeds down it closes itself, and `/return` afterwards answers `not in a state.`

### dream

- Turn 1 delivers a real connection: `antemuse-plugin: catalog entry for ed0834ab7028 ↔
  antemuse-plugin: catalog entry for d6a495fb0f5b · shared: catalog, entry · may already be
  answered by the other side · window: 7 days (today had too few projects to connect…)`.
- That caveat — "today had too few projects to connect, and a week is as far back as this looks"
  — is the most honest sentence in the plugin.
- The account collapses all of it to the word `connection`.
- Adversarial read: *"it says it found a connection between my projects and names neither."*

### unstuck

- The single worst experience: the recommendation is never delivered, and the account says
  `starts from seed=project:antemuse`.
- Adversarial read: *"it recommends something, refuses to say what, and calls it a seed."*

### explore

- Works end to end: no dose, ends only on `/return`, account names the person's own picks
  (`3 shot(s) on 2 concept(s) · bookshelf ×2, legacy ×1`), annotation honest
  (`— exploring · open · you end it`).
- Gaps are elsewhere: nothing aims it (`/explore <concept>`), and picks do not become material for
  the next turn beyond the account line.

## Retracted: `/return` after a state closed itself

I claimed this answered `not in a state.` and that a CLI has no notifier, so the account was
lost. Both are wrong against the current code. `stop()` scans residue for a report with
`turns_left > 0` and answers `WALKING finished · 5 of 6 hops · …`, and
`tests/test_states.py::removed-state coverage`,
`tests/test_command_context.py::test_return_with_nothing_running_does_not_repeat_the_last_ending`
and `test_semantic_states.py::test_the_account_is_posted_when_the_dose_lands` already hold that
line. Without a notifier the report stays as unreported residue and reaches the next turn as
`[ANTEMUSE REPORT]`. The `not in a state.` answer is correct behaviour once the two-turn residue
window has passed — my probe ran seven turns and hit exactly that.

## Missed path: the pane drains the dose without a turn

Verified: four `deliver_if_due()` calls with no `note_turn()` moved a walk from `served 1` to
`served 5`, and `annotate()` then read `— walking · 1 hops left`. The cockpit and map poll
`GET /state` every four seconds, and that endpoint serves. So a person who enters `/walk` and then
sits in the cockpit can spend the entire dose while the agent sees one hop. Delivery is not owned
by the turn; it is owned by whoever polls first.

## Retracted: the reply annotation is dead in practice

`annotate()` works while a state is active — measured, on a live walk:
`— walking · 5 hops left · /return to come back`, and again after four pane polls. It returns
`None` only once the state has completed, which is correct. My probe inspected completed states
and generalised from them.

## Copy

- Four states close with the same generic sentence — *"The act is done, so the state is over.
  Carry what it gave you into the work."* — including the ones that gave one item of three.
- Internal vocabulary sits beside human language: `0/6 hops`, `seed=project:…`,
  `[14 skipped as work]`, `joined ×2`.
- Doomscroll's "the person only sees pictures" is false on every surface.

## Ranked

1. **P0 — a failed source is counted as material and completes the state.** `daydream` with a
   dead provider reports `2 of 2 pairs · feed unavailable`: the dose is spent, the account is a
   completion, and the closing instruction asks for material that never existed. Failure lines
   must not increment `served`, and such a state should end `failed`, not `complete`.
2. **P0 — the final unit of each feed-enabled state never reaches a turn.** `deliver_if_due()`
   serves it and completes in the same call, so `inject()` builds the block from an empty `active`
   and the closing instruction asks about material the model never saw. Needs presentation state,
   not a different call site.
3. **P0 — `/unstuck` serves its own seed marker instead of the direction.** `unstuck_text()`
   inserts `starts from seed=…` at index 0 and the dose is one line, so the recommendation is
   discarded before delivery. Independent of defect 1, and fatal on its own.
4. **P1 — the pane drains the dose without a turn.** `GET /state` calls `deliver_if_due()`; four
   polls took a walk from 1 to 5 served with `turns == 1`. Whoever polls first spends the state.
5. **P1 — accounts report counts, not content** (`joined ×2`, `connection`). Constrained by
   `test_the_account_never_quotes_the_material_it_was_given`: the fix is a safe reference, never a
   quote of memory text.
6. **P1 — the tool contract is opt-in but stated as intrinsic.** `enter()` defaults to
   `block=False`, `_effective_tools()` returns `None`, and the injected rule reads
   `Tools are open in this state.` while the state's own card says "No tools, no instructions."
   Either the copy or the default has to move.
7. **P1 — doomscroll hygiene**: hostnames and handles in front of the model, `[14 skipped as work]`
   repeated on every item, and "the person only sees pictures" in a chat that shows none.
8. **P2 — walk hands over a path it tells the model to ignore**, and the path is semantic noise.
9. **P3 — one generic closing sentence** for four different states, in the command reply.

## What is good and should be protected

- Withholding walk material is a measured decision with a written rationale; delivery tests will
  tempt someone to "fix" it. Do not.
- `dream`'s caveat about the widened window is the tone the rest should have.
- `/explore`'s "open · you end it" and the picks-by-count account are the best copy in the plugin.
- States closing on their dose rather than a clock is right; the defect is what the close drops,
  not that it exists.

## Not covered

- No model was called: this records what each state hands the model, not what a model does with
  it. Whether delivered material changes output is the benchmark's question.
- Doses were driven by a loop, not by a person's typing.
- The panes are a separate audit (`../design-pass/audit.md`).

## Review round two

Two independent hostile reviewers ran on the nous provider (`openai/gpt-5.6-terra`): one against
the code, one as a user who had not read the README. Their verdicts, and what I did with each.

| Claim | Verdict |
| --- | --- |
| `/unstuck`'s root cause is the seed line at index 0, not closure ordering | **Accepted — verified in `core/sources.py:1120` and `deliver_if_due`'s `got[:1]`** |
| "Let `complete_if_dosed()` own the close" is a vacuous fix, because it already runs inside `deliver_if_due()` | **Accepted — verified at `engine.py:782`** |
| `GET /state` drains doses with no turn | **Accepted — verified: 4 polls, `served 1 → 5`, `turns == 1`** |
| Tool blocking is opt-in (`block=False` default) while the copy says "No tools" | **Accepted — verified in `enter()` and `_effective_tools()`** |
| `/return` after a self-close returns the account, not `not in a state.` | **Accepted — my claim was false for the residue window** |
| A CLI without a notifier loses the account | **Accepted — false; unreported residue reaches the next turn** |
| The reply annotation "almost never appears" | **Accepted — false; measured live during an active walk** |
| "Accounts should name what arrived" | **Narrowed — blocked by an explicit privacy test; a safe reference only** |
| Walk's final unit is "swallowed" | **Accepted — wrong; walk withholds by design and its account carries the path** |
| "The person only sees pictures" is false on every surface | **Narrowed — it is model-facing copy that contradicts the README; overstated as universal** |
| Unattended states are "overstated" in the README | **Rejected — `README.md:333` says cron and gateway runs progress; each turn serves a unit, and the no-ticker comment says exactly that. `/explore` is the stated exception.** |

Neither reviewer was asked to be agreeable, and both corrected the audit in ways that changed the
fix. The pattern in my own errors is consistent: I measured the tail of a state and generalised to
the whole of it — the same mistake twice, first on delivery, then on the annotation.

## Round three: the failure paths

Every state was then run with its source broken, plus the two commands a person can type at the
wrong moment. Three new findings, one retraction, one thing that is right.

### P0 — a failed source counts as delivered, and the state reports a full dose

`daydream` with its provider returning a failure line, driven on the production path:

```
turn 1  [WHAT ARRIVED WHILE YOU WERE THERE — react to this, the person only sees pictures]
          · feed unavailable · nothing to read
turn 2  [YOU JUST CAME BACK — the daydream is over. In one line: the two things that
         surfaced and what they touched …]
          · daydream · 2 of 2 pairs · feed unavailable
```

The failure line was counted as a served unit, so the state completed with `served == dose`, and
the account claims `2 of 2 pairs` for a state that produced nothing. `_is_failure_line()` exists
and is used to keep failure lines out of the concept ledger — the count does not consult it.
Everything downstream inherits the lie: the dose is spent, the account is a completion, and the
closing instruction asks for two memories that were never there.

This is the inverse of "sources fail by name". They fail by name *and then claim the dose*.

**Fix direction:** failure lines must not increment `served`. A state whose source failed should
end with a reason of its own — `failed`, naming the source — rather than `complete`, and the
account should say `nothing arrived`.

### P1 — the README documents an ending that no longer exists

`README.md:24` lists three endings and quotes one: "`expired` (the ceiling passed first:
'expired before its dose: 2 of 3')". `_expire()` has no clock — its own docstring says time
passing is not a reason for anything — and nothing in the code emits that string; it survives only
in a failure-word tuple and a comment. Anyone reading the README will look for a stall guard that
was deliberately removed.

### P2 — entering a second state drops the first without a receipt

```
/walk   → WALKING · 6 hops · work continues · the frame is elsewhere · different on return
/dream  → DREAMING · 2 recombinations · the day across projects · connections between tasks
          (left walk; no residue kept)
```

The entry line is honest about the replacement, but the walk produces no account at all: the
person loses a state they paid several turns for and gets one parenthetical. Either refuse while
one is running, or post the abandoned state's account.

### Right, and worth protecting: the bystander rule

A state belongs to the session that entered it. From another session, `inject()` returns `None`
and `/return` answers `WALKING is running in the session that started it. Nothing was ended here
— /return there to finish it.` The state keeps running. That is correct and was tested before it
was trusted.

### Retracted before it was published: journal bloat

I suspected `journal_cap` (60) was not enforced, because a prefilled 200-entry journal stayed at
200 after a write. It stays there because `record()` returns early when no state is active, which
is correct. Every write made during a state is trimmed to the cap. No finding.

### Still unverified after two rounds

- Whether a fix that preserves the final unit changes the timing of the notifier post or the
  `/return` reason in a way a person would notice.
- Whether `inject()`'s snapshot can be made authoritative when a pane poll lands between delivery
  and the block, without a lock held across a provider call.
