"""End-to-end over the sole agent state: enter, spend the dose, record the ending."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATES = ["walk"]


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
    assert result["_exit"] == 0, result["_out"] + str(result["problems"])
    assert not result["problems"], result["problems"]
    assert result["ended_by_dose"]
    state, ending, dose_done = result["moves_rows"][-1]
    assert state == key
    assert ending in ("complete", "dry")
    assert dose_done > 0
    if ending == "dry":
        assert dose_done < int(result["dose"])
    if not result.get("partial"):
        assert result["served_rows"] > 0


def test_every_state_is_in_the_table():
    from core import states

    assert sorted(states.STATES) == STATES
    src = (ROOT / "tools" / "e2e_states.py").read_text()
    assert 'STATES = ["walk"]' in src
