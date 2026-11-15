# Adversarial review — Sonnet 5.5

Run 2026-11-14 against the uncommitted working tree, read-only, 60 turns:

```
hermes chat --provider nous -m anthropic/claude-sonnet-5.5 \
  --query-file review-brief.md -Q --max-turns 60 --run-budget 1200
```

Brief listed twelve claims (C1–C12) and asked for findings with evidence. Verdict returned:
**not shippable as a release yet.** Full transcript:
`~/.hermes/cache/scratch/sonnet-review.txt`.

Everything below was re-checked here before it was accepted. A reviewer's finding is a claim like
any other.

## Accepted and fixed

| # | Finding | Fix |
| --- | --- | --- |
| 1 | A drained pool ended `failed` saying `nothing arrived`, though a pair had been served and shown. Repeats shared the failure branch. | `deliver_if_due()` now separates a repeat from a failure: repeats count in `active["repeated"]`, clear `empty`, and end the state `dry` after two — which is what `dry` means. Guard: `test_a_repeated_line_ends_dry_and_does_not_claim_nothing_arrived`. |
| 5 | The `CHANGELOG` Unreleased section sits above a released `0.10.44` with explore entries already under it; no version bump. | Recorded; belongs to the release cut (S6), not to a code fix. |
| 9 | Stale "paced by the clock / one a second" text in `dashboard/plugin_api.py`, the `deliver_if_due()` docstring, and "until it ends or expires" in `README.md:400` and `TESTING.md:102`. | All four reworded. My earlier claim that the README no longer mentions expiry was **false** and is retracted here. |
| 10 | `tools/examples.py` leaked `settings.override(dream_projects=…)` across scenarios and wrote the walk cursor into the repository (dirtying `.antemuse/walk_cursor.json`). | Overrides cleared in `finally`; the walk runs with `os.chdir(home)` and a cursor inside the temp home. The tracked cursor file is clean again. |
| 11 | `StateChip` printed a count beside a failed poll, and `chip()` could return `NaN/6 hops` for a non-numeric `served`. | `error ? '' : chip(payload)`, plus a finite-number guard. |
| 12 | `.gitignore` ignored `*.png`, so `docs/design/*.png` — which `APP_FLOW.md` points at — could never be committed. | `!docs/design/*.png` added. |

## Accepted and fixed, second pass

| # | Finding | Fix |
| --- | --- | --- |
| 2 | `_material_key()` keys on the rendered string; daydream truncates each memory to 70 characters, so two memories sharing a prefix collide and one is swallowed. | The provider now owns identity. `memory_pairs(keyed=True)` returns `(pair id, line)` where the id is a sha1 of the two memories, and `deliver_if_due()` asks any provider whose signature takes `skip` for keyed material. Guard: `removed-state coverage` (three memories with an identical 70-character prefix; both pairs are served, `shown` has two distinct keys). |
| 3 | `_pair_cursor()` was a global counter file, not keyed by session or state, and a no-op on a two-memory pool. | Deleted. `memory_pairs(skip=…)` returns the best pair that has not been served — pure in the pool, correct per state, and it cannot rotate to a weaker pair while a better one is unserved. `pair_cursor.json` is no longer read or written. |
| 7 | `moves.dose_done` and the account line could disagree. | Not reproducible now: accounts read `dream · 1 of 2 recombinations · connection · nothing new arrived`. Verified in `docs/EXAMPLES.md`. |
| 8 | `TURN_GAP = 1.1` was latent after delivery stopped being clock-paced. | `0.05`, with a comment saying why it exists at all. |
| 13 | `_is_failure_line()` matched a substring anywhere, so a headline containing "unavailable" was scored as the source failing. | Matched in the first 60 characters only. Guard: `test_a_provider_failure_line_is_not_material`, both directions. |
| 14 | `PROVIDERS["explore"] = None` broke any iteration over providers. | Kept `None` (explore genuinely has no provider) with a comment that says so, so the next reader does not treat it as a gap. |

## Still open

| # | Finding | Why it stands open |
| --- | --- | --- |
| 4 | `plugin-catalog/antemuse.yaml` is stale (old category, description, sha; `--check` fails). | By design: the entry is generated at release time and cannot embed a commit that contains it. Regenerate in S6, never hand-edit. |

## Rejected

- **"`seen` can be advanced by a session that does not own the state."** Not reproduced.
  Probe: state entered as `A`, one unit served, `seen=None`; after `inject("B")` the stored
  `seen` is still unset and the block is withheld. The owner gate at `inject()` holds. What the
  probe *did* show is that a foreign `inject` leaves `active` empty afterwards — a different
  question from the one raised, and it is on the list to check.
- **"Pane-only completion no longer happens."** Confirmed as behaviour, and it is intended: a unit
  is spent when shown, and a poll is not a turn. It needs one sentence in the README rather than a
  code change.

## Verified after the fixes

- `pytest tests/ -q` → **943 passed, 1 skipped**.
- `tools/cockpit_harness.py` → **26/26** (one earlier run reported 25/26; the harness has at least
  one timing-sensitive check — a flake to pin down, not a regression).
- `tools/examples.py --check` → ok, 8 examples; `walk_cursor.json` untouched.
- No reference to `_pair_cursor` / `pair_cursor.json` remains in `core/`, `tests/`, `tools/`.
