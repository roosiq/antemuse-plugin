"""The experiment ledger must refuse a record that would make the analysis a lie."""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools import ledger_check  # noqa: E402


def row(**over):
    base = {
        "session_id": "s-1", "model": "m", "provider": "p", "state": "walk",
        "arm": "default", "ending_reason": "complete", "block_seed": 3497679622,
        "dose": 6, "ceiling_minutes": 3, "entered_at": 1794182709.99,
        "turns": 6, "seconds_to_dose": 240, "tokens_in": 1200, "tokens_out": 800,
        "tool_failures": 0, "tool_blocks": 0, "outcome": True, "excluded": False,
    }
    base.update(over)
    return base


def test_a_complete_entry_passes():
    assert ledger_check.check_entry(1, row()) == []


def test_a_missing_field_fails():
    bad = row()
    del bad["tokens_out"]
    assert any("missing tokens_out" in e for e in ledger_check.check_entry(1, bad))


def test_an_outcome_must_be_a_boolean_not_a_guess():
    errs = ledger_check.check_entry(1, row(outcome="likely"))
    assert any("outcome must be a boolean" in e for e in errs)


def test_an_excluded_entry_must_say_why_and_carry_no_outcome():
    errs = ledger_check.check_entry(1, row(excluded=True))
    assert any("exclusion_reason" in e for e in errs)
    assert any("must not carry an outcome" in e for e in errs)


def test_a_kept_entry_may_not_have_a_null_outcome():
    errs = ledger_check.check_entry(1, row(outcome=None))
    assert any("needs an outcome" in e for e in errs)


def test_control_entries_deliver_no_dose():
    errs = ledger_check.check_entry(1, row(arm="control", dose=3))
    assert any("control entries deliver no dose" in e for e in errs)


def test_unstuck_has_no_half_arm():
    errs = ledger_check.check_entry(1, row(state="unstuck", arm="half", dose=0))
    assert any("no half arm" in e for e in errs)


def test_zero_tokens_is_refused():
    errs = ledger_check.check_entry(1, row(tokens_in=0, tokens_out=0))
    assert any("zero tokens" in e for e in errs)


def test_the_cli_validates_a_file_and_summarises(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_text("\n".join(json.dumps(row(state=s, arm=a, outcome=True))
                              for s, a in [("walk", "default"), ("walk", "half"),
                                           ("dream", "double")]) + "\n")
    good = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ledger_check.py"),
                           "--ledger", str(path), "--summary"],
                          capture_output=True, text=True)
    assert good.returncode == 0, good.stderr
    assert "below the 60/arm floor" in good.stdout

    path.write_text(json.dumps(row(outcome="maybe")) + "\n")
    bad = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ledger_check.py"),
                          "--ledger", str(path)], capture_output=True, text=True)
    assert bad.returncode == 1
    assert "outcome must be a boolean" in bad.stderr


def test_the_preregistration_names_every_state_and_seed():
    text = open(os.path.join(ROOT, "experiments", "state-settings",
                             "preregistration.md")).read()
    for state in ("walk", "daydream", "doomscroll", "dream", "unstuck"):
        assert state in text
    for seed in ("3497679622", "18095054", "751586276", "3399968528", "1739374009"):
        assert seed in text, seed
