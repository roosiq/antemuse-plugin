# Change: scan past sessions automatically, bounded, at session start

Status: **LIVE** · opened 2026-11-08 · built 2026-11-08

## Intent

`concept-history` can read past sessions, but only when asked. A ledger that is filled by hand
is a ledger nobody fills: the moves that depend on it — walk's "seen before", dream's circling
connections, unstuck's history — would always be looking at whatever was scanned last time.

This change runs the scan itself: **once per session, bounded by messages and by wall clock,
never in the turn's way, never with a model call**.

## Behaviour

On the first `pre_llm_call` of a session (the hook already receives `session_id`):

1. Skip if this session has already been auto-scanned, or if the last auto-scan was under
   `MIN_INTERVAL` (30 min) ago — a resumed session must not re-scan on every turn.
2. Otherwise start **one** background scan of at most `AUTO_MESSAGES` (300) new messages with a
   wall-clock budget of `AUTO_BUDGET_S` (2.0 s). It runs in a daemon thread, so the turn is
   never delayed and the process is never held open by it.
3. When it finishes, record one line in the ledger's own event log —
   `scanned N messages → C concepts from S past sessions` — and the same line in the journal
   when a state happens to be open (the journal only exists inside a state, and a session
   scan usually runs before one starts). Silent when there was nothing new to scan.
4. Single-flight: a second call while one scan is running does nothing.

The cursor is shared with the manual scan, so an automatic scan and a batched manual scan never
read the same message twice, and a larger manual run simply continues where the small one
stopped.

## Non-goals

- No cron, no scheduler, no work outside a live session. Nothing runs when no one is talking.
- No model call, no network, no write to the agent's memory or any provider.
- No new setting, no new command, no change to any state's material, dose, ceiling or ending.
- No scan of tool output, reasoning fields, or any table other than `messages`.
- No scan that can fail a turn: every path swallows its own exception.

## Acceptance criteria

1. **It runs once.** Two `pre_llm_call` events in the same session start one scan, not two, and
   the second within `MIN_INTERVAL` does nothing even for a different session.
2. **It is bounded.** A store with 5 000 messages scans at most `AUTO_MESSAGES`, and with a
   1 ms budget it stops early, records what it stored so far, and leaves the cursor at the last
   message it actually read — never ahead of it.
3. **It never blocks the turn.** `autoscan()` returns immediately; the caller's measured wall
   time stays under 50 ms even when the scan itself takes longer.
4. **It is silent when there is nothing.** A scan that finds no new messages writes no journal
   line.
5. **It is not in the turn's way when it fails.** A missing or corrupt session store, a
   read-only ledger, or an exception inside the thread produces at most one named failure event
   and no raised exception.
6. **Nothing else changes.** All five states still deliver with the same material; §18's
   protected set is untouched.

## Verification

- `tests/test_session_scan.py`: once-per-session, the interval, the message cap, the wall-clock
  budget, cursor never ahead of the last read message, silence when empty, single-flight, and a
  failing store.
- A measured call: `autoscan()` wall time with a real `state.db`, and the journal line it left.

## Must not change

The protected set in `docs/spec.md` §18 — lifecycle, doses, ceilings, endings, turn budgets,
tool policy, directives, contracts, residue labels, journal cap, residue cap and decay, hook
contracts, `/return`, `CONTROL_TOOLS`, the wordless card — and the six settings stay six.

## Verification (2026-11-08)

- **Turn path measured at 0.014 s** through the real hook (`_pre_llm_call` with a platform and
  session id), while the scan itself ran in the background.
- **First live run**: `scanned 125 messages → 1 509 concept sightings from 3 past sessions`,
  ledger at 626 concepts; the second call in the same session returned `skipped`.
- `tests/test_session_scan.py` (11): once per session, the 30-minute interval, the message cap
  (5 of 20), a spent budget stopping early with the cursor left on the last message actually
  read (the follow-up scan then reads exactly the remainder), return-before-finish under 50 ms,
  single flight, silence when nothing is new, one event line when something is, the kill
  switch, a missing store as a named failure, and the lock never left set.
- Suite-wide isolation added (`tests/conftest.py`): an autouse temp data dir, `ANTEMUSE_NO_SCAN`
  by default, and a `real_home` marker for the one test whose subject is the installed frames.

Suite: **849 passed, 1 skipped**; `spec_audit` 0 drift.
