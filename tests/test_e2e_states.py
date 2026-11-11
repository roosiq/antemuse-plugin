"""End-to-end over the public surface: enter, spend the dose, check the record.

The runner is executed as a subprocess, not imported. Importing it would purge and re-import the
`core` modules inside the pytest process, and every other module holding a reference to `states` or
`engine` would keep the old one — nine unrelated tests failed that way the first time.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATES = ["walk", "daydream", "dream", "unstuck"]


def _run(key: str, tmp_path: Path) -> dict:
    out = tmp_path / f"{key}.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "e2e_states.py"), "--only", key,
         "--json", str(out)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    assert out.exists(), proc.stdout + proc.stderr
    result = json.loads(out.read_text())[0]
    result["_exit"] = proc.returncode
    result["_out"] = proc.stdout
    return result


@pytest.mark.parametrize("key", STATES)
def test_a_state_serves_its_own_material_and_records_its_ending(key, tmp_path):
    result = _run(key, tmp_path)
    assert result["_exit"] == 0, result["_out"] + str(result["problems"])
    assert not result["problems"], result["problems"]
    assert result["ended_by_dose"], "the state must end on its own dose, not on /return"
    assert result["moves_rows"], "no moves row: the ending was not recorded"
    state, ending, dose_done = result["moves_rows"][-1]
    assert state == key
    assert ending == "complete", ending
    assert dose_done and dose_done > 0, dose_done
    if not result.get("partial"):
        assert result["served_rows"] > 0, "served material was not written to the ledger"


def test_every_state_is_in_the_table():
    """A new state must be added to the runner, or it ships without ever being entered."""
    from core import states

    assert sorted(states.STATES) == sorted(STATES + ["doomscroll"]), sorted(states.STATES)
    src = (ROOT / "tools" / "e2e_states.py").read_text()
    for key in states.STATES:
        assert re.search(rf'"{key}"', src), f"{key} missing from the runner"
