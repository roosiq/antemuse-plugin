"""End-to-end over the sole agent state: enter, spend the dose, record the ending."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATES = ["walk", "daydream", "doomscroll", "dream", "unstuck"]
#: The one state whose material must never reach the concept ledger: feed text is untrusted
#: and unpersisted by rule. Every other state records what it surfaced.
NO_LEDGER_STATES = {"doomscroll"}


def _run(key: str, tmp_path: Path) -> dict:
    out = tmp_path / f"{key}.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "e2e_states.py"), "--only", key, "--json", str(out)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    assert out.exists(), proc.stdout + proc.stderr
    result = json.loads(out.read_text())[0]
    result["_exit"] = proc.returncode
    result["_out"] = proc.stdout
    return result


@pytest.mark.parametrize("key", STATES)
def test_a_state_serves_its_own_material_and_records_its_ending(key, tmp_path):
    result = _run(key, tmp_path)
    if "cannot enter" in str(result.get("entered", "")):
        # A state whose material is not in this environment refuses by name at entry. That is
        # the state working; the dose contract is checked where the material exists.
        pytest.skip(result["entered"])
    assert result["_exit"] == 0, result["_out"] + str(result["problems"])
    assert not result["problems"], result["problems"]
    assert result["ended_by_dose"]
    state, ending, dose_done = result["moves_rows"][-1]
    assert state == key
    assert ending in ("complete", "dry", "failed"), ending
    if ending == "failed":
        # A provider that cannot reach its material ends the state by name, with nothing
        # served. That is the state working; the dose path is covered where material exists
        # (tests/test_state_<state>.py). The name must be in the account, not just a zero.
        assert dose_done == 0, result
        said = " ".join([result.get("account") or ""] + list(result.get("journal_tail") or [])).lower()
        assert any(word in said for word in ("unavailable", "failed", "empty")), result
        return
    assert dose_done > 0
    if ending == "dry":
        assert dose_done < int(result["dose"])
    if not result.get("partial") and key not in NO_LEDGER_STATES:
        assert result["served_rows"] > 0, result
    if key in NO_LEDGER_STATES:
        # Material that is not a concept (a memory pair, a feed item, a commit subject) must
        # not reach the concept ledger; a zero here is the privacy rule working.
        assert result["served_rows"] == 0, result


def test_every_state_is_in_the_table():
    from core import states

    assert sorted(states.STATES) == sorted(STATES)
    src = (ROOT / "tools" / "e2e_states.py").read_text()
    assert "STATES =" in src
    for key in states.STATES:
        assert key in src
