"""The site is a build artifact of `docs/architecture.md`, so it can be stale.

A generated page that nobody rebuilds is a second copy of the truth, which is the
failure mode `tools/spec_audit.py` exists to prevent for specs. Rebuild in memory and
compare bytes.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location("site", ROOT / "tools/site.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_site_matches_the_architecture_document():
    mod = load()
    built = (ROOT / "site/index.html").read_text()
    assert built == mod.build(), (
        "site/index.html is stale — rebuild with: python3 tools/site.py"
    )
    md = mod.SRC.read_text()
    import re
    for heading in re.findall(r"^## (.+)$", md, re.M):
        assert heading.split("—")[0].strip() in built, heading


def test_status_chips_are_derived_not_typed():
    mod = load()
    page = (ROOT / "site/index.html").read_text()
    for word, cls in mod.STATUS_CLASS.items():
        if f'class="chip {cls}"' in page:
            assert f">{word} " in page  # the header board counts something real
