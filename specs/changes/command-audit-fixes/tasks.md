# Tasks

- [x] T1 — Stamp recorded turns with their session; filter reads by session (`core/recall.py`).
- [x] T2 — Thread the owning session through readiness and the provider call
      (`core/sources.py::_own_turns/ready/memory_pairs`, `core/engine.py` entry + delivery).
- [x] T3 — Scope the seeding pool to the owning chat (`core/engine.py::owner_session`,
      `core/seeding.py`).
- [x] T4 — Record turns with their session in the hooks (`__init__.py`).
- [x] T5 — Write digests, not material, to `delivery_trace.log` (`core/engine.py::_trace_key`).
- [x] T6 — Refuse picks from a chat that is not exploring (`core/engine.py::note_pick`).
- [x] T7 — Recognise the account line as a footer so an ending is drawn once
      (`core/engine.py::_is_footer_line`).
- [x] T8 — Ground `/unstuck` in earlier history and name the last change as the thing to avoid
      (`core/sources.py::unstuck_text`).
- [x] T9 — Say `APART` / `adjacent` when a pair shares nothing
      (`core/sources.py::memory_pairs/day_connections`).
- [x] T10 — Correct dream and doomscroll copy to match the code (`core/states.py`).
- [x] T11 — Regression tests for T1–T9 (`tests/test_command_audit_fixes.py`,
      `tests/test_state_unstuck.py`), reversion-proved.
- [x] T12 — Update `specs/product/states.md`: walk as an act, ownership, trace privacy, honesty,
      and the repaired tools paragraph.
- [x] T13 — Full suite green: 946 passed, 6 skipped.

## Follow-ups (not in this change)

- [ ] Decide whether a restarted doomscroll keeps its count or its ephemerality.
- [ ] Decide whether `GET /state` should hide another chat's active summary.
- [ ] `/unstuck`'s account still names extracted tokens rather than the recommendation's substance;
      the wording change improves what is extracted but the ledger still tokenises prose.
