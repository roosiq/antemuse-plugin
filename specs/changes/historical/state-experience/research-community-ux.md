SUPERSEDED 2026-11-16 — this spec describes the retired multi-state product; see one-state-and-verdict.

# Community plugin UX — research

Change id: `state-experience` (research annex)
Status: **research complete, gaps proposed — nothing built**
Method: local evidence. The 1,379-entry Hermes plugin catalog in
`hermes-agent/plugin-catalog/`, the Desktop Plugin SDK cookbook, and the four desktop plugins installed
in this profile. Web search returned no results and `web_extract` is unavailable on this backend
(SearXNG is search-only), so nothing here rests on a web page.

## What the ecosystem actually is

| | count |
| --- | --- |
| catalog entries | 1,379 |
| tier community / official / verified | 1,343 / 21 / 11 |
| categories | tools 602 · desktop 255 · models 111 · memory 88 · automation 86 · general 77 · web 62 · platform 59 · voice 36 |
| entries shipping screenshots / an image | 267 / 429 |
| entries declaring `known_issues` | 236 |
| entries providing **zero** tools | 908 of 1,375 |
| tools per plugin, mean / max | 2.04 / 100 |

Hook frequency across the community (top of the distribution):

`pre_tool_call` 172 · `pre_llm_call` 171 · `post_tool_call` 114 · `on_session_end` 83 ·
`on_session_start` 57 · `post_llm_call` 51 · **`transform_llm_output` 51** · `post_api_request` 42 ·
`on_session_finalize` 42 · **`transform_tool_result` 37** · `subagent_start` 30 ·
`post_approval_response` 28 · `pre_approval_request` 17 · `pre_verify` 11 · `post_compaction` 10

Language census over every entry's prose (description, title, readme, known_issues):

`disclosure` 79.4% · `live` 24.7% · `read-only` 21.5% · `settings` 11.5% · `dashboard` 9.1% ·
`pane` 8.7% · `cost` 6.2% · `button` 3.6% · `progress` 2.5% · `panel` 2.5% · `status bar` 2.1% ·
`timeline` 1.1% · `onboarding` 0.4% · `keyboard shortcut` 0.1% · `empty state` 0.0%

## The live marketplace (checked at the source, not the repo copy)

`hermes plugins search --json` returns the curated catalog the site is built from: **2,311
entries** — the local `hermes-agent/plugin-catalog/` copy in this checkout is stale at 1,379.
Tiers: community 2,277, official 21, verified 13. Shelves: tools 1,114, desktop 409,
automation 174, models 141, memory 127, general 119, platform 92, web 80, voice 55.

The site (`hermes-agent.nousresearch.com/docs/plugins`) is a public marketplace: hero, featured
shelf, search across plugins · skills · connectors, category pills, and cards sorted by GitHub
stars. Discovery is by **stars and card copy**, not by tier.

How Antemuse appears there today:

- `general` / `community`, **1 star**, added one day ago, `0.10.44 @ b19cca81`, 1 tool, 8 hooks.
- It has a banner and three screenshots (all resolve, 200), `known_issues`, and a disclosure
  paragraph. The listing is better equipped than expected.
- **The page renders the README from the pinned sha, and that README is stale.** It says "four
  states … and one that names a direction" (five, no `/explore`), "the units arrive one a second …
  a six-hop walk is served in about six seconds" (the timer pacing was removed), and "three
  endings: complete, returned, expired" (`expired` no longer exists). The current repo README says
  one agent state, four endings, and no expiry — so the marketplace is contradicting the product.
- **Search is where it gets lost.** `state` returns 448 entries (we are one of them, buried);
  `daydream` returns 1 (us); `stuck` returns 15 (us); **`cognitive` returns 0** and
  **`creativity` returns 0** on a 2,311-entry marketplace. The framing the product is built on is
  not searchable, because no entry uses those words and there is no cognition shelf.

Adjacent competition, live: `dreamer` (idle dreaming, replays the day's residue — overlaps
`/dream`), `innerscape` (journaling plus an **Unstuck Coach** — overlaps `/unstuck` by name and
purpose), `mood` and `mood-engine` (overlap `/mood` and the recommendation evidence),
`biomimetic-brain` (25 subsystem state files: energy, fatigue, circadian, attention),
`web-crawler-spider` (a spider that grows a web with tool calls — the ambient-visual precedent).

## The surfaces the SDK offers, and which we use

The desktop SDK's contribution areas are the menu of UX positions a plugin can occupy. Antemuse's
registrations, read from `desktop/plugin.js`:

| Surface | We use it | Notes |
| --- | --- | --- |
| Layout pane | **yes, ×2** | right dock (map), main (cockpit) |
| Full page + sidebar nav | **yes, ×2+×2** | `/{id}` and `/{id}/cockpit` |
| Status bar | **yes** | one chip |
| ⌘K palette | **yes, ×2** | open cockpit, watch |
| Plugin settings page | no, deliberately | `config_schema` renders the host form; a second page would shadow it |
| Keybinds | no | the cockpit has its own canvas keys |
| Title bar | no | — |
| Composer extensions | no | — |
| Transcript directives | no | — |
| Tool media renderers | no | our tool returns text, not `MEDIA:` files |
| Appearance settings | no | we read `--ui-*` rather than offering a theme |
| Session-row decorations / kanban badges | no | not our object |

So the surface coverage is broad. The gaps are not "missing surfaces" — they are what those
surfaces *say*.

## Six patterns in how community plugins approach UX

**1 · Ambient, live, and small beats a new page.** taskwatch renders every background process into
the status bar and a side pane, with live output, runtime, a silence heartbeat, a two-click stop, and
an OS notification when something goes quiet. `crypto-prices` is a marquee in the status bar;
`cheatsheet` is a title-bar tool. The unit of contribution is a glance, not a destination.

**2 · Read-only observability is a product category.** `session-lens` (cost and why, full trace,
tool failures, quotas), `bot-activity` (per-bot timeline), `pending-queue-monitor` (approval backlog),
`protean-subagent-viewer` (live workers). 21.5% of entries say "read-only" and mean it as a virtue:
they show what the agent did without touching it.

**3 · Disclosure is the norm, and it is specific.** 79.4% carry a paragraph naming exactly what
leaves the machine, which credentials are used, and what is written. `pending-queue-monitor` is the
model: it "returns only counts, age buckets, oldest age… never summaries, payloads, or record
content." Our account's counts-not-quotes rule is the same instinct — but our catalog entry has no
disclosure at all.

**4 · Draw, don't add tools.** 908 of 1,375 plugins register no tools; the median plugin registers 2.
The desktop-side plugins reach the gateway's own projections (`process.list`, state.db, pending
queues) instead of asking the model to call something. Context is treated as a budget.

**5 · Friction is deliberate and tiny.** taskwatch's "two-click stop" is the clearest example: a
destructive action costs two clicks, and everything else costs none. Notification — not a modal — is
how they tell you something ended.

**6 · One honest caveat beats a confident claim.** `dream`'s "today had too few projects to connect"
is the same move as `artifacts`' "early public preview" and the 236 entries that publish
`known_issues`. The ecosystem rewards stating the limit in the listing.

## Gaps this exposes in Antemuse

Ranked by user-visible value per unit of work. Each maps to an option in `proposal.md`.

**G1 — The status chip has no state in it.** We occupy the status bar (2.1% of plugins do) but the
chip shows a label. It could show `walking · 4/6 hops`, the ending reason for a few seconds, and
nothing when idle. Evidence: taskwatch/crypto-prices put *live detail* in that slot. Cost: small,
one render function. → D1.

**G2 — No observability surface.** Every state already writes a `moves` row (turns-to-dose, ending),
plus `normal.json` (how long a dose took, per state) and the journal. None of it is readable by the
person. A read-only "states" panel — last N states, served/seen, ending, turns — is the same shape as
`session-lens` but with our data. Cost: medium; read-only; no new writes. → new D6.

**G3 — The outcome is not an object.** Community plugins that produce something give you something:
`artifacts` (a library), `hwiki` (markdown files you and the agent edit), `hermes-chat-share` (PNG,
HTML, PDF). A state produces one line that expires in two turns. Cost: medium (a journal file).
→ O3.

**G4 — Six states are only discoverable by knowing the commands.** `cheatsheet` exists because the
ecosystem knows this is a problem. We have palette entries for the cockpit but none for the states.
A catalogue page (contract, dose, product, enter button) closes it. Cost: medium. → D4.

- **G5 — The shop window is stale and mis-shelved.** [revised after checking the live site] The
  README rendered on the page describes five states, second-based pacing and an `expired` ending
  that no longer exist, and never mentions `/explore`. The entry sits on `general` (119, mixed with
  themes and telemetry) rather than `desktop` (409). Card copy does not contain "cognitive",
  "creativity" or "state", which is why `cognitive` returns 0 results marketplace-wide.
  Cost: a release plus copy — no engine work. (Original claim, now retracted:)
screenshots and 3 `known_issues`, but **no disclosure paragraph** (79% of entries have one) and no
cockpit image — the screenshots all pre-date it. For a plugin that reads memory files, session
transcripts and live feeds, that omission is a trust gap, not a formatting one. Cost: small; the entry
is generated, so `tools/catalog_entry.py` needs the field.

**G6 — A blocked tool has no reason.** `transform_tool_result` is used by 37 community plugins and by
none of ours; when a state forbids a tool the agent gets a bare refusal. Cost: small.

**G7 — No cost visibility.** 42 plugins hook `post_api_request`; we record turns-to-dose and nothing
about tokens or latency, so "what did this walk cost" is unanswerable. Cost: medium; privacy-sensitive
(no content, counts only).

**G8 — The tool schema is 3,461 characters in every turn** while the median plugin registers 2 tools
and 908 register none. The experimental engine (`walk_new`, `walk_del`, `spark`, `keep`, `method`,
`budget`, `spec`) rides along in every conversation. Cost: medium; moving it to a second tool is the
largest single context saving available.

## What not to copy

- **Long disclosure paragraphs as a substitute for design.** 79% have one; several are 150+ words of
  prose. We need one precise paragraph, not a wall.
- **Zero-tool plugins as a template.** They are draw-only by nature; our product is agent-side, so a
  tool is correct. The lesson is the schema's *size*, not its existence.
- **Approval cards.** `pre_approval_request` (17 plugins) exists for actions that need a human gate.
  A state is an aside; a card would make it a checkpoint.
- **Themes.** 255 desktop entries include theme plugins; we already read the host theme, which is the
  better behaviour.

## Corrections this research makes to earlier claims

- I said "only antemuse and plan-mode use `transform_llm_output`". That was true of the four plugins
  installed here; across the live catalog **116** plugins use it. The behaviour is sound, the claim
  was too strong.
- I implied the status bar was unused by us. It is used — the chip exists and is the only place a
  state is visible without opening a pane. The gap is its content, not its presence.
- I said the listing has no disclosure. It does — 84.2% of live entries carry one, and ours is
  precise. The listing problems are different: a stale README, the wrong shelf, and card copy that
  does not name `/explore`.
- I used the 1,379-entry local catalog as "the ecosystem". The live catalog is 2,311 entries; the
  local copy lags.

## Additions to the plan

- **D6 · a read-only states panel** (G2) — shipped with D1 in Phase 1 if the panel is cheap, else
  Phase 2.
- **L1 · listing work** (G5) — disclosure field in `tools/catalog_entry.py`, a cockpit screenshot, and
  a states-table screenshot. Independent of code; do it before the next release.
- **X1 · `transform_tool_result`** (G6) — one sentence in a blocked tool's result. Phase 1 or 2.
- **C1 · cost counts via `post_api_request`** (G7) — Phase 3, only if the states panel shows it.
