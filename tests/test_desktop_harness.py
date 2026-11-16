"""The jsdom harness ships in the package, so it has to pass in the package.

It went stale for four releases without anyone noticing: it asserted the registration by the
*shape* of the area list, which changes every time a route or palette command is added, and it
still expected a countdown clock the pane stopped having. Anyone running the documented command
on a downloaded tarball got an assertion error before the fourth check.

This test runs it, so drift fails the suite instead of the reader.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tools" / "desktop_harness" / "mount.mjs"
DEPS = ROOT / "tools" / "desktop_harness" / "node_modules"
NODE = shutil.which("node") or ""


@pytest.mark.skipif(not NODE, reason="the jsdom harness needs node on PATH")
@pytest.mark.skipif(
    not DEPS.exists(),
    reason="harness dependencies are not installed: npm ci --prefix tools/desktop_harness",
)
def test_the_shipped_harness_passes_on_a_clean_mount():
    done = subprocess.run(
        [NODE, str(HARNESS)], cwd=str(ROOT), capture_output=True, text=True, timeout=300
    )
    tail = (done.stdout or "") + (done.stderr or "")
    assert done.returncode == 0, "the shipped harness fails on a clean mount:\n" + tail[-3000:]
    assert "12 properties PASS" in tail, "the harness ran but did not reach its summary"
