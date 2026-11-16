"""Repository hygiene: shipped and experimental code never reads host credentials."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("auth.json", "access_token")


def test_non_test_files_do_not_name_hermes_credential_storage():
    offenders = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or "tests" in path.relative_to(ROOT).parts or ".git" in path.parts:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        if any(token in text for token in FORBIDDEN):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, "credential-storage references outside tests: " + ", ".join(offenders)
