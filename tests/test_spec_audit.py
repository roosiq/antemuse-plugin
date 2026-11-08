"""The spec record is part of the contract, so drift is a test failure.

Two kinds of drift have been real here: a change whose own header disagreed with
`docs/spec.md` §15, and a status word matched as a substring ("Not implemented."
reading as "implemented"). The audit is a tool because it is useful by hand; it is a
test because a stale record is indistinguishable from a lie in a review.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def audit():
    path = ROOT / "tools/spec_audit.py"
    spec = importlib.util.spec_from_file_location("spec_audit", path)
    assert spec and spec.loader, f"cannot load {path}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_change_is_recorded_and_decided():
    mod = audit()
    rows, specs = mod.doc_rows(), mod.spec_status()
    assert specs, "no change folders found"
    missing_row = sorted(set(specs) - set(rows))
    missing_folder = sorted(set(rows) - set(specs))
    assert not missing_row, f"changes with no §15 row: {missing_row}"
    assert not missing_folder, f"§15 rows with no change folder: {missing_folder}"

    drift = [name for name, text in specs.items()
             if mod.status_word(text) != mod.status_word(rows[name])]
    assert not drift, f"status disagrees between spec.md and §15: {drift}"


def test_not_implemented_is_not_implemented():
    mod = audit()
    assert mod.status_word("**proposed** 2026-11-08. Not implemented.") == "proposed"
    assert mod.status_word("Status: implemented (684 tests)") == "implemented"
    assert mod.status_word("**partial — picture done**") == "partial"
