"""The docs, checked against the code they describe.

Every stale number in this repository's documentation was a number a person wrote by hand
and nobody re-read: "the six commands" outlived the new state by a week, "the pane is
the only visual surface" outlived the cockpit, and "12 properties hold" outlived the
harness that grew to twenty-six. These tests read the code and the files, so the count is
never a memory.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT))

from core import states  # noqa: E402

WORDS = {1: "one", 2: "two", 3: "three", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


def _doc(name: str) -> str:
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return fh.read()


def test_every_state_is_a_command_in_every_doc_that_lists_commands():
    """A state that is not in the command list is a state nobody can start."""
    docs = ("README.md", "SKILL.md", "TESTING.md", "CONTRIBUTING.md")
    for name in docs:
        body = _doc(name)
        for key in states.STATES:
            assert f"/{key}" in body, f"{name} never mentions the /{key} command"


def test_the_command_count_in_the_docs_matches_the_states():
    """One agent-state command plus `/return`; `/explore` remains person-driven."""
    states_word = WORDS[len(states.STATES)]
    assert "The three commands" in _doc("README.md"), \
        "README's heading is not 'The three commands'"
    assert "one agent state" in _doc("README.md"), \
        "README does not say there is one agent state"


def test_the_manifest_and_catalog_name_every_state():
    manifest = yaml.safe_load(_doc("plugin.yaml"))
    catalog = yaml.safe_load(_doc("plugin-catalog/antemuse.yaml"))
    for label, text in (("plugin.yaml", manifest["description"]),
                        ("catalog", catalog["description"])):
        for key in states.STATES:
            assert key in text, f"{label}'s description never mentions {key}"


def test_the_catalog_known_issues_do_not_promise_one_pane():
    """The cockpit is a second surface; a catalog that says 'the pane only' is wrong."""
    catalog = yaml.safe_load(_doc("plugin-catalog/antemuse.yaml"))
    issues = " ".join(catalog["known_issues"])
    assert "pane only" not in issues, issues
    assert "cockpit" in issues, issues


def _test_names():
    names = set()
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("def test_"):
                names.add(line[4:line.index("(")])
    return names


def test_the_specs_cite_tests_that_exist():
    """A spec that names a test nobody wrote is a claim with no evidence behind it.

    Written after a spec was drafted citing four plausible-sounding test names that had
    never existed — the failure mode is inventing the evidence, not forgetting it.
    """
    known = _test_names()
    # a module path (`tests/test_docs_current.py`) is not a test name
    modules = {p.stem for p in (ROOT / "tests").glob("test_*.py")}
    cited = set()
    pattern = re.compile(r"(test_[a-z0-9_]+)")
    for path in (ROOT / "specs").rglob("*.md"):
        cited.update(pattern.findall(path.read_text(encoding="utf-8")))
    missing = sorted(cited - known - modules)
    assert not missing, f"specs cite tests that do not exist: {missing}"


def test_the_specs_cite_harness_checks_that_exist():
    """Same rule for the behaviour harness: check names are evidence too."""
    def flat(text):
        return re.sub(r"\s+", " ", text)

    harness = flat((ROOT / "tools" / "cockpit_harness.py").read_text(encoding="utf-8"))
    cited = set()
    pattern = re.compile(
        r"`((?:module|pane|data|canvas|render|flight|shoot|net|lifecycle|mobile|"
        r"reduced motion|ui|theme): [^`]+)`")
    for path in (ROOT / "specs").rglob("*.md"):
        cited.update(flat(n) for n in pattern.findall(path.read_text(encoding="utf-8")))
    # a spec may quote the measured value next to the check name: `net: … (caught=13)`
    missing = sorted(n for n in cited if re.sub(r"\s*\(.*\)$", "", n) not in harness)
    assert not missing, f"specs cite harness checks that do not exist: {missing}"


def test_the_layout_section_counts_the_settings_it_has():
    manifest = yaml.safe_load(_doc("plugin.yaml"))
    n = len(manifest["config_schema"])
    assert f"{n} bounded settings" in _doc("README.md"), \
        f"README's layout block does not say {n} settings"
    assert f"the {WORDS[n]} settings" in _doc("README.md")
